use crate::completion::Suggestion;
use std::{path::PathBuf, time::Instant};
use zellij_tile::prelude::*;

mod glyphs {
    include!("../../../design-system/generated/zellij-symbols.rs");
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Query {
    pub directory: PathBuf,
    prefix: String,
    parent: String,
    directories_only: bool,
}

impl Query {
    pub fn new(prefix: &str, cwd: &std::path::Path, directories_only: bool) -> Self {
        let parent = prefix.rfind('/').map_or("", |i| &prefix[..=i]);
        let path = PathBuf::from(parent);
        Self {
            directory: if path.is_absolute() {
                path
            } else {
                cwd.join(path)
            },
            prefix: prefix.into(),
            parent: parent.into(),
            directories_only,
        }
    }

    fn choices(&self, paths: Vec<(PathBuf, Option<FileMetadata>)>) -> Vec<Suggestion> {
        let mut items = paths
            .into_iter()
            .filter_map(|(path, metadata)| {
                let name = path.file_name()?.to_str()?;
                let directory = metadata.is_some_and(|m| m.is_dir);
                if self.directories_only && !directory {
                    return None;
                }
                let value = format!("{}{name}{}", self.parent, if directory { "/" } else { "" });
                value.starts_with(&self.prefix).then(|| {
                    Suggestion::new(
                        value,
                        name,
                        if directory {
                            glyphs::DIRECTORY
                        } else {
                            glyphs::REGULAR
                        },
                    )
                })
            })
            .take(512)
            .collect::<Vec<_>>();
        items.sort_by(|a, b| a.value.cmp(&b.value));
        items
    }
}

#[derive(Clone)]
pub struct Choices {
    pub query: Query,
    pub items: Vec<Suggestion>,
}

struct Pending {
    query: Query,
    line: String,
    cursor: usize,
    started: Instant,
}

#[derive(Default)]
pub struct Lookup {
    pending: Option<Pending>,
    timed_out: bool,
}

impl Lookup {
    pub fn start(&mut self, query: Query, line: &str, cursor: usize) -> Result<(), &'static str> {
        if self.timed_out {
            return Err("File lookup timed out; reopen the palette to retry.");
        }
        if self.pending.is_some() {
            return Err("Directory lookup is still running. Keep editing or cancel.");
        }
        change_host_folder(query.directory.clone());
        self.pending = Some(Pending {
            query,
            line: line.into(),
            cursor,
            started: Instant::now(),
        });
        set_timeout(5.0);
        Ok(())
    }

    pub fn finish(
        &mut self,
        paths: Vec<(PathBuf, Option<FileMetadata>)>,
        line: &str,
        cursor: usize,
    ) -> Option<Choices> {
        let pending = self.pending.take()?;
        if pending.line != line || pending.cursor != cursor {
            return None;
        }
        Some(Choices {
            items: pending.query.choices(paths),
            query: pending.query,
        })
    }

    pub fn failed(&mut self) {
        self.pending = None;
    }

    pub fn timeout(&mut self) -> bool {
        if self
            .pending
            .as_ref()
            .is_some_and(|p| p.started.elapsed().as_secs() >= 5)
        {
            self.pending = None;
            // NOTE: Native scan events have no request ID; a fresh popup excludes late results.
            self.timed_out = true;
            true
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn directory_mount_preserves_quoted_relative_and_symlink_prefixes() {
        let query = Query::new(
            "../linked/notes ",
            std::path::Path::new("/work/project"),
            false,
        );
        assert_eq!(query.directory, PathBuf::from("/work/project/../linked/"));
        let items = query.choices(vec![(
            "/host/notes one.txt".into(),
            Some(FileMetadata::default()),
        )]);
        assert_eq!(items[0].value, "../linked/notes one.txt");
        assert_eq!(
            shlex::split(&crate::completion::quote(&items[0].value)).unwrap(),
            ["../linked/notes one.txt"]
        );
    }

    #[test]
    fn cwd_filters_files_and_stale_results_cannot_replace_newer_input() {
        let query = Query::new("", std::path::Path::new("/work"), true);
        assert!(query
            .choices(vec![(
                "/host/notes.txt".into(),
                Some(FileMetadata::default())
            )])
            .is_empty());
        let mut lookup = Lookup {
            pending: Some(Pending {
                query,
                line: "edit n".into(),
                cursor: 6,
                started: Instant::now(),
            }),
            timed_out: false,
        };
        assert!(lookup.finish(vec![], "edit nx", 7).is_none());
        assert!(lookup.pending.is_none());
    }
}
