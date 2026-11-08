use zellij_tile::prelude::{AttentionStatus, PaletteColor, Styling};

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

pub fn mark(status: AttentionStatus, question: bool, colors: &Styling) -> (&'static str, PaletteColor) {
    match status {
        AttentionStatus::NeedsYou if question => ("?", colors.text_unselected.emphasis_0),
        AttentionStatus::NeedsYou => ("!", colors.text_unselected.emphasis_0),
        AttentionStatus::Failed => ("×", colors.exit_code_error.base),
        AttentionStatus::Done => ("✓", colors.exit_code_success.base),
        AttentionStatus::Working => ("●", colors.text_unselected.emphasis_1),
        AttentionStatus::NewOutput => ("·", colors.text_unselected.emphasis_1),
        _ => ("", colors.ribbon_unselected.base),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use zellij_tile::prelude::ModeInfo;

    #[test]
    fn received_native_styles_own_attention_colors() {
        let mut colors = ModeInfo::default().style.colors;
        colors.exit_code_error.base = PaletteColor::Rgb((11, 22, 33));
        assert_eq!(foreground(mark(AttentionStatus::Failed, false, &colors).1), "38;2;11;22;33");
        colors.exit_code_error.base = PaletteColor::EightBit(42);
        assert_eq!(foreground(mark(AttentionStatus::Failed, false, &colors).1), "38;5;42");
        assert_eq!(background(PaletteColor::EightBit(17)), "48;5;17");
    }
}
