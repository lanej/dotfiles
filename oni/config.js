"use strict";
exports.__esModule = true;
exports.activate = function (oni) {
    console.log("config activated");
    // Input
    //
    // Add input bindings here:
    //
    //
    // Or remove the default bindings here by uncommenting the below line:
    //
    // oni.input.unbind("<c-p>")
};
exports.deactivate = function (oni) {
    console.log("config deactivated");
};
exports.configuration = {
    //add custom config here, such as
    "ui.colorscheme": "tender",
    "sidebar.enabled": false,
    // "oni.useDefaultConfig": true,
    //"oni.bookmarks": ["~/Documents"],
    //"oni.loadInitVim": false,
    "editor.fontSize": "16px",
    "editor.fontFamily": "Hack",
    "ui.fontSize": "16px",
    "ui.fontFamily": "Hack",
    // UI customizations
    "editor.scrollBar.visible": false,
    "statusbar.enabled": false,
    "ui.animations.enabled": true,
    "ui.fontSmoothing": "auto"
};
