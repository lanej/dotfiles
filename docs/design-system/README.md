# Catalog symbol font

`symbols.woff2` contains only the default presentation-token characters from Hack Nerd Font Mono Regular, patched by Nerd Fonts v3.5.1. Its source is `HackNerdFontMono-Regular.ttf` in the [Nerd Fonts v3.5.1 Hack release](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1/Hack.zip). The subset retains font license metadata; [SYMBOLS-LICENSE.txt](SYMBOLS-LICENSE.txt) includes the Hack, Font Awesome, Octicons and Powerline Symbols license texts from that version.

To regenerate after adding default symbols, supply that source font explicitly:

```sh
uv run --script scripts/theme-symbol-font.py /path/to/HackNerdFontMono-Regular.ttf
```

Font generation is separate from native theme generation and startup. Preset overrides are not added automatically to the font; the catalog prints Unicode values alongside symbol previews to identify glyphs outside the bundled subset. Font rendering in the browser does not establish glyph availability or width in a native terminal.
