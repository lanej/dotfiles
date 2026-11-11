package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math/big"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"syscall"
)

var version = "dev"

const marker = "# git-worktree-policy dispatcher v1"

var (
	hooks            = []string{"pre-worktree", "post-worktree", "post-checkout"}
	sizePattern      = regexp.MustCompile(`(?i)^\s*(\d+)\s*(B|[KMGT]I?B)?\s*$`)
	localKeysPattern = regexp.MustCompile(`^GIT_CONFIG_(KEY|VALUE)_\d+$`)
)

type inventory struct {
	LinkedCount int              `json:"linked_count"`
	Worktrees   []map[string]any `json:"worktrees"`
}
type policy struct {
	localEnv []string
	ctx      context.Context
}

func (p *policy) command(directory string, args ...string) ([]byte, error) {
	var env []string

	if directory != "" {
		if p.localEnv == nil {
			output, err := exec.CommandContext(p.ctx, "git", "rev-parse", "--local-env-vars").Output()
			if err != nil {
				return nil, fmt.Errorf("read Git environment: %w", err)
			}

			names := map[string]bool{"GIT_NAMESPACE": true}
			for _, name := range strings.Fields(string(output)) {
				names[name] = true
			}

			for _, field := range os.Environ() {
				name, _, _ := strings.Cut(field, "=")
				if !names[name] && !localKeysPattern.MatchString(name) {
					env = append(env, field)
				}
			}

			p.localEnv = env
		}

		env = p.localEnv

		args = append([]string{"--git-dir=" + directory}, args...)
	}

	//nolint:gosec // rationale: Git arguments are passed as separate argv entries without a shell.
	command := exec.CommandContext(p.ctx, "git", args...)
	command.Env = env

	var stderr bytes.Buffer

	command.Stderr = &stderr

	output, err := command.Output()
	if err != nil && stderr.Len() > 0 {
		return output, fmt.Errorf("%s: %w", strings.TrimSpace(stderr.String()), err)
	}

	return output, err
}

func (p *policy) git(directory string, optional bool, args ...string) (string, error) {
	output, err := p.command(directory, args...)

	var exited *exec.ExitError
	if optional && errors.As(err, &exited) && exited.ExitCode() == 1 {
		return "", nil
	}

	return strings.TrimSuffix(string(output), "\n"), err
}

func (p *policy) common() (string, error) {
	return p.git("", false, "rev-parse", "--path-format=absolute", "--git-common-dir")
}

func (p *policy) inventory(directory string) (inventory, error) {
	output, err := p.command(directory, "worktree", "list", "--porcelain", "-z")
	if err != nil {
		return inventory{}, err
	}

	state := inventory{Worktrees: []map[string]any{}}
	row := map[string]any{}

	for _, field := range bytes.Split(output, []byte{0}) {
		if len(field) == 0 {
			if len(row) > 0 {
				state.Worktrees = append(state.Worktrees, row)
				row = map[string]any{}
			}

			continue
		}

		key, value, hasValue := bytes.Cut(field, []byte(" "))
		if hasValue && len(value) > 0 {
			row[string(key)] = gitText(value)
		} else {
			row[string(key)] = true
		}
	}

	if len(row) > 0 {
		state.Worktrees = append(state.Worktrees, row)
	}

	state.LinkedCount = max(0, len(state.Worktrees)-1)

	return state, nil
}

func atomicJSON(path string, value any) (resultErr error) {
	if mkdirAllErr := os.MkdirAll(filepath.Dir(path), 0o750); mkdirAllErr != nil {
		return mkdirAllErr
	}

	file, err := os.CreateTemp(filepath.Dir(path), ".inventory-")
	if err != nil {
		return err
	}

	name := file.Name()
	defer func() {
		if removeErr := os.Remove(name); removeErr != nil && !errors.Is(removeErr, os.ErrNotExist) {
			resultErr = errors.Join(resultErr, removeErr)
		}
	}()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	encodeErr := encoder.Encode(value)
	closeErr := file.Close()

	if encodeErr != nil {
		return encodeErr
	}

	if closeErr != nil {
		return closeErr
	}

	return os.Rename(name, path)
}

func registryDir() (string, error) {
	root := os.Getenv("XDG_STATE_HOME")
	if root == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}

		root = filepath.Join(home, ".local/state")
	}

	return filepath.Join(root, "git-worktree-policy/repositories"), nil
}

func registryPath(common string) (string, error) {
	root, err := registryDir()
	if err != nil {
		return "", err
	}

	hash := sha256.Sum256([]byte(common))

	return filepath.Join(root, hex.EncodeToString(hash[:])+".json"), nil
}

func canonical(path string) (string, error) {
	absolute, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}

	resolved, err := filepath.EvalSymlinks(absolute)
	if errors.Is(err, os.ErrNotExist) {
		parent, leaf := filepath.Dir(absolute), filepath.Base(absolute)
		if parent == absolute {
			return absolute, nil
		}

		resolved, err = canonical(parent)
		if err != nil {
			return "", err
		}

		return filepath.Join(resolved, leaf), nil
	}

	return resolved, err
}

func (p *policy) reconcile(directory string) (inventory, error) {
	if directory == "" {
		common, err := p.common()
		if err != nil {
			return inventory{}, err
		}

		directory = common
	}

	common, err := canonical(directory)
	if err != nil {
		return inventory{}, err
	}

	state, err := p.inventory(common)
	if err != nil {
		return inventory{}, err
	}

	if atomicJSONErr := atomicJSON(filepath.Join(common, "worktree-policy/inventory.json"), state); atomicJSONErr != nil {
		return inventory{}, atomicJSONErr
	}

	record, err := registryPath(common)
	if err != nil {
		return inventory{}, err
	}

	err = atomicJSON(record, map[string]any{"common_gitdir": gitText(common), "inventory": state})

	return state, err
}

func readLimits() (map[string]*big.Int, error) {
	root, err := registryDir()
	if err != nil {
		return nil, err
	}

	path := filepath.Join(filepath.Dir(root), "config.json")

	//nolint:gosec // rationale: This is the caller-selected XDG state file, not an external file request.
	data, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return map[string]*big.Int{}, nil
	}

	if err != nil {
		return nil, err
	}

	var raw map[string]json.RawMessage
	if unmarshalErr := json.Unmarshal(data, &raw); unmarshalErr != nil {
		return nil, unmarshalErr
	}

	if raw == nil {
		return nil, fmt.Errorf("invalid global configuration: %s", path)
	}

	limits := map[string]*big.Int{}

	for key, value := range raw {
		if key != "max_bytes" && key != "max_worktrees" {
			return nil, fmt.Errorf("invalid global configuration: %s", path)
		}

		number := new(big.Int)
		if !integerJSON(value) || number.UnmarshalJSON(value) != nil || number.Sign() < 0 {
			return nil, fmt.Errorf("global limits must be nonnegative integers: %s", path)
		}

		limits[key] = number
	}

	return limits, nil
}

func integerJSON(value []byte) bool {
	text := strings.TrimSpace(string(value))
	if text == "" {
		return false
	}

	for i, character := range text {
		if character == '-' && i == 0 {
			continue
		}

		if character < '0' || character > '9' {
			return false
		}
	}

	return true
}

func parseNumber(value string) (*big.Int, error) {
	number, ok := new(big.Int).SetString(strings.TrimSpace(value), 10)
	if !ok || number.Sign() < 0 {
		return nil, errors.New("limits must be nonnegative integers")
	}

	return number, nil
}

func parseSize(value string) (*big.Int, error) {
	match := sizePattern.FindStringSubmatch(value)
	if match == nil {
		return nil, fmt.Errorf("invalid byte size: %q; use bytes or a size such as 2GiB", value)
	}

	number, err := parseNumber(match[1])
	if err != nil {
		return nil, err
	}

	unit := strings.ToUpper(match[2])

	power := 0
	if unit != "" && unit != "B" {
		power = strings.IndexByte("KMGT", unit[0]) + 1
	}

	base := int64(1000)
	if strings.Contains(unit, "I") {
		base = 1024
	}

	multiplier := new(big.Int).Exp(big.NewInt(base), big.NewInt(int64(power)), nil)

	return number.Mul(number, multiplier), nil
}

func (p *policy) localLimit(directory, key string, byteSize bool) (*big.Int, error) {
	value, err := p.git(directory, true, "config", "--local", "--get", key)
	if err != nil || value == "" {
		return nil, err
	}

	if byteSize {
		return parseSize(value)
	}

	number, err := parseNumber(value)
	if err != nil {
		return nil, errors.New("worktree.limit must be a nonnegative integer")
	}

	return number, nil
}

func paths(state inventory) []string {
	result := []string{}
	if len(state.Worktrees) < 2 {
		return result
	}

	for _, row := range state.Worktrees[1:] {
		if path, ok := row["worktree"].(gitText); ok {
			result = append(result, string(path))
		}
	}

	return result
}

func allocated(paths []string) (*big.Int, error) {
	type fileIdentity struct {
		Device any
		Inode  uint64
	}

	seen := map[fileIdentity]bool{}
	total := new(big.Int)

	var visit func(string) error

	visit = func(path string) error {
		info, err := os.Lstat(path)
		if err != nil {
			return err
		}

		stat, ok := info.Sys().(*syscall.Stat_t)
		if !ok {
			return fmt.Errorf("allocated-block accounting unavailable: %s", path)
		}

		identity := fileIdentity{stat.Dev, stat.Ino}
		if seen[identity] || info.Mode()&os.ModeSymlink != 0 {
			return nil
		}

		seen[identity] = true

		if stat.Blocks < 0 {
			return fmt.Errorf("negative allocated-block count: %s", path)
		}

		total.Add(total, new(big.Int).Mul(big.NewInt(stat.Blocks), big.NewInt(512)))

		if info.IsDir() {
			entries, err := os.ReadDir(path)
			if err != nil {
				return err
			}

			for _, entry := range entries {
				if visitErr := visit(filepath.Join(path, entry.Name())); visitErr != nil {
					return visitErr
				}
			}
		}

		return nil
	}
	for _, path := range paths {
		if visitErr := visit(path); visitErr != nil {
			return nil, visitErr
		}
	}

	return total, nil
}

func (p *policy) records() ([]map[string]any, error) {
	root, err := registryDir()
	if err != nil {
		return nil, err
	}

	files, err := filepath.Glob(filepath.Join(root, "*.json"))
	if err != nil {
		return nil, err
	}

	sort.Strings(files)

	records := []map[string]any{}

	for _, file := range files {
		record := map[string]any{"registry_record": gitText(file)}
		loadErr := func() error {
			//nolint:gosec // rationale: Registry entries are selected from this user-owned state directory.
			data, err := os.ReadFile(file)
			if err != nil {
				return err
			}

			var stored struct {
				Common    *gitText        `json:"common_gitdir"`
				Inventory json.RawMessage `json:"inventory"`
			}
			if unmarshalErr := json.Unmarshal(data, &stored); unmarshalErr != nil {
				return unmarshalErr
			}

			if stored.Common == nil {
				return errors.New("missing common_gitdir")
			}

			if len(stored.Inventory) > 0 {
				record["inventory"] = stored.Inventory
			}

			common := string(*stored.Common)
			record["common_gitdir"] = *stored.Common

			resolved, err := canonical(common)
			if err != nil {
				return err
			}

			if resolved != common {
				return errors.New("registered path now resolves elsewhere; register the new location and forget this historical path")
			}

			state, err := p.reconcile(common)
			if err != nil {
				return err
			}

			record["inventory"] = state

			return nil
		}()

		record["available"] = loadErr == nil
		if loadErr != nil {
			record["error"] = loadErr.Error()
		}

		records = append(records, record)
	}

	return records, nil
}

func asInventory(record map[string]any) (inventory, error) {
	state, ok := record["inventory"].(inventory)
	if !ok {
		return inventory{}, errors.New("missing reconciled inventory")
	}

	return state, nil
}

func (p *policy) status() (int, error) {
	records, err := p.records()
	if err != nil {
		return 1, err
	}

	complete := true
	totalCount := 0
	allPaths := []string{}

	for _, row := range records {
		if row["available"] != true {
			complete = false
			continue
		}

		rowErr := func() error {
			common, ok := row["common_gitdir"].(gitText)
			if !ok {
				return errors.New("missing common_gitdir")
			}

			limit, rowError := p.localLimit(string(common), "worktree.limit", false)
			if rowError != nil {
				return rowError
			}

			row["limit"] = limit

			maximum, rowError := p.localLimit(string(common), "worktree.maxBytes", true)
			if rowError != nil {
				return rowError
			}

			row["max_bytes"] = maximum

			state, rowError := asInventory(row)
			if rowError != nil {
				return rowError
			}

			used, rowError := allocated(paths(state))
			if rowError != nil {
				return rowError
			}

			row["disk_bytes"] = used

			return nil
		}()
		if rowErr != nil {
			row["available"] = false
			row["error"] = rowErr.Error()
			complete = false

			continue
		}

		state, inventoryErr := asInventory(row)
		if inventoryErr != nil {
			return 1, inventoryErr
		}

		totalCount += state.LinkedCount
		allPaths = append(allPaths, paths(state)...)
	}

	totals := map[string]any{"linked_count": totalCount}

	if complete {
		used, allocatedErr := allocated(allPaths)
		if allocatedErr != nil {
			return 1, allocatedErr
		}

		totals["disk_bytes"] = used
	}

	limits, err := readLimits()
	if err != nil {
		return 1, err
	}

	err = json.NewEncoder(os.Stdout).Encode(map[string]any{"repositories": records, "global_limits": limits, "totals": totals, "complete": complete})
	if err != nil {
		return 1, err
	}

	if !complete {
		return 1, nil
	}

	return 0, nil
}

func (p *policy) capacity(state inventory, block bool) (int, error) {
	type check struct {
		description     string
		actual, maximum *big.Int
	}

	checks := []check{}

	count, err := p.localLimit("", "worktree.limit", false)
	if err != nil {
		return 1, err
	}

	if count != nil {
		checks = append(checks, check{"repository linked worktrees", big.NewInt(int64(state.LinkedCount)), count})
	}

	maximum, err := p.localLimit("", "worktree.maxBytes", true)
	if err != nil {
		return 1, err
	}

	if maximum != nil {
		used, allocatedErr := allocated(paths(state))
		if allocatedErr != nil {
			return 1, allocatedErr
		}

		checks = append(checks, check{"repository allocated bytes", used, maximum})
	}

	limits, err := readLimits()
	if err != nil {
		return 1, err
	}

	if len(limits) > 0 {
		records, err := p.records()
		if err != nil {
			return 1, err
		}

		count := 0
		allPaths := []string{}

		for _, row := range records {
			if row["available"] != true {
				return 1, fmt.Errorf("cannot evaluate global budget: %v: %v", row["common_gitdir"], row["error"])
			}

			current, err := asInventory(row)
			if err != nil {
				return 1, err
			}

			count += current.LinkedCount
			allPaths = append(allPaths, paths(current)...)
		}

		if limit := limits["max_worktrees"]; limit != nil {
			checks = append(checks, check{"global linked worktrees", big.NewInt(int64(count)), limit})
		}

		if limit := limits["max_bytes"]; limit != nil {
			used, err := allocated(allPaths)
			if err != nil {
				return 1, err
			}

			checks = append(checks, check{"global allocated bytes", used, limit})
		}
	}

	exceeded := false

	for _, check := range checks {
		if check.actual.Cmp(check.maximum) >= 0 {
			exceeded = true

			suffix := "; next cooperating allocation will be refused"
			if block {
				suffix = "; refusing add"
			}

			if _, printErr := fmt.Fprintf(os.Stderr, "git-worktree-policy: %s %s; limit is %s%s\n", check.actual, check.description, check.maximum, suffix); printErr != nil {
				return 1, printErr
			}
		}
	}

	if block && exceeded {
		return 1, nil
	}

	return 0, nil
}

func (p *policy) observe(name string, args []string) (int, error) {
	if (name == "pre-worktree" || name == "post-worktree") && len(args) != 4 {
		return 1, fmt.Errorf("%s expects event, id, old path, new path", name)
	}

	block := name == "pre-worktree" && args[0] == "add"
	if name == "pre-worktree" && !block {
		return 0, nil
	}

	state, err := p.reconcile("")

	status := 0
	if err == nil {
		status, err = p.capacity(state, block)
	}

	if err != nil {
		if _, printErr := fmt.Fprintf(os.Stderr, "git-worktree-policy: %s\n", err); printErr != nil {
			return 1, printErr
		}

		if block {
			return 1, nil
		}

		return 0, nil
	}

	return status, nil
}

func contains(values []string, value string) bool {
	for _, candidate := range values {
		if candidate == value {
			return true
		}
	}

	return false
}

func shellQuote(value string) string { return "'" + strings.ReplaceAll(value, "'", "'\"'\"'") + "'" }

func (p *policy) requireDefault(directory string) error {
	output, err := p.command(directory, "config", "--get", "core.hooksPath")

	var exited *exec.ExitError
	if errors.As(err, &exited) && exited.ExitCode() == 1 {
		return nil
	}

	if err != nil {
		return err
	}

	return fmt.Errorf("installation does not support configured core.hooksPath in %s (%s); invoke the hook command from your existing hook manager", directory, strings.TrimSpace(string(output)))
}

func (p *policy) install() error {
	if requireDefaultErr := p.requireDefault(""); requireDefaultErr != nil {
		return requireDefaultErr
	}

	common, err := p.common()
	if err != nil {
		return err
	}

	enabled, err := p.git("", true, "config", "--bool", "--get", "extensions.worktreeConfig")
	if err != nil {
		return err
	}

	if enabled == "true" {
		if requireDefaultErr := p.requireDefault(common); requireDefaultErr != nil {
			return requireDefaultErr
		}

		entries, entriesErr := os.ReadDir(filepath.Join(common, "worktrees"))
		if entriesErr != nil && !errors.Is(entriesErr, os.ErrNotExist) {
			return entriesErr
		}

		for _, entry := range entries {
			if entry.IsDir() {
				if requireDefaultErr := p.requireDefault(filepath.Join(common, "worktrees", entry.Name())); requireDefaultErr != nil {
					return requireDefaultErr
				}
			}
		}
	}

	bare, err := p.git("", false, "rev-parse", "--is-bare-repository")
	if err != nil {
		return err
	}

	if bare == "true" {
		return errors.New("install from a non-bare repository worktree")
	}

	directory := filepath.Join(common, "hooks")

	info, err := os.Lstat(directory)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}

	if info != nil && info.Mode()&os.ModeSymlink != 0 {
		return errors.New("installation does not support a symlinked hooks directory; use your existing hook manager")
	}

	if mkdirAllErr := os.MkdirAll(directory, 0o750); mkdirAllErr != nil {
		return mkdirAllErr
	}

	executable, err := os.Executable()
	if err != nil {
		return err
	}

	type plan struct {
		name, target, backup string
		exists               bool
	}

	plans := []plan{}

	for _, name := range hooks {
		target := filepath.Join(directory, name)
		backup := target + ".worktree-policy-original"

		info, err := os.Lstat(target)
		if err != nil && !errors.Is(err, os.ErrNotExist) {
			return err
		}

		if info != nil && info.Mode().IsRegular() {
			//nolint:gosec // rationale: Inspect the repository hook selected for explicit compatibility installation.
			data, err := os.ReadFile(target)
			if err != nil {
				return err
			}

			if bytes.Contains(data, []byte(marker)) {
				continue
			}
		}

		if _, lstatErr := os.Lstat(backup); lstatErr == nil {
			return fmt.Errorf("refusing to overwrite existing backup: %s", backup)
		} else if !errors.Is(lstatErr, os.ErrNotExist) {
			return lstatErr
		}

		if info != nil && info.IsDir() {
			return fmt.Errorf("hook is a directory: %s", target)
		}

		plans = append(plans, plan{name, target, backup, info != nil})
	}

	for _, plan := range plans {
		if plan.exists {
			if renameErr := os.Rename(plan.target, plan.backup); renameErr != nil {
				return renameErr
			}
		}

		content := "#!/bin/sh\n" + marker + "\nexec " + shellQuote(executable) + " hook " + plan.name + " \"$@\"\n"
		//nolint:gosec // rationale: Git invokes these repository hook scripts as executables.
		if writeFileErr := os.WriteFile(plan.target, []byte(content), 0o755); writeFileErr != nil {
			return writeFileErr
		}
	}

	if _, reconcileErr := p.reconcile(""); reconcileErr != nil {
		return reconcileErr
	}

	_, printErr := fmt.Println("Installed repository hooks; configure a cap with git config --local worktree.limit 4")

	return printErr
}

func (p *policy) hook(name string, args []string) (int, error) {
	common, err := p.common()
	if err != nil {
		return 1, err
	}

	original := filepath.Join(common, "hooks", name+".worktree-policy-original")
	prior := 0

	//nolint:gosec // rationale: Explicit compatibility installation retains Git's existing trust in local repository hooks.
	if info, statErr := os.Stat(original); statErr == nil && info.Mode().IsRegular() && info.Mode().Perm()&0o111 != 0 {
		//nolint:gosec // rationale: Compatibility mode intentionally invokes the saved repository hook, without a shell.
		command := exec.CommandContext(p.ctx, original, args...)
		command.Stdin = os.Stdin
		command.Stdout = os.Stdout

		command.Stderr = os.Stderr
		if runErr := command.Run(); runErr != nil {
			var exited *exec.ExitError
			if !errors.As(runErr, &exited) {
				return 1, runErr
			}

			prior = exited.ExitCode()
		}
	} else if statErr != nil && !errors.Is(statErr, os.ErrNotExist) {
		return 1, statErr
	}

	if name == "pre-worktree" && prior != 0 {
		return prior, nil
	}

	status, err := p.observe(name, args)
	if prior != 0 {
		return prior, err
	}

	return status, err
}
func writeJSON(value any) error { return json.NewEncoder(os.Stdout).Encode(value) }
func (p *policy) run(args []string) (int, error) {
	if len(args) == 1 && args[0] == "--version" {
		_, printErr := fmt.Println("git-worktree-policy " + version)
		return 0, printErr
	}

	usage := "usage: git-worktree-policy {install,refresh,preflight,status,forget,configure,hook,observe}"
	if len(args) == 1 && args[0] == "--help" {
		_, printErr := fmt.Fprintln(os.Stdout, usage)
		return 0, printErr
	}

	if len(args) == 0 {
		return 2, errors.New(usage)
	}

	command := args[0]

	args = args[1:]
	if (command == "install" || command == "refresh" || command == "preflight") && len(args) != 0 {
		return 2, fmt.Errorf("unexpected arguments for %s", command)
	}

	switch command {
	case "install":
		return 0, p.install()
	case "status":
		if len(args) != 1 || args[0] != "--all" {
			return 2, errors.New("status requires --all")
		}

		return p.status()
	case "refresh", "preflight":
		state, err := p.reconcile("")
		if err != nil {
			return 1, err
		}

		if command == "refresh" {
			return 0, writeJSON(state)
		}

		return p.capacity(state, true)
	case "forget":
		if len(args) != 1 {
			return 2, errors.New("forget requires common_gitdir")
		}

		common, err := filepath.Abs(args[0])
		if err != nil {
			return 1, err
		}

		path, err := registryPath(common)
		if err != nil {
			return 1, err
		}

		if removeErr := os.Remove(path); removeErr != nil {
			return 1, fmt.Errorf("repository is not registered: %s; expected record: %s: %w", common, path, removeErr)
		}

		return 0, writeJSON(map[string]any{"forgotten_common_gitdir": gitText(common), "removed_registry_record": gitText(path)})
	case "configure":
		limits, err := readLimits()
		if err != nil {
			return 1, err
		}

		global := false

		for len(args) > 0 {
			key := args[0]
			args = args[1:]

			if option, value, found := strings.Cut(key, "="); found && option != "--global" {
				key = option

				args = append([]string{value}, args...)
			}

			if key == "--global" {
				global = true
				continue
			}

			if (key != "--max-bytes" && key != "--max-worktrees") || len(args) == 0 {
				return 2, fmt.Errorf("invalid configure option: %s", key)
			}

			value := args[0]
			args = args[1:]

			field := "max_worktrees"
			if key == "--max-bytes" {
				field = "max_bytes"
			}

			if value == "off" {
				delete(limits, field)
				continue
			}

			var number *big.Int
			if field == "max_bytes" {
				number, err = parseSize(value)
			} else {
				number, err = parseNumber(value)
			}

			if err != nil {
				return 1, err
			}

			limits[field] = number
		}

		if !global {
			return 2, errors.New("configure requires --global")
		}

		root, err := registryDir()
		if err != nil {
			return 1, err
		}

		if atomicJSONErr := atomicJSON(filepath.Join(filepath.Dir(root), "config.json"), limits); atomicJSONErr != nil {
			return 1, atomicJSONErr
		}

		return 0, writeJSON(limits)
	case "hook", "observe":
		if len(args) == 0 || !contains(hooks, args[0]) {
			return 2, errors.New("expected pre-worktree, post-worktree, or post-checkout")
		}

		if command == "hook" {
			return p.hook(args[0], args[1:])
		}

		return p.observe(args[0], args[1:])
	default:
		return 2, fmt.Errorf("unknown command: %s", command)
	}
}

func entry() int {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	status, err := (&policy{ctx: ctx}).run(os.Args[1:])
	if err != nil {
		if _, printErr := fmt.Fprintf(os.Stderr, "git-worktree-policy: %s\n", err); printErr != nil {
			return 1
		}

		if status == 0 {
			status = 1
		}
	}

	return status
}
func main() { os.Exit(entry()) }
