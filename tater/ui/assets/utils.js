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
 * Filter: matches on node name (label); ancestor nodes of any match are also
 * included so hierarchy context is visible.
 *
 * renderOption: indents each option by depth (derived from "|"-separated value),
 * renders non-leaf (disabled) entries bold, and highlights the matched substring.
 */

// Shared search term written by hlMultiFilter, read by hlMultiRenderOption.
let _hlMultiSearch = "";

window.dashMantineFunctions.hlMultiFilter = function ({ options, search }) {
    _hlMultiSearch = (search || "").toLowerCase();
    if (!_hlMultiSearch) return options;

    const includedPaths = new Set();
    options.forEach((option) => {
        if (option.label.toLowerCase().includes(_hlMultiSearch)) {
            const segments = option.value.split("|");
            for (let i = 1; i <= segments.length; i++) {
                includedPaths.add(segments.slice(0, i).join("|"));
            }
        }
    });

    return options.filter((option) => includedPaths.has(option.value));
};

window.dashMantineFunctions.hlMultiRenderOption = function ({ option }) {
    const depth = option.value.split("|").length - 1;
    const label = option.label;
    const lower = _hlMultiSearch;

    // Build label content — highlight the matching substring if present.
    let content;
    const matchIdx = lower ? label.toLowerCase().indexOf(lower) : -1;
    if (matchIdx !== -1) {
        content = [
            label.slice(0, matchIdx),
            React.createElement(
                "mark",
                { key: "m", style: { background: "var(--mantine-color-yellow-3)", borderRadius: "3px", padding: "0 0" } },
                label.slice(matchIdx, matchIdx + lower.length)
            ),
            label.slice(matchIdx + lower.length),
        ];
    } else {
        content = label;
    }

    return React.createElement(
        "span",
        {
            style: {
                paddingLeft: `${depth * 14}px`,
                fontWeight: option.disabled ? 600 : "normal",
                opacity: option.disabled ? 0.75 : 1,
            },
        },
        content
    );
};
