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
