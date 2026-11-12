# Radar icons

Upstream icons are stored locally so the radar works without third-party image requests. Upstream artwork is unmodified except for the Simple Icons glyphs, which use the shared sage tile treatment described below. Project names and marks identify their respective projects.

| Asset | Pinned source | License |
| --- | --- | --- |
| neovim.png | [neovim/neovim](https://github.com/neovim/neovim/blob/629e501cd6112e5d77301afa01f5fcfd531b9ea0/runtime/nvim.png) | [Neovim license](LICENSE-neovim.txt) |
| kitty.png | [kovidgoyal/kitty](https://github.com/kovidgoyal/kitty/blob/6d8f7ac14ff14757b87977cc0b177ef0274e3759/logo/kitty-128.png) | [GPL-3.0](LICENSE-kitty.txt) |
| yabai.png | [koekeishiya/yabai](https://github.com/koekeishiya/yabai/blob/dd845723416f5fe92af49fad5ebab00369e07edd/assets/icon/1x/icon-128px.png) | [MIT](LICENSE-yabai.txt) |
| zellij.png | [zellij-org/zellij](https://github.com/zellij-org/zellij/blob/c8585459c37186fae1321727ad8dd4c96480ef41/zellij-utils/assets/icons/logo128.png) | [MIT](LICENSE-zellij.txt) |
| ghostty.png | [ghostty-org/ghostty](https://github.com/ghostty-org/ghostty/blob/2693982f8e20186c9a1e1c59dfb97f41ef3f57a0/images/icons/icon_128.png) | [MIT](LICENSE-ghostty.txt) |
| aerospace.png | [nikitabobko/AeroSpace](https://github.com/nikitabobko/AeroSpace/blob/0d498debee6c5bf4571124fe9851dbfaee427137/docs/assets/icon.png) | [MIT](LICENSE-aerospace.txt) |
| opencode.png | [anomalyco/opencode](https://github.com/anomalyco/opencode/blob/92265ca63733cdbc6b0a8c9c560005e6f983c474/packages/app/public/favicon-96x96.png) | [MIT](LICENSE-opencode.txt) |
| viewrule.png | [lanej/viewrule](https://github.com/lanej/viewrule/blob/15d95d32ad345290d0508cb20fa7f8aa07b70e9a/docs/brand/viewrule-logo.png) | [MIT](LICENSE-viewrule.txt) |
| paseo.png | [getpaseo/paseo](https://github.com/getpaseo/paseo/blob/4df5307eaab6b22d06fe54a45c68211b3413f45c/packages/app/assets/images/favicon.png) | [Apache-2.0](LICENSE-paseo.txt) |
| pi.svg | [earendil-works/pi](https://github.com/earendil-works/pi/blob/b22e525b325ff1934b4110f7fc60426fd6f0a8f3/apps/p2/public/icons/favicon.svg) | [MIT](LICENSE-pi.txt) |

The original symbolic illustrations identify Mergiraf (merge branches), Firstmate (anchor), Superpowers (bolt), andrej-karpathy-skills (book), and sccache (cache). The generic tool icon is used when a new radar entry has no assigned icon. These symbols are not upstream logos. Icon selection, ring placement, and decision text are maintained together in `docs/radar.yaml`. The generator produces `docs/radar.md` and the website diagram data.

## Core tool icons

The glyphs for [bat.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/bat.svg), [claude.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/claude.svg), [git.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/git.svg), [github.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/github.svg), [just.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/just.svg), [starship.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/starship.svg), [tmux.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/tmux.svg), [zsh.svg](https://github.com/simple-icons/simple-icons/blob/cd796c98565fc466923fc1128b962e133fa3c612/icons/zsh.svg) come from Simple Icons under [CC0](LICENSE-simple-icons.txt). They are recolored and placed on the same sage tiles as the original symbols.

The fzf lettermark and symbols for Atuin (history), fd (file finding), eza (tree), ripgrep (text search), direnv (directory environment), delta (diff), jq (JSON), yq (YAML), and Codex (code) are original identification aids, not upstream logos. They remain identical across the plot, legend, and tool heading.
