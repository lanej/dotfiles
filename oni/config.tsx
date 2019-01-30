import * as React from "react"
import * as Oni from "oni-api"

export const activate = (oni: Oni.Plugin.Api) => {
  oni.input.unbind("<c-g>") // make C-g work as expected in vim
  oni.input.unbind("<c-v>") // make C-v work as expected in vim
  oni.input.bind("<s-c-g>", () => oni.commands.executeCommand("sneak.show")) // You can rebind Oni's behaviour to a new keybinding
}

export const configuration = {
  activate,
  "achievements.enabled"     : false, // Turn off achievements tracking / UX
  "autoClosingPairs.enabled" : false, // disable autoclosing pairs
  "commandline.mode"         : false, // Do not override commandline UI
  "editor.completions.mode": "native",
  "editor.fontFamily": "Hack Nerd Font",
  "editor.fontSize": "13px",
  "editor.scrollBar.visible": false,
  "editor.textMateHighlighting.enabled" : false, // Use vim syntax highlighting
  "editor.typingPrediction"  : false, // Wait for vim's confirmed typed characters, avoid edge cases
  "experimental.indentLines.enabled": true,
  "learning.enabled"         : false, // Turn off learning pane
  "oni.hideMenu"             : "hidden", // Hide top bar menu
  "oni.loadInitVim"          : true, // Load user's init.vim
  "oni.useDefaultConfig"     : false, // Do not load Oni's init.vim
  "sidebar.default.open"     : false, // the side bar collapse 
  "sidebar.enabled"          : false, // sidebar ui is gone
  "statusbar.enabled"        : false, // use vim's default statusline
  "tabs.mode"                : "native", // Use vim's tabline, need completely quit Oni and restart a few times
  "terminal.shellCommand": "/bin/zsh",
  "ui.animations.enabled": true,
  "ui.colorscheme"           : "n/a", // Load init.vim colorscheme, remove this line if wants Oni's default
  "ui.fontFamily": "Hack Nerd Font",
  "ui.fontSize": "13px",
  "ui.fontSmoothing": "auto",
  "wildmenu.mode"            : false, // Do not override wildmenu UI,
  "environment.additionalPaths": [ 
    "/usr/bin", 
    "/Users/jlane/go/bin", 
    "/usr/local/bin", 
  ]
}
