"use strict";
exports.__esModule = true;
exports.activate = function (oni) {
    oni.input.unbind("<c-g>"); // make C-g work as expected in vim
    oni.input.unbind("<c-v>"); // make C-v work as expected in vim
    oni.input.bind("<s-c-g>", function () { return oni.commands.executeCommand("sneak.show"); }); // You can rebind Oni's behaviour to a new keybinding
};
exports.configuration = {
    activate: exports.activate,
    "achievements.enabled": false,
    "autoClosingPairs.enabled": false,
    "commandline.mode": false,
    "editor.completions.mode": "native",
    "editor.fontFamily": "Hack Nerd Font",
    "editor.fontSize": "13px",
    "editor.scrollBar.visible": false,
    "editor.textMateHighlighting.enabled": false,
    "editor.typingPrediction": false,
    "experimental.indentLines.enabled": true,
    "learning.enabled": false,
    "oni.hideMenu": "hidden",
    "oni.loadInitVim": true,
    "oni.useDefaultConfig": false,
    "sidebar.default.open": false,
    "sidebar.enabled": false,
    "statusbar.enabled": false,
    "tabs.mode": "native",
    "terminal.shellCommand": "/bin/zsh",
    "ui.animations.enabled": true,
    "ui.colorscheme": "n/a",
    "ui.fontFamily": "Hack Nerd Font",
    "ui.fontSize": "13px",
    "ui.fontSmoothing": "auto",
    "wildmenu.mode": false,
    "environment.additionalPaths": [
        "/usr/bin",
        "/Users/jlane/go/bin",
        "/usr/local/bin",
    ]
};
