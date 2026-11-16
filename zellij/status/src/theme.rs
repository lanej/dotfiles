use zellij_tile::prelude::PaletteColor;

pub fn foreground(color: PaletteColor) -> String {
    match color {
        PaletteColor::Rgb((r, g, b)) => format!("38;2;{r};{g};{b}"),
        PaletteColor::EightBit(index) => format!("38;5;{index}"),
    }
}

pub fn background(color: PaletteColor) -> String {
    match color {
        PaletteColor::Rgb((r, g, b)) => format!("48;2;{r};{g};{b}"),
        PaletteColor::EightBit(index) => format!("48;5;{index}"),
    }
}
