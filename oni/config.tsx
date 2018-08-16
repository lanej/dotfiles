
import * as React from "react"
import * as Oni from "oni-api"

export const activate = (oni: Oni.Plugin.Api) => {
    console.log("config activated")

    // Input
    //
    // Add input bindings here:
    //

    //
    // Or remove the default bindings here by uncommenting the below line:
    //
    // oni.input.unbind("<c-p>")

}

export const deactivate = (oni: Oni.Plugin.Api) => {
    console.log("config deactivated")
}

export const configuration = {
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
    "ui.fontSmoothing": "auto",
}
