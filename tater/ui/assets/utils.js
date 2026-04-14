/**
 * General-purpose clientside callback utilities for Tater.
 */

window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.tater = window.dash_clientside.tater || {};

Object.assign(window.dash_clientside.tater, {

    autoScrollTop: function (_docId) {
        window.scrollTo({ top: 0, behavior: "instant" });
    },

    /**
     * Conditional visibility toggle.
     * v         – current value of the controlling widget
     * config    – {target, empty} from the tater-cond-config dcc.Store
     */
    conditionalVisibility: function (v, config) {
        if (config === null || config === undefined) return {};
        return v === config.target ? {} : { "display": "none" };
    },

    /**
     * Conditional value-clear: returns empty_value when the widget is hidden.
     * v         – current value of the controlling widget
     * config    – {target, empty} from the tater-cond-config dcc.Store
     */
    conditionalClear: function (v, config) {
        if (config === null || config === undefined) return window.dash_clientside.no_update;
        return v !== config.target ? config.empty : window.dash_clientside.no_update;
    },

    /** Show an element ({}) when v is truthy; hide it (display:none) otherwise. */
    showWhenTruthy: function (v) {
        return v ? {} : { "display": "none" };
    },

    /** Clear a text input — returns an empty string. */
    clearInput: function () {
        return "";
    },

    /** Open a component by returning true (e.g. a Drawer's opened prop). */
    openOnClick: function () {
        return true;
    },

});


// ---------------------------------------------------------------------------
// DMC Functions-as-Props (window.dashMantineFunctions)
// ---------------------------------------------------------------------------

window.dashMantineFunctions = window.dashMantineFunctions || {};

/**
 * renderOption / filter for HierarchicalLabelMultiWidget.
 *
 * Filter (hlMultiFilter): matches on node name (label); ancestor nodes of any match are
 * always included. Optionally also includes siblings and/or direct children of matched
 * nodes, controlled by a sentinel config item prepended to the data array by
 * HierarchicalLabelMultiWidget.component() in hierarchical_label.py.
 *
 * Sentinel format: value = "__config__" + JSON string, e.g.:
 *   __config__{"showSiblings":true,"showChildren":false}
 * The sentinel has an empty label and disabled=true so it is never rendered or selected.
 *
 * renderOption (hlMultiRenderOption): indents each option by depth (derived from
 * "|"-separated value), renders non-leaf (disabled) entries bold, and highlights
 * the matched substring using the search term stashed by hlMultiFilter.
 */

// Shared search term written by hlMultiFilter, read by hlMultiRenderOption.
let _hlMultiSearch = "";

const _CONFIG_PREFIX = "__config__";

window.dashMantineFunctions.hlMultiFilter = function ({ options, search }) {
    _hlMultiSearch = (search || "").toLowerCase();

    // Extract and strip the sentinel config item.
    let showSiblings = false;
    let showChildren = false;
    const dataOptions = options.filter((o) => {
        if (!o.value.startsWith(_CONFIG_PREFIX)) return true;
        try {
            const config = JSON.parse(o.value.slice(_CONFIG_PREFIX.length));
            showSiblings = !!config.showSiblings;
            showChildren = !!config.showChildren;
        } catch (e) {
            console.warn("hlMultiFilter: failed to parse sentinel config", o.value);
        }
        return false;  // always strip sentinel from results
    });

    if (!_hlMultiSearch) return dataOptions;

    const includedPaths = new Set();

    dataOptions.forEach((option) => {
        if (!option.label.toLowerCase().includes(_hlMultiSearch)) return;

        const segments = option.value.split("|");

        // Always include ancestors (full spine to root).
        for (let i = 1; i <= segments.length; i++) {
            includedPaths.add(segments.slice(0, i).join("|"));
        }

        // Siblings: all options sharing the same parent path.
        if (showSiblings && segments.length > 1) {
            const parentPrefix = segments.slice(0, -1).join("|") + "|";
            dataOptions.forEach((o) => {
                if (o.value.startsWith(parentPrefix) && !o.value.slice(parentPrefix.length).includes("|")) {
                    includedPaths.add(o.value);
                }
            });
        }

        // Direct children: one level below the matched node.
        if (showChildren) {
            const childPrefix = option.value + "|";
            dataOptions.forEach((o) => {
                if (o.value.startsWith(childPrefix) && !o.value.slice(childPrefix.length).includes("|")) {
                    includedPaths.add(o.value);
                }
            });
        }
    });

    return dataOptions.filter((option) => includedPaths.has(option.value));
};

// Tabler chevron-down SVG used to indicate non-leaf (expandable) nodes.
const _chevronDown = React.createElement(
    "svg",
    {
        xmlns: "http://www.w3.org/2000/svg",
        width: 10, height: 10,
        viewBox: "0 0 24 24",
        fill: "none",
        stroke: "currentColor",
        strokeWidth: 2,
        strokeLinecap: "round",
        strokeLinejoin: "round",
        style: { marginLeft: "4px", verticalAlign: "middle", opacity: 0.5, flexShrink: 0 },
    },
    React.createElement("polyline", { points: "6 9 12 15 18 9" })
);

window.dashMantineFunctions.hlMultiRenderOption = function ({ option, checked }) {
    const depth = option.value.split("|").length - 1;
    const label = option.label;
    const lower = _hlMultiSearch;
    const isLeaf = option.leaf !== false;  // default true if field absent

    // Build label content — highlight the matching substring if present.
    let labelContent;
    const matchIdx = lower ? label.toLowerCase().indexOf(lower) : -1;
    if (matchIdx !== -1) {
        labelContent = [
            label.slice(0, matchIdx),
            React.createElement(
                "mark",
                { key: "m", style: { background: "var(--mantine-color-yellow-3)", borderRadius: "3px", padding: "0 0" } },
                label.slice(matchIdx, matchIdx + lower.length)
            ),
            label.slice(matchIdx + lower.length),
        ];
    } else {
        labelContent = label;
    }

    return React.createElement(
        "span",
        {
            style: {
                display: "flex",
                alignItems: "center",
                paddingLeft: `${depth * 14}px`,
                fontWeight: option.disabled ? 600 : "normal",
                opacity: option.disabled ? 0.75 : 1,
                borderLeft: checked ? "3px solid var(--mantine-primary-color-filled)" : "3px solid transparent",
            },
        },
        labelContent,
        !isLeaf ? _chevronDown : null,
    );
};
