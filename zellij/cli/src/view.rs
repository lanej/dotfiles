use lane_zellij_protocol::{BatteryReading, PowerState, StatusView};
use std::ffi::CStr;
#[cfg(any(not(target_os = "macos"), test))]
use std::fs;
#[cfg(any(not(target_os = "macos"), test))]
use std::path::Path;

pub fn view(session: Option<&str>) -> StatusView {
    let power = battery();
    StatusView {
        session: session.map(str::to_owned),
        auto_titles: session.map(crate::titles::owned_titles).unwrap_or_default(),
        host: hostname(),
        clock: clock(),
        battery: power.map(|b| format!("{}%", b.percent)).unwrap_or_default(),
        power,
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
fn battery() -> Option<BatteryReading> {
    use std::time::{Duration, Instant};
    crate::command::output(
        "pmset",
        &["-g", "batt"],
        Instant::now() + Duration::from_secs(2),
    )
    .ok()
    .and_then(|output| mac_battery(&output))
}

#[cfg(not(target_os = "macos"))]
fn battery() -> Option<BatteryReading> {
    linux_battery(Path::new("/sys/class/power_supply"))
}

fn percent(value: &str) -> Option<u8> {
    value.trim().parse::<u8>().ok().filter(|n| *n <= 100)
}

fn power_state(value: &str) -> PowerState {
    match value.trim().to_ascii_lowercase().as_str() {
        "discharging" => PowerState::Discharging,
        "charging" | "finishing charge" => PowerState::Charging,
        "charged" | "full" | "not charging" | "ac attached" => PowerState::Idle,
        _ => PowerState::Unknown,
    }
}

#[cfg(any(target_os = "macos", test))]
fn mac_battery(output: &str) -> Option<BatteryReading> {
    output
        .lines()
        .filter(|line| line.contains("InternalBattery"))
        .find_map(|line| {
            let (device, details) = line.split_once('%')?;
            let percent = percent(device.split_whitespace().next_back()?)?;
            let state = details
                .split(';')
                .map(power_state)
                .find(|s| *s != PowerState::Unknown)
                .unwrap_or(PowerState::Unknown);
            let remaining_minutes = details.split_whitespace().find_map(|word| {
                let (h, m) = word.split_once(':')?;
                let minutes = m.parse::<u32>().ok().filter(|n| *n < 60)?;
                h.parse::<u32>().ok()?.checked_mul(60)?.checked_add(minutes)
            });
            Some(BatteryReading {
                percent,
                state,
                remaining_minutes,
            })
        })
}

#[cfg(any(not(target_os = "macos"), test))]
fn linux_battery(root: &Path) -> Option<BatteryReading> {
    let mut entries: Vec<_> = fs::read_dir(root).ok()?.filter_map(Result::ok).collect();
    entries.sort_by_key(|e| e.file_name());
    entries.into_iter().find_map(|entry| {
        let read = |key| fs::read_to_string(entry.path().join(key)).ok();
        let is_battery = read("type").map_or_else(
            || entry.file_name().to_string_lossy().starts_with("BAT"),
            |kind| kind.trim() == "Battery",
        );
        if !is_battery
            || read("scope").is_some_and(|s| s.trim() == "Device")
            || read("present").is_some_and(|s| s.trim() == "0")
        {
            return None;
        }
        let percent = percent(&read("capacity")?)?;
        let state = read("status")
            .as_deref()
            .map(power_state)
            .unwrap_or(PowerState::Unknown);
        let seconds = match state {
            PowerState::Charging => read("time_to_full_now"),
            PowerState::Discharging => read("time_to_empty_now"),
            _ => None,
        };
        let remaining_minutes = seconds
            .and_then(|s| s.trim().parse::<u32>().ok())
            .filter(|n| *n > 0)
            .map(|n| n / 60);
        Some(BatteryReading {
            percent,
            state,
            remaining_minutes,
        })
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reads_pmset_state_and_time_from_the_internal_battery() {
        for (details, state, minutes) in [
            (
                "discharging; 4:45 remaining",
                PowerState::Discharging,
                Some(285),
            ),
            (
                "charging; 0:31 until charged",
                PowerState::Charging,
                Some(31),
            ),
            ("charged; 0:00 remaining", PowerState::Idle, Some(0)),
            ("not charging; (no estimate)", PowerState::Idle, None),
        ] {
            let output = format!("Now drawing from 'AC Power'\n -InternalBattery-0 (id=123) 87%; {details} present: true");
            assert_eq!(
                mac_battery(&output),
                Some(BatteryReading {
                    percent: 87,
                    state,
                    remaining_minutes: minutes
                })
            );
        }
        assert!(mac_battery("No batteries").is_none());
    }
    #[test]
    fn reads_system_battery_and_skips_peripherals_and_bad_values() {
        let root = tempfile::tempdir().unwrap();
        for (name, capacity, scope) in [
            ("BAT0", "101", "System"),
            ("BAT1", "7", "Device"),
            ("CMB0", "42", "System"),
        ] {
            let path = root.path().join(name);
            fs::create_dir(&path).unwrap();
            for (file, val) in [
                ("type", "Battery"),
                ("scope", scope),
                ("capacity", capacity),
                ("status", "Discharging"),
                ("time_to_empty_now", "7380"),
            ] {
                fs::write(path.join(file), val).unwrap();
            }
        }
        assert_eq!(
            linux_battery(root.path()),
            Some(BatteryReading {
                percent: 42,
                state: PowerState::Discharging,
                remaining_minutes: Some(123)
            })
        );
    }
    #[test]
    fn absent_session_serializes_as_null() {
        let value = serde_json::to_value(view(None)).unwrap();
        assert!(value["session"].is_null());
        assert_eq!(value["auto_titles"], serde_json::json!({}));
        assert_eq!(value["clock"].as_str().unwrap().len(), 5);
    }
}
