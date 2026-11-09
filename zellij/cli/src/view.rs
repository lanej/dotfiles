use lane_zellij_protocol::StatusView;
use std::ffi::CStr;
#[cfg(any(not(target_os = "macos"), test))]
use std::fs;
#[cfg(any(not(target_os = "macos"), test))]
use std::path::Path;

pub fn view(session: Option<&str>) -> StatusView {
    StatusView {
        session: session.map(str::to_owned),
        auto_titles: session.map(crate::titles::owned_titles).unwrap_or_default(),
        host: hostname(),
        clock: clock(),
        battery: battery(),
    }
}

fn hostname() -> String {
    let mut bytes = [0 as libc::c_char; 256];
    // SAFETY: bytes is a writable buffer of the given size. Reserve a NUL byte.
    if unsafe { libc::gethostname(bytes.as_mut_ptr(), bytes.len() - 1) } != 0 {
        return String::new();
    }
    // SAFETY: the final byte remains zero even if gethostname truncates.
    unsafe { CStr::from_ptr(bytes.as_ptr()) }
        .to_string_lossy()
        .split('.')
        .next()
        .unwrap_or_default()
        .to_owned()
}

fn clock() -> String {
    // SAFETY: time accepts a null output pointer; localtime_r initializes the tm.
    unsafe {
        let now = libc::time(std::ptr::null_mut());
        let mut local = std::mem::MaybeUninit::<libc::tm>::uninit();
        if libc::localtime_r(&now, local.as_mut_ptr()).is_null() {
            return String::new();
        }
        let local = local.assume_init();
        format!("{:02}:{:02}", local.tm_hour, local.tm_min)
    }
}

#[cfg(target_os = "macos")]
fn battery() -> String {
    use std::time::{Duration, Instant};
    crate::command::output(
        "pmset",
        &["-g", "batt"],
        Instant::now() + Duration::from_secs(2),
    )
    .ok()
    .and_then(|output| battery_percentage(&output))
    .unwrap_or_default()
}

#[cfg(not(target_os = "macos"))]
fn battery() -> String {
    linux_battery(Path::new("/sys/class/power_supply"))
}

#[cfg(any(target_os = "macos", test))]
fn battery_percentage(output: &str) -> Option<String> {
    for (end, _) in output.match_indices('%') {
        let start = output.as_bytes()[..end]
            .iter()
            .rposition(|byte| !byte.is_ascii_digit())
            .map_or(0, |index| index + 1);
        if start < end {
            return Some(output[start..=end].to_owned());
        }
    }
    None
}

#[cfg(any(not(target_os = "macos"), test))]
fn linux_battery(root: &Path) -> String {
    let Ok(entries) = fs::read_dir(root) else {
        return String::new();
    };
    for entry in entries.filter_map(Result::ok) {
        if !entry.file_name().to_string_lossy().starts_with("BAT") {
            continue;
        }
        if let Some(capacity) = fs::read_to_string(entry.path().join("capacity"))
            .ok()
            .and_then(|text| text.trim().parse::<i64>().ok())
        {
            return format!("{capacity}%");
        }
    }
    String::new()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_pmset_battery_without_matching_other_numbers() {
        assert_eq!(
            battery_percentage(
                "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=123) 87%; discharging"
            ),
            Some("87%".into())
        );
        assert_eq!(battery_percentage("No batteries %"), None);
    }
    #[test]
    fn reads_linux_capacity_and_skips_invalid_batteries() {
        let root = std::env::temp_dir().join(format!("lane-battery-{}", std::process::id()));
        fs::create_dir_all(root.join("BAT0")).unwrap();
        fs::create_dir_all(root.join("BAT1")).unwrap();
        fs::write(root.join("BAT0/capacity"), "invalid").unwrap();
        fs::write(root.join("BAT1/capacity"), " 42\n").unwrap();
        assert_eq!(linux_battery(&root), "42%");
        fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn absent_session_serializes_as_null() {
        let value = serde_json::to_value(view(None)).unwrap();
        assert!(value["session"].is_null());
        assert_eq!(value["auto_titles"], serde_json::json!({}));
        assert_eq!(value["clock"].as_str().unwrap().len(), 5);
    }
}
