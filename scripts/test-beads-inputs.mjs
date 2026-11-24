/** Actual workflow selection for the capability-local Beads recipe. */
import assert from "node:assert/strict";
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { test } from "node:test";

const root = fileURLToPath(new URL("../", import.meta.url));
const require = createRequire(new URL("../tools/task-runtime/package.json", import.meta.url));
const { load } = require("js-yaml");
const minimatch = require("minimatch");
const workflows = new Map(readdirSync(join(root, ".github/workflows"))
  .filter(name => name.endsWith(".yml"))
  .map(name => [name, load(readFileSync(join(root, ".github/workflows", name), "utf8"))]));

// GitHub evaluates whole repository-relative paths, in order, with case preserved.
// This fixture uses the documented literal/*/** subset. Unsupported pattern
// syntax selects conservatively, so it cannot manufacture an exclusion proof.
// https://docs.github.com/actions/writing-workflows/workflow-syntax-for-github-actions#filter-pattern-cheat-sheet
function matches(path, pattern) {
  if (/[?+\[\]{}()\\]/.test(pattern)) return true;
  return minimatch(path, pattern, {
    dot: true, nocase: false, matchBase: false, nobrace: true,
    noext: true, nocomment: true, nonegate: true,
  });
}
function pathSelected(path, patterns) {
  let selected = false;
  for (const pattern of patterns) {
    const negative = pattern.startsWith("!");
    const body = negative ? pattern.slice(1) : pattern;
    // Unknown negative patterns cannot safely exclude an input.
    if (negative && /[?+\[\]{}()\\]/.test(body)) continue;
    if (matches(path, body)) selected = !negative;
  }
  return selected;
}
function selected(path, event, source = workflows) {
  return [...source].filter(([, workflow]) => {
    const triggers = workflow.on;
    const filter = typeof triggers === "string" ? (triggers === event ? {} : undefined)
      : Array.isArray(triggers) ? (triggers.includes(event) ? {} : undefined)
      : triggers?.[event];
    if (filter === undefined) return false;
    if (filter?.paths) return pathSelected(path, filter.paths);
    if (filter?.["paths-ignore"]) {
      if (filter["paths-ignore"].some(pattern => /[?+\[\]{}()\\]/.test(pattern))) return true;
      return !pathSelected(path, filter["paths-ignore"]);
    }
    return true;
  }).map(([name]) => name).sort();
}
const consumers = ["beads-service.yml", "neovim-beads.yml", "paseo-tasks.yml",
  "pi-resources.yml", "project-updates.yml", "setup.yml", "worktree-manager.yml", "beads-inputs.yml"];
const unrelated = ["git-worktree-hooks.yml",
  "worktree-policy.yml", "agent-treehouse.yml", "directory-picker.yml"];
function assertManifestCoverage(source = workflows) {
  for (const event of ["pull_request", "push"]) {
    const observed = selected("tools/beads/tool.toml", event, source);
    for (const name of consumers) assert(observed.includes(name), `${event}: missing ${name}; selected ${observed}`);
    for (const name of unrelated) assert(!observed.includes(name), `${event}: unrelated ${name} selected`);
  }
}

test("Beads manifest selects actual consumers, excluding independent Git hooks/worktree policy/fzf inputs", () => {
  assertManifestCoverage();
  console.log("Beads manifest workflows:", selected("tools/beads/tool.toml", "pull_request").join(", "));
});
test("shared loader, schema and workflow changes retain their actual consumers", () => {
  for (const event of ["pull_request", "push"]) {
    for (const name of ["setup.yml", "project-updates.yml", "pi-resources.yml", "worktree-manager.yml"])
      assert(selected("scripts/dotfiles-config.py", event).includes(name), `${event}: loader missing ${name}`);
    assert(selected("config/schema.json", event).includes("setup.yml"));
    for (const name of consumers)
      assert(selected(`.github/workflows/${name}`, event).includes(name), `${event}: workflow self-change missing ${name}`);
  }
});
test("selection preserves basename boundaries, case, dot paths and ordered exclusions", () => {
  assert(pathSelected("tools/beads/tool.toml", ["tools/beads/**"]));
  assert(!pathSelected("elsewhere/tool.toml", ["tools/beads/**"]));
  assert(!pathSelected("tools/Beads/tool.toml", ["tools/beads/**"]));
  assert(!pathSelected("nested/tools/beads/tool.toml", ["tools/beads/**"]));
  assert(pathSelected(".github/workflows/beads-service.yml", [".github/workflows/*.yml"]));
  assert(!pathSelected("tools/beads/private/a", ["tools/beads/**", "!tools/beads/private/**"]));
  assert(pathSelected("tools/beads/private/a", ["tools/beads/**", "!tools/beads/private/**", "tools/beads/private/a"]));
  assert(pathSelected("future/input", ["future/[ab]input"]), "Unsupported syntax must select conservatively");
  const future = new Map([["future.yml", { on: { pull_request: { "paths-ignore": ["future/[ab]input"] } } }]]);
  assert.deepEqual(selected("future/input", "pull_request", future), ["future.yml"]);
  for (const event of ["pull_request", "push"])
    for (const name of consumers.filter(name => name !== "beads-inputs.yml")) {
      assert(!selected("unrelated/tool.toml", event).includes(name), `${event}: basename-only selection in ${name}`);
      assert(!selected("tools/Beads/tool.toml", event).includes(name), `${event}: case-insensitive selection in ${name}`);
    }
});
test("removing an actual manifest edge is detected independently", () => {
  const broken = new Map(workflows);
  const workflow = structuredClone(broken.get("beads-service.yml"));
  for (const event of ["pull_request", "push"])
    workflow.on[event].paths = workflow.on[event].paths.filter(pattern => pattern !== "tools/beads/**");
  broken.set("beads-service.yml", workflow);
  assert.throws(() => assertManifestCoverage(broken), /missing beads-service.yml/);
});

// This is also the worktree-manager integration's real provider-selection path.
// Even SELECTED_TARGETS=git resolves the full catalog before running a recipe.
const configureInputs = ["Makefile", "config/targets.mk", "scripts/dotfiles-config.py",
  "scripts/runtime_requirements.py", "bootstrap/tools.toml", "tools/beads/tool.toml"];
const setInputs = readdirSync(join(root, "config/sets"))
  .filter(name => name.endsWith(".toml"))
  .map(name => `config/sets/${name}`);
function assertFixtureCoverage(source = workflows) {
  for (const event of ["pull_request", "push"])
    for (const input of [...configureInputs, ...setInputs])
      assert(selected(input, event, source).includes("beads-inputs.yml"), `${event}: fixture input missing ${input}`);
}
test("the real Make configure entrypoint requires the Beads manifest before effects", () => {
  const python = spawnSync(process.env.PYTHON ?? "python3", ["-c",
    "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'; print(sys.executable)"], { encoding: "utf8" });
  assert.equal(python.status, 0, python.error?.message ?? python.stderr);
  const directory = mkdtempSync(join(tmpdir(), "beads-config-inputs-"));
  const fixture = join(directory, "checkout"), home = join(directory, "home");
  try {
    mkdirSync(fixture); mkdirSync(home);
    mkdirSync(join(fixture, "scripts/make"), { recursive: true });
    for (const input of [...configureInputs, ...setInputs]) {
      const destination = join(fixture, input);
      mkdirSync(dirname(destination), { recursive: true });
      copyFileSync(join(root, input), destination);
    }
    const machine = join(home, "machine.toml");
    copyFileSync(join(root, "config/sets/worktrees.toml"), machine);
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
      !/^(DOTFILES_|XDG_|GIT_|WORKTREE_)/.test(key) && !["MAKEFLAGS", "MFLAGS", "MAKELEVEL"].includes(key)));
    Object.assign(env, { HOME: home, XDG_CONFIG_HOME: join(home, ".config"),
      XDG_STATE_HOME: join(home, "state"), XDG_CACHE_HOME: join(home, "cache"), DOTFILES_CONFIG: machine });
    const run = () => spawnSync("make", ["--no-print-directory", "-n", "configure",
      "SELECTED_TARGETS=git", `DOTFILES_PYTHON=${python.stdout.trim()}`],
      { cwd: fixture, env, encoding: "utf8", timeout: 10_000 });
    const complete = run();
    assert.equal(complete.status, 0, complete.error?.message ?? complete.stdout + complete.stderr);
    assert(complete.stdout.includes("config.sh"), complete.stdout);
    const manifest = join(fixture, "tools/beads/tool.toml");
    rmSync(manifest);
    const missing = run();
    assert.notEqual(missing.status, 0, "Make configure silently skipped the missing Beads recipe");
    assert.match(missing.stderr, /tools\/beads\/tool\.toml/);
    assert.match(missing.stderr, /Invalid dotfiles configuration/);
    assertFixtureCoverage();
    // Removing the actual worktree-manager edge must fail the routing contract.
    const broken = new Map(workflows);
    const workflow = structuredClone(broken.get("worktree-manager.yml"));
    for (const event of ["pull_request", "push"])
      workflow.on[event].paths = workflow.on[event].paths.filter(pattern => pattern !== "tools/beads/tool.toml");
    broken.set("worktree-manager.yml", workflow);
    assert.throws(() => assertManifestCoverage(broken), /missing worktree-manager.yml/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
test("removing a real Make fixture input from its gate is detected", () => {
  const broken = new Map(workflows);
  const workflow = structuredClone(broken.get("beads-inputs.yml"));
  for (const event of ["pull_request", "push"])
    workflow.on[event].paths = workflow.on[event].paths.filter(pattern => pattern !== "Makefile");
  broken.set("beads-inputs.yml", workflow);
  assert.throws(() => assertFixtureCoverage(broken), /fixture input missing Makefile/);
});
