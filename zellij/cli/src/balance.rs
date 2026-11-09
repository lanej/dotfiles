//! Bounded, single-shot boundary moves. Concurrent or ambiguous layouts stop the operation.
use crate::util::*;
use anyhow::{bail, Context, Result};
use serde::Deserialize;
use std::collections::{BTreeMap, HashSet};
use std::env;
use std::path::PathBuf;
use std::time::{Duration, Instant};
#[derive(Clone, Deserialize)]
struct Pane {
    id: i64,
    tab_id: i64,
    pane_x: i64,
    pane_y: i64,
    pane_columns: i64,
    pane_rows: i64,
    pane_content_columns: i64,
    is_plugin: bool,
    is_floating: bool,
    is_fullscreen: bool,
    is_suppressed: bool,
    is_collapsed: bool,
    exited: bool,
    index_in_pane_group: serde_json::Map<String, serde_json::Value>,
}
impl Pane {
    fn rect(&self) -> [i64; 4] {
        [self.pane_x, self.pane_y, self.pane_columns, self.pane_rows]
    }
    fn geometry(&self) -> [i64; 5] {
        [
            self.id,
            self.pane_x,
            self.pane_y,
            self.pane_columns,
            self.pane_rows,
        ]
    }
    fn valid(&self) -> bool {
        [
            self.id,
            self.tab_id,
            self.pane_x,
            self.pane_y,
            self.pane_columns,
            self.pane_rows,
            self.pane_content_columns,
        ]
        .iter()
        .all(|n| (0..=i32::MAX as i64).contains(n))
            && self.pane_columns > 0
            && self.pane_rows > 0
            && self.pane_content_columns <= self.pane_columns
    }
}
fn geometry(panes: &[Pane]) -> Vec<[i64; 5]> {
    panes.iter().map(Pane::geometry).collect()
}
fn neighboring(p: &Pane, q: &Pane, axis: usize) -> bool {
    let a = p.rect();
    let b = q.rect();
    p.id != q.id
        && b[axis] == a[axis] + a[axis + 2]
        && (b[1 - axis] + b[3 - axis]).min(a[1 - axis] + a[3 - axis]) > b[1 - axis].max(a[1 - axis])
}
struct Balance {
    session: String,
    origin: i64,
    tab: Option<i64>,
    deadline: Instant,
    stop: Instant,
    calls: u8,
    panes: Vec<Pane>,
}
impl Balance {
    fn action(&self, args: &[&str]) -> Result<String> {
        let mut command = vec!["action"];
        command.extend_from_slice(args);
        zellij(
            &self.session,
            &command,
            self.deadline.min(Instant::now() + Duration::from_secs(3)),
        )
        .context("Native command failed or timed out; stopped without retry")
    }
    fn snapshot(&mut self) -> Result<()> {
        let all: Vec<Pane> = serde_json::from_str(&self.action(&["list-panes", "--json"])?)?;
        if all.iter().any(|p| !p.valid()) {
            bail!("Unsupported layout or invalid pane metadata; skipped");
        }
        let origins: Vec<_> = all
            .iter()
            .filter(|p| !p.is_plugin && p.id == self.origin)
            .collect();
        if origins.len() != 1 {
            bail!("Origin disappeared");
        }
        let tab = origins[0].tab_id;
        if self.tab.is_some_and(|old| old != tab) {
            bail!("Origin moved tabs");
        }
        let mut terminals: Vec<_> = all
            .iter()
            .filter(|p| p.tab_id == tab && !p.is_plugin)
            .cloned()
            .collect();
        // Native stack headers are fixed one-row panes; selection-group and
        // collapsed-pane metadata describe separate runtime features.
        if terminals.iter().any(|p| {
            p.is_floating
                || p.is_fullscreen
                || p.is_suppressed
                || p.is_collapsed
                || p.pane_rows <= 1
                || p.exited
                || !p.index_in_pane_group.is_empty()
        }) {
            bail!("Floating, zoomed, stacked, hidden or exited panes are unsupported");
        }
        let left = terminals
            .iter()
            .map(|p| p.pane_x)
            .min()
            .context("No terminals")?;
        let top = terminals
            .iter()
            .map(|p| p.pane_y)
            .min()
            .context("No terminals")?;
        let right = terminals
            .iter()
            .map(|p| p.pane_x + p.pane_columns)
            .max()
            .context("No terminals")?;
        let bottom = terminals
            .iter()
            .map(|p| p.pane_y + p.pane_rows)
            .max()
            .context("No terminals")?;
        if all.iter().any(|p| {
            p.tab_id == tab
                && p.is_plugin
                && !p.is_suppressed
                && p.pane_x < right
                && p.pane_x + p.pane_columns > left
                && p.pane_y < bottom
                && p.pane_y + p.pane_rows > top
        }) {
            bail!("Plugin pane overlaps tiled group");
        }
        terminals.sort_by_key(|p| p.id);
        if terminals.windows(2).any(|p| p[0].id == p[1].id) {
            bail!("Duplicate pane IDs");
        }
        self.tab = Some(tab);
        self.panes = terminals;
        Ok(())
    }
    fn pane(&self, id: i64) -> Result<&Pane> {
        self.panes
            .iter()
            .find(|p| p.id == id)
            .context("Pane disappeared")
    }
    fn resize(
        &mut self,
        id: i64,
        axis: usize,
        increase: bool,
        allowed: &HashSet<i64>,
    ) -> Result<()> {
        let before = self.panes.clone();
        let expected = geometry(&before);
        self.snapshot()?;
        if geometry(&self.panes) != expected {
            bail!("Layout changed concurrently; stopped");
        }
        if self.calls >= 32 || Instant::now() >= self.stop {
            bail!("Resize budget reached; stopped");
        }
        let pane = self.pane(id)?;
        if !self.panes.iter().any(|q| neighboring(pane, q, axis)) {
            bail!("Boundary is no longer internal");
        }
        let native_id = if increase {
            self.panes
                .iter()
                .find(|q| allowed.contains(&q.id) && neighboring(pane, q, axis))
                .context("No eligible neighbor at the intended boundary")?
                .id
        } else {
            id
        };
        let direction = match (axis, increase) {
            (0, false) => "right",
            (0, true) => "left",
            (_, false) => "down",
            (_, true) => "up",
        };
        self.calls += 1;
        self.action(&[
            "resize",
            "decrease",
            direction,
            "--pane-id",
            &format!("terminal_{native_id}"),
        ])?;
        self.snapshot()?;
        let old = before
            .iter()
            .find(|p| p.id == id)
            .context("Missing source")?
            .rect();
        let delta = self.pane(id)?.rect()[axis + 2] - old[axis + 2];
        let edge = old[axis] + old[axis + 2];
        let expected: Vec<_> = before
            .iter()
            .map(|p| {
                let mut r = p.rect();
                if allowed.contains(&p.id) {
                    if r[axis] + r[axis + 2] == edge {
                        r[axis + 2] += delta;
                    } else if r[axis] == edge {
                        r[axis] += delta;
                        r[axis + 2] -= delta;
                    }
                }
                [p.id, r[0], r[1], r[2], r[3]]
            })
            .collect();
        if geometry(&self.panes) != expected {
            bail!("Unexpected boundary or pane change; stopped without rollback");
        }
        Ok(())
    }
    fn approach(
        &mut self,
        id: i64,
        axis: usize,
        target: i64,
        ceiling: Option<i64>,
        allowed: &HashSet<i64>,
    ) -> Result<()> {
        loop {
            let rect = self.pane(id)?.rect();
            let edge = rect[axis] + rect[axis + 2];
            if edge == target {
                return Ok(());
            }
            if self.calls >= 31 {
                bail!("Step budget reached");
            }
            let old = geometry(&self.panes);
            let increase = edge < target;
            self.resize(id, axis, increase, allowed)?;
            if geometry(&self.panes) == old {
                return Ok(());
            }
            let rect = self.pane(id)?.rect();
            let next = rect[axis] + rect[axis + 2];
            let crossed = ceiling.is_some_and(|c| edge <= c && next > c);
            let farther = (next - target).abs() >= (edge - target).abs()
                && ceiling.is_none_or(|c| edge <= c || next > c);
            if crossed || farther {
                self.resize(id, axis, !increase, allowed)?;
                if geometry(&self.panes) != old {
                    bail!("Overshoot reversal was not exact; stopped");
                }
                return Ok(());
            }
        }
    }
}
fn execute(mode: &str) -> Result<()> {
    let mut b = Balance {
        session: session()?,
        origin: origin_id()?.try_into()?,
        tab: None,
        deadline: Instant::now() + Duration::from_secs(20),
        stop: Instant::now() + Duration::from_secs(17),
        calls: 0,
        panes: vec![],
    };
    b.snapshot()?;
    let namespace = env::var("ZELLIJ_SOCKET_DIR")
        .or_else(|_| env::var("XDG_RUNTIME_DIR"))
        .unwrap_or_default();
    let key = hash(&format!(
        "{namespace}\n{}\n{}",
        b.session,
        b.tab.context("No tab")?
    ));
    let directory = env::var_os("XDG_CACHE_HOME")
        .map(PathBuf::from)
        .unwrap_or(home()?.join(".cache"))
        .join("zellij/balance");
    private_dir(&directory)?;
    let _lock = Lock::acquire(&directory.join(format!("{key}.lock")), b.stop)?;
    b.snapshot()?;
    if b.panes.len() <= 1 {
        return Ok(());
    }
    if mode != "equalize" {
        let p = b
            .panes
            .iter()
            .min_by_key(|p| (p.pane_x, p.pane_y))
            .context("No panes")?;
        if mode == "golden" && p.pane_content_columns >= 120 {
            return Ok(());
        }
        if Some(p.pane_y) != b.panes.iter().map(|p| p.pane_y).min()
            || Some(p.pane_y + p.pane_rows) != b.panes.iter().map(|p| p.pane_y + p.pane_rows).max()
        {
            bail!("Golden sizing needs one full-height left pane");
        }
        let total = b
            .panes
            .iter()
            .map(|p| p.pane_x + p.pane_columns)
            .max()
            .context("No panes")?
            - p.pane_x;
        let frame = p.pane_columns - p.pane_content_columns;
        let id = p.id;
        let target = p.pane_x + (total * 382 / 1000).min(180) + frame;
        let ceiling = p.pane_x + 180 + frame;
        let allowed = b.panes.iter().map(|p| p.id).collect();
        b.approach(id, 0, target, Some(ceiling), &allowed)?;
    } else {
        let mut plans = vec![];
        for axis in 0..2 {
            let mut groups: BTreeMap<(i64, i64), Vec<&Pane>> = BTreeMap::new();
            for p in &b.panes {
                let r = p.rect();
                groups
                    .entry((r[1 - axis], r[3 - axis]))
                    .or_default()
                    .push(p);
            }
            for mut group in groups.into_values() {
                group.sort_by_key(|p| p.rect()[axis]);
                if group.len() > 1
                    && group.iter().any(|p| p.id == b.origin)
                    && group
                        .windows(2)
                        .all(|p| p[0].rect()[axis] + p[0].rect()[axis + 2] == p[1].rect()[axis])
                {
                    plans.push((
                        axis,
                        group.iter().map(|p| p.id).collect::<Vec<_>>(),
                        group[0].rect()[axis],
                        group.iter().map(|p| p.rect()[axis + 2]).sum::<i64>(),
                    ));
                }
            }
        }
        if plans.len() != 1 {
            bail!("Origin has no unambiguous aligned row or column group");
        }
        let (axis, ids, start, extent) = plans.remove(0);
        let n = ids.len() as i64;
        let allowed = ids.iter().copied().collect();
        for (i, id) in ids.iter().enumerate().take(ids.len() - 1) {
            b.approach(
                *id,
                axis,
                start + (extent * (i as i64 + 1) + n / 2) / n,
                None,
                &allowed,
            )?;
        }
    }
    Ok(())
}
pub fn main(args: &[String]) -> Result<()> {
    let [mode] = args else {
        bail!("Expected equalize, golden or golden-force");
    };
    if !matches!(mode.as_str(), "equalize" | "golden" | "golden-force") {
        bail!("Expected equalize, golden or golden-force");
    }
    let result = execute(mode);
    if let Err(error) = &result {
        if let Ok(session) = session() {
            let _ = zellij(
                &session,
                &[
                    "prompt",
                    "notify",
                    &format!("Pane balance: {error}"),
                    "--timeout",
                    "5s",
                ],
                Instant::now() + Duration::from_secs(1),
            );
        }
    }
    result
}
