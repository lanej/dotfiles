//! Host telemetry on the right side of the status row.
use crate::{bar::Ribbon, clipped, plain};
use lane_zellij_protocol::{BatteryReading, PowerState, StatusView};
use unicode_width::UnicodeWidthStr;
use zellij_tile::prelude::*;

#[derive(Default)]
pub(crate) struct RightSide {
    spans: Vec<(String, PaletteColor, bool)>,
    width: usize,
}

impl RightSide {
    fn push(&mut self, text: &str, color: PaletteColor, bold: bool) {
        if !text.is_empty() {
            self.width += text.width();
            self.spans.push((text.to_owned(), color, bold));
        }
    }
    pub fn width(&self) -> usize {
        self.width
    }
    pub fn draw(&self, bg: PaletteColor) {
        for (text, fg, bold) in &self.spans {
            Ribbon {
                fg: *fg,
                bg,
                bold: *bold,
            }
            .paint(text);
        }
    }
}

fn battery(
    reading: BatteryReading,
    ascii: bool,
    colors: Styling,
) -> Option<(String, String, PaletteColor, bool)> {
    use PowerState::*;
    let n = reading.percent;
    if n > 100 || reading.state == Idle {
        return None;
    }
    let (color, bold) = match reading.state {
        Charging => (colors.exit_code_success.base, false),
        Discharging if n < 10 => (colors.exit_code_error.base, true),
        Discharging if n < 20 => (colors.ribbon_unselected.emphasis_0, true),
        Discharging => (colors.text_unselected.emphasis_0, false),
        _ => (colors.ribbon_unselected.base, false),
    };
    let icon = match (reading.state, ascii) {
        (Charging, true) => "AC+",
        (_, true) => "BAT",
        (Charging, false) => "󰂄",
        _ => match n {
            0..=10 => "",
            11..=35 => "",
            36..=60 => "",
            61..=85 => "",
            _ => "",
        },
    };
    let short = format!("{icon} {n}%");
    let full = reading.remaining_minutes.filter(|n| *n > 0).map_or_else(
        || short.clone(),
        |m| format!("{short} {}:{:02}", m / 60, m % 60),
    );
    Some((short, full, color, bold))
}

pub(crate) fn right_side(
    view: &StatusView,
    mode: &ModeInfo,
    counts: &str,
    notice: Option<(&str, PaletteColor)>,
    cols: usize,
    ideal_left: usize,
    compact_left: usize,
) -> RightSide {
    let mut out = RightSide::default();
    let colors = mode.style.colors;
    let normal = colors.ribbon_unselected.base;
    let budget = cols.saturating_sub((cols / 3).clamp(20, 48) + 2);
    let counts = clipped(counts, budget);
    let prefix_cost = if counts.is_empty() {
        0
    } else {
        counts.width() + 3
    };
    let space = budget.saturating_sub(prefix_cost);
    let gap = " │ ";
    out.push(" ", normal, false);
    if let Some((message, color)) = notice {
        if space >= 8 {
            let text = clipped(&plain(message), space.min(64));
            out.push(&text, color, false);
            if !text.is_empty() && !counts.is_empty() {
                out.push(gap, normal, false);
            }
        }
        out.push(&counts, normal, false);
    } else {
        out.push(&counts, normal, false);
        let remote = mode
            .remote_client
            .as_deref()
            .is_some_and(|loc| loc.starts_with("from a terminal, over SSH"));
        let ascii = mode.capabilities.arrow_fonts;
        let host = clipped(&plain(&view.host), 20);
        let host = if remote && !host.is_empty() {
            format!("{} {host}", if ascii { "SSH" } else { "" })
        } else {
            host
        };
        let clock = plain(&view.clock);
        // Older helpers still publish the bare percentage.
        let power = view.power.or_else(|| {
            Some(BatteryReading {
                percent: view.battery.strip_suffix('%')?.parse().ok()?,
                state: PowerState::Unknown,
                remaining_minutes: None,
            })
        });
        let (short, full, battery_color, bold) = power
            .and_then(|p| battery(p, ascii, colors))
            .unwrap_or((String::new(), String::new(), normal, false));
        let room = |left| {
            if cols < 48 {
                0
            } else {
                space.min(cols.saturating_sub(left + prefix_cost + 2))
            }
        };
        let generous = room(ideal_left);
        let compact = room(compact_left);
        let host_only = if remote { host.as_str() } else { "" };
        let choices = [
            ([full.as_str(), clock.as_str(), host.as_str()], generous),
            ([short.as_str(), clock.as_str(), host.as_str()], generous),
            ([short.as_str(), "", host.as_str()], generous),
            ([short.as_str(), "", host_only], compact),
            (["", "", host_only], compact),
            ([short.as_str(), "", ""], compact),
        ];
        for (parts, budget) in choices {
            let n = parts.iter().filter(|s| !s.is_empty()).count();
            let width = parts.iter().map(|s| s.width()).sum::<usize>() + 2 * n.saturating_sub(1);
            if n == 0 || width > budget {
                continue;
            }
            if !counts.is_empty() {
                out.push(gap, normal, false);
            }
            let mut first = true;
            for (i, text) in parts.into_iter().enumerate().filter(|(_, s)| !s.is_empty()) {
                if !first {
                    out.push("  ", normal, false);
                }
                let color = match i {
                    0 => battery_color,
                    2 if remote => colors.text_unselected.emphasis_1,
                    _ => normal,
                };
                out.push(text, color, i == 0 && bold);
                first = false;
            }
            break;
        }
    }
    if out.width == 1 {
        return RightSide::default();
    }
    out.push(" ", normal, false);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ssh_follows_the_attached_client_and_idle_battery_disappears() {
        let mut mode = ModeInfo::default();
        mode.capabilities.arrow_fonts = false;
        let mut view = StatusView {
            host: "dev".into(),
            clock: "12:34".into(),
            power: Some(BatteryReading {
                percent: 12,
                state: PowerState::Discharging,
                remaining_minutes: Some(36),
            }),
            ..Default::default()
        };
        let text = |side: RightSide| side.spans.into_iter().map(|s| s.0).collect::<String>();
        for (location, lock) in [
            (Some("from a terminal, over SSH from 192.0.2.1"), true),
            (Some("from a terminal"), false),
            (Some("through the web server"), false),
            (None, false),
        ] {
            mode.remote_client = location.map(str::to_owned);
            let rendered = text(right_side(&view, &mode, "", None, 100, 25, 20));
            assert_eq!(rendered.contains(" dev"), lock);
            assert!(rendered.contains("12% 0:36"));
            assert!(!rendered.contains("192.0.2.1"));
        }
        view.power.as_mut().unwrap().state = PowerState::Idle;
        assert!(!text(right_side(&view, &mode, "", None, 100, 25, 20)).contains('%'));
    }
    #[test]
    fn notices_and_long_hosts_leave_space_for_the_selected_title() {
        let mode = ModeInfo::default();
        let view = StatusView {
            host: "界".repeat(90),
            ..Default::default()
        };
        for cols in 0..140 {
            for notice in [
                None,
                Some(("copy\x1b\nfailure", mode.style.colors.exit_code_error.base)),
            ] {
                let right = right_side(&view, &mode, "!1 ✓2", notice, cols, 45, 25);
                assert!(right.width() <= cols.saturating_sub(20));
                assert!(right
                    .spans
                    .iter()
                    .all(|(s, _, _)| !s.chars().any(char::is_control)));
            }
        }
    }

    #[test]
    fn a_long_local_hostname_leaves_room_for_the_other_tabs() {
        let mode = ModeInfo::default();
        let view = StatusView {
            host: "iad20-fj923-6e82d2dd-e876-49ef-9c4d-8400bb225283".into(),
            clock: "12:34".into(),
            ..Default::default()
        };
        let bar = right_side(&view, &mode, "!2 ●2", None, 120, 97, 39);
        assert_eq!(bar.spans.into_iter().map(|s| s.0).collect::<String>(), " !2 ●2 ");
    }
}
