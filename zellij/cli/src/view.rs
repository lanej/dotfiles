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
    macos::battery()
}

#[cfg(target_os = "macos")]
mod macos {
    use super::{BatteryReading, PowerState};
    use std::ffi::{c_char, c_void, CStr};
    use std::ptr;

    type Ref = *const c_void;
    #[link(name = "IOKit", kind = "framework")]
    extern "C" {
        fn IOPSCopyPowerSourcesInfo() -> Ref;
        fn IOPSCopyPowerSourcesList(info: Ref) -> Ref;
        fn IOPSGetPowerSourceDescription(info: Ref, source: Ref) -> Ref;
    }
    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        fn CFRelease(value: Ref);
        fn CFGetTypeID(value: Ref) -> usize;
        fn CFArrayGetCount(array: Ref) -> isize;
        fn CFArrayGetValueAtIndex(array: Ref, index: isize) -> Ref;
        fn CFDictionaryGetValue(dictionary: Ref, key: Ref) -> Ref;
        fn CFStringCreateWithCString(allocator: Ref, value: *const c_char, encoding: u32) -> Ref;
        fn CFStringGetTypeID() -> usize;
        fn CFStringGetCString(value: Ref, buffer: *mut c_char, size: isize, encoding: u32) -> bool;
        fn CFNumberGetTypeID() -> usize;
        fn CFNumberGetValue(value: Ref, kind: isize, output: *mut i64) -> bool;
        fn CFBooleanGetTypeID() -> usize;
        fn CFBooleanGetValue(value: Ref) -> bool;
    }

    struct Owned(Ref);
    impl Owned {
        fn new(value: Ref) -> Option<Self> {
            (!value.is_null()).then_some(Self(value))
        }
    }
    impl Drop for Owned {
        fn drop(&mut self) {
            // SAFETY: Owned contains a non-null CoreFoundation Copy/Create result.
            unsafe { CFRelease(self.0) };
        }
    }

    // These values borrow the power-source snapshot, which outlives every lookup.
    struct Description(Ref);
    impl Description {
        fn value(&self, key: &CStr) -> Option<Ref> {
            // SAFETY: key is NUL terminated UTF-8; the dictionary is owned by the snapshot.
            unsafe {
                let key = Owned::new(CFStringCreateWithCString(
                    ptr::null(),
                    key.as_ptr(),
                    0x08000100,
                ))?;
                let value = CFDictionaryGetValue(self.0, key.0);
                (!value.is_null()).then_some(value)
            }
        }
        fn number(&self, key: &CStr) -> Option<i64> {
            let value = self.value(key)?;
            // SAFETY: type checking precedes reading a signed 64-bit CFNumber (type 4).
            unsafe {
                let mut result = 0;
                (CFGetTypeID(value) == CFNumberGetTypeID()
                    && CFNumberGetValue(value, 4, &mut result))
                .then_some(result)
            }
        }
        fn boolean(&self, key: &CStr) -> Option<bool> {
            let value = self.value(key)?;
            // SAFETY: only CFBoolean values are read as booleans.
            unsafe {
                (CFGetTypeID(value) == CFBooleanGetTypeID()).then(|| CFBooleanGetValue(value))
            }
        }
        fn string(&self, key: &CStr) -> Option<String> {
            let value = self.value(key)?;
            // SAFETY: type checking precedes UTF-8 conversion into a bounded buffer.
            unsafe {
                let mut buffer = [0 as c_char; 64];
                if CFGetTypeID(value) != CFStringGetTypeID()
                    || !CFStringGetCString(
                        value,
                        buffer.as_mut_ptr(),
                        buffer.len() as isize,
                        0x08000100,
                    )
                {
                    return None;
                }
                Some(
                    CStr::from_ptr(buffer.as_ptr())
                        .to_string_lossy()
                        .into_owned(),
                )
            }
        }
    }

    pub(super) fn battery() -> Option<BatteryReading> {
        // SAFETY: IOKit Copy results are released after all borrowed array/dictionary values.
        unsafe {
            let info = Owned::new(IOPSCopyPowerSourcesInfo())?;
            let sources = Owned::new(IOPSCopyPowerSourcesList(info.0))?;
            (0..CFArrayGetCount(sources.0)).find_map(|index| {
                let source = CFArrayGetValueAtIndex(sources.0, index);
                let description = IOPSGetPowerSourceDescription(info.0, source);
                if description.is_null() {
                    return None;
                }
                let description = Description(description);
                if description.string(c"Type").as_deref() != Some("InternalBattery")
                    || description.boolean(c"Is Present") != Some(true)
                {
                    return None;
                }
                reading(
                    description.number(c"Current Capacity")?,
                    description.number(c"Max Capacity")?,
                    description.boolean(c"Is Charging"),
                    description.string(c"Power Source State").as_deref(),
                    description.number(c"Time to Empty"),
                    description.number(c"Time to Full Charge"),
                )
            })
        }
    }

    fn reading(
        current: i64,
        maximum: i64,
        charging: Option<bool>,
        source: Option<&str>,
        empty: Option<i64>,
        full: Option<i64>,
    ) -> Option<BatteryReading> {
        if maximum <= 0 || current < 0 || current > maximum {
            return None;
        }
        let percent = u8::try_from(current.checked_mul(100)? / maximum).ok()?;
        let state = match (charging, source) {
            (Some(true), _) => PowerState::Charging,
            (Some(false), Some("Battery Power")) => PowerState::Discharging,
            (Some(false), Some("AC Power")) => PowerState::Idle,
            _ => PowerState::Unknown,
        };
        let remaining_minutes = match state {
            PowerState::Charging => full,
            PowerState::Discharging => empty,
            _ => None,
        }
        .and_then(|minutes| u32::try_from(minutes).ok());
        Some(BatteryReading {
            percent,
            state,
            remaining_minutes,
        })
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        #[test]
        fn reads_capacity_charge_transitions_and_unknown_estimates() {
            for (charging, source, state, minutes) in [
                (Some(true), Some("AC Power"), PowerState::Charging, Some(31)),
                (
                    Some(false),
                    Some("Battery Power"),
                    PowerState::Discharging,
                    Some(285),
                ),
                (Some(false), Some("AC Power"), PowerState::Idle, None),
                (None, None, PowerState::Unknown, None),
            ] {
                assert_eq!(
                    reading(4350, 5000, charging, source, Some(285), Some(31)),
                    Some(BatteryReading {
                        percent: 87,
                        state,
                        remaining_minutes: minutes
                    })
                );
            }
            for estimate in [None, Some(-1)] {
                assert_eq!(
                    reading(87, 100, Some(false), Some("Battery Power"), estimate, None)
                        .unwrap()
                        .remaining_minutes,
                    None
                );
            }
            assert_eq!(
                reading(0, 100, Some(false), Some("Battery Power"), Some(0), None)
                    .unwrap()
                    .remaining_minutes,
                Some(0)
            );
            for (current, maximum) in [(-1, 100), (101, 100), (0, 0), (0, -1), (i64::MAX, i64::MAX)]
            {
                assert!(reading(current, maximum, None, None, None, None).is_none());
            }
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn battery() -> Option<BatteryReading> {
    linux_battery(Path::new("/sys/class/power_supply"))
}

#[cfg(any(not(target_os = "macos"), test))]
fn percent(value: &str) -> Option<u8> {
    value.trim().parse::<u8>().ok().filter(|n| *n <= 100)
}

#[cfg(any(not(target_os = "macos"), test))]
fn power_state(value: &str) -> PowerState {
    match value.trim().to_ascii_lowercase().as_str() {
        "discharging" => PowerState::Discharging,
        "charging" | "finishing charge" => PowerState::Charging,
        "charged" | "full" | "not charging" | "ac attached" => PowerState::Idle,
        _ => PowerState::Unknown,
    }
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
