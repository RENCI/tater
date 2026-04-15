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
 * filter / renderOption for HierarchicalLabel*Widget (shared by Select and MultiSelect).
 *
 * Option values are compact JSON arrays encoding the full path, e.g. '["Animals","Mammals","Dog"]'.
 * Depth is path.length - 1. JSON.stringify is used for ancestor/sibling/child comparisons,
 * which is safe because Python builds values with the same compact format (separators=(',',':')).
 *
 * hlFilter: matches on node name (label); ancestors of any match are always included.
 * Optionally also includes siblings and/or direct children of matched nodes, controlled
 * by a sentinel config item prepended to the data array by HierarchicalLabel*Widget.component().
 *
 * Sentinel format: value = "__config__" + JSON, e.g.:
 *   __config__{"showSiblings":true,"showChildren":false}
 * The sentinel has an empty label and disabled=true so it is never rendered or selected.
 * The search term is stashed in _hlSearch for use by hlRenderOption.
 *
 * hlRenderOption: indents each option by depth, renders non-leaf nodes bold, highlights the
 * matched substring, shows a chevron-down for non-leaf nodes, and a check icon when selected.
 */

// Shared search term written by hlFilter, read by hlRenderOption.
let _hlSearch = "";

const _CONFIG_PREFIX = "__config__";

window.dashMantineFunctions.hlFilter = function ({ options, search }) {
    _hlSearch = (search || "").toLowerCase();

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
            console.warn("hlFilter: failed to parse sentinel config", o.value);
        }
        return false;  // always strip sentinel from results
    });

    if (!_hlSearch) return dataOptions;

    // Parse all paths once upfront so comparisons don't re-parse on every check.
    const parsed = dataOptions.map((o) => JSON.parse(o.value));

    const includedValues = new Set();

    dataOptions.forEach((option, i) => {
        if (!option.label.toLowerCase().includes(_hlSearch)) return;

        const path = parsed[i];

        // Always include ancestors (full spine to root).
        for (let j = 1; j <= path.length; j++) {
            includedValues.add(JSON.stringify(path.slice(0, j)));
        }

        // Siblings: all options at the same depth sharing the same parent path.
        if (showSiblings && path.length > 1) {
            const parentStr = JSON.stringify(path.slice(0, -1));
            parsed.forEach((p, k) => {
                if (p.length === path.length && JSON.stringify(p.slice(0, -1)) === parentStr) {
                    includedValues.add(dataOptions[k].value);
                }
            });
        }

        // Direct children: one level below the matched node.
        if (showChildren) {
            parsed.forEach((p, k) => {
                if (p.length === path.length + 1 && JSON.stringify(p.slice(0, -1)) === option.value) {
                    includedValues.add(dataOptions[k].value);
                }
            });
        }
    });

    return dataOptions.filter((option) => includedValues.has(option.value));
};

// ---------------------------------------------------------------------------
// SVG icon helpers
// ---------------------------------------------------------------------------

// Renders a Tabler-style SVG icon. strokeWidth compensates for the 24×24 viewBox
// being scaled to `size` px so line weight stays consistent.
function _tablerSvg(points, stroke, size, svgStyle) {
    return React.createElement(
        "svg",
        {
            xmlns: "http://www.w3.org/2000/svg",
            width: size, height: size,
            viewBox: "0 0 24 24",
            fill: "none",
            stroke,
            strokeWidth: Math.round(2 * 24 / size),
            strokeLinecap: "round",
            strokeLinejoin: "round",
            style: svgStyle,
        },
        React.createElement("polyline", { points })
    );
}

// tabler:chevron-down — indicates a non-leaf (expandable) node.
function _chevronDown() {
    return _tablerSvg(
        "6 9 12 15 18 9",
        "var(--mantine-color-dimmed)",
        12,
        { marginLeft: "4px", flexShrink: 0 }
    );
}

// tabler:check — right-aligned selection indicator; hidden when unchecked.
function _checkIcon(visible) {
    return React.createElement(
        "span",
        {
            style: {
                marginLeft: "auto",
                paddingLeft: "8px",
                flexShrink: 0,
                visibility: visible ? "visible" : "hidden",
                display: "flex",
                alignItems: "center",
            },
        },
        _tablerSvg(
            "20 6 9 17 4 12",
            "var(--mantine-color-dimmed)",
            14,
            {}
        )
    );
}

window.dashMantineFunctions.hlRenderOption = function ({ option, checked }) {
    const depth = JSON.parse(option.value).length - 1;
    const label = option.label;
    const lower = _hlSearch;
    const isLeaf = option.leaf !== false;  // default true if field absent

    // Build label — highlight the matched substring if present.
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
                flex: 1,
                paddingLeft: `${depth * 14}px`,
                fontWeight: option.disabled ? 600 : "normal",
                opacity: option.disabled ? 0.75 : 1,
            },
        },
        React.createElement("span", null, labelContent),
        !isLeaf ? _chevronDown() : null,
        _checkIcon(checked),
    );
};
