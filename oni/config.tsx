
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
  "editor.fontFamily": "Hack Nerd Font",
  "editor.fontSize": "13px",
  "editor.scrollBar.visible": false,
  "oni.loadInitVim": true,
  "oni.useDefaultConfig": false,
  "sidebar.enabled": false,
  "statusbar.enabled": false,
  "tabs.mode": "native",
  "oni.hideMenu": true,
  "terminal.shellCommand": "/bin/zsh",
  "ui.animations.enabled": true,
  "ui.colorscheme": "tender",
  "ui.fontFamily": "Hack Nerd Font",
  "ui.fontSize": "13px",
  "ui.fontSmoothing": "auto",
  "autoClosingPairs.enabled": false,

  "environment.additionalPaths": [ 
    "/usr/bin", 
    "/Users/jlane/go/bin", 
    "/usr/local/bin", 
  ],

  "experimental.indentLines.filetypes": [
    ".tsx",
    ".ts",
    ".jsx",
    ".js",
    ".go",
    ".re",
    ".py",
    ".c",
    ".cc",
    ".lua",
    ".java",
    ".tf",
    ".json",
  ],
  "experimental.indentLines.enabled": true,
}
