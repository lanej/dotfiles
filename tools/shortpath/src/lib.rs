use std::collections::HashMap;
use std::ffi::OsString;
use std::fs;
use std::io;
use std::path::{Component, Path, PathBuf};

#[derive(Clone, Copy)]
pub struct Options {
    pub min_length: usize,
    pub keep: usize,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            min_length: 1,
            keep: 1,
        }
    }
}

#[derive(Default)]
pub struct Shortener {
    siblings: HashMap<PathBuf, Vec<OsString>>,
}

impl Shortener {
    /// Produce a display label using a snapshot of each parent directory.
    /// Relative paths are interpreted against the caller's working directory.
    pub fn shorten(&mut self, input: &str, options: Options) -> io::Result<String> {
        if input.is_empty() || options.min_length == 0 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "path must be nonempty and minimum length must be positive",
            ));
        }
        let path = Path::new(input);
        fs::symlink_metadata(path)?;
        let count = path
            .components()
            .filter(|c| matches!(c, Component::Normal(_)))
            .count();
        let shorten_count = count.saturating_sub(options.keep);
        let mut original = PathBuf::new();
        let mut display = PathBuf::new();
        let mut index = 0;
        for component in path.components() {
            if let Component::Normal(name) = component {
                if index < shorten_count {
                    let parent = if original.as_os_str().is_empty() {
                        Path::new(".")
                    } else {
                        &original
                    };
                    if !self.siblings.contains_key(parent) {
                        let entries = fs::read_dir(parent)?
                            .map(|entry| entry.map(|entry| entry.file_name()))
                            .collect::<io::Result<Vec<_>>>()?;
                        self.siblings.insert(parent.to_path_buf(), entries);
                    }
                    let name = name.to_str().ok_or_else(|| {
                        io::Error::new(io::ErrorKind::InvalidInput, "path must be UTF-8")
                    })?;
                    display.push(unique_prefix(
                        name,
                        &self.siblings[parent],
                        options.min_length,
                    ));
                } else {
                    display.push(name);
                }
                index += 1;
            } else {
                display.push(component.as_os_str());
            }
            // WHY: Read subsequent siblings through the original path, including symlinks and '..'.
            original.push(component.as_os_str());
        }
        let mut result = display
            .into_os_string()
            .into_string()
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "path must be UTF-8"))?;
        if input.ends_with(std::path::MAIN_SEPARATOR)
            && !result.ends_with(std::path::MAIN_SEPARATOR)
        {
            result.push(std::path::MAIN_SEPARATOR);
        }
        Ok(result)
    }
}

fn unique_prefix<'a>(name: &'a str, siblings: &[OsString], minimum: usize) -> &'a str {
    // WHY: An unrepresentable sibling could share a prefix; retain the full name conservatively.
    let Some(siblings) = siblings
        .iter()
        .map(|s| s.to_str())
        .collect::<Option<Vec<_>>>()
    else {
        return name;
    };
    for (index, (offset, character)) in name.char_indices().enumerate() {
        if index + 1 < minimum {
            continue;
        }
        let prefix = &name[..offset + character.len_utf8()];
        if prefix != "."
            && prefix != ".."
            && !siblings
                .iter()
                .any(|sibling| *sibling != name && sibling.starts_with(prefix))
        {
            return prefix;
        }
    }
    name
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;
    use std::os::unix::ffi::OsStringExt;

    #[test]
    fn non_utf8_sibling_preserves_full_component() {
        let siblings = vec![
            OsString::from("normal"),
            OsString::from_vec(b"no\xff".to_vec()),
        ];
        assert_eq!(unique_prefix("normal", &siblings, 1), "normal");
    }
}
