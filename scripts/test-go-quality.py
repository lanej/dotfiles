#!/usr/bin/env python3
"""Exercise the installed Go gate with real analyzers and the race detector."""

from pathlib import Path
import json
import subprocess
import tempfile


SOURCE = Path(__file__).resolve().parents[1]
CODE = '''package sample

import (
	"errors"
	"io"
)

type State uint8

const (
	StateUnknown State = iota
	StatePending
	StateDone
)

var Labels = map[State]string{
	StateUnknown: "unknown",
	StatePending: "pending",
	StateDone:    "done",
}

func Terminal(state State) (bool, error) {
	switch state {
	case StateUnknown:
		return false, errors.New("unknown state")
	case StatePending:
		return false, nil
	case StateDone:
		return true, nil
	default:
		return false, errors.New("invalid state")
	}
}

//sumtype:decl
type Result interface {
	isResult()
}

type Accepted struct{ ID string }
type Rejected struct{ Reason string }

func (Accepted) isResult() {}
func (Rejected) isResult() {}

func Value(result Result) string {
	switch value := result.(type) {
	case Accepted:
		return value.ID
	case Rejected:
		return value.Reason
	default:
		return "invalid result"
	}
}

func Write(writer io.Writer) error {
	_, err := io.WriteString(writer, "ok")
	return err
}
'''
TEST = '''package sample

import "testing"

func TestTerminal(t *testing.T) {
	done, err := Terminal(StateDone)
	if err != nil || !done {
		t.Fatalf("done state: got %v, %v", done, err)
	}

	if _, err := Terminal(State(99)); err == nil {
		t.Fatal("out-of-set state accepted")
	}
}
'''
RACE = '''package sample

import "testing"

func TestConcurrent(t *testing.T) {
	var count int
	done := make(chan struct{})
	go func() {
		count++
		close(done)
	}()
	count++
	<-done
	if count == 0 {
		t.Fatal("counter did not change")
	}
}
'''


def run(command, cwd, success=True):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    if (result.returncode == 0) != success:
        raise AssertionError(f"{command}: exit {result.returncode}\n{output}")
    return output


with tempfile.TemporaryDirectory(prefix="go-quality-acceptance-") as temporary:
    project = Path(temporary) / "Go project"
    run([str(SOURCE / "bin/repo-bootstrap"), "--repo", str(project), "--init", "--go",
         "--skills", "go", "--agents", "codex", "--pr-template", "none"], SOURCE)
    (project / "go.mod").write_text("module example.invalid/quality\n\ngo 1.26.2\n")
    (project / "state.go").write_text(CODE + "\nfunc Extra()int{return 1}\n")
    (project / "state_test.go").write_text(TEST)
    check = ["bash", "scripts/check-go.sh"]
    output = run([*check, "lint"], project, success=False)
    assert "gofumpt" in output and "not properly formatted" in output, output
    (project / "state.go").write_text(CODE)
    run([*check, "fmt"], project)
    run(check, project)
    clean = (project / "state.go").read_text()

    # New enum/union members must fail despite default branches. Discarded
    # errors must also fail, without splitting feedback across successive runs.
    broken = clean.replace('_, err := io.WriteString(writer, "ok")\n\treturn err',
                           '_, _ = io.WriteString(writer, "ok")\n\treturn nil')
    broken += "\nconst StateRetry State = 42\n\ntype Deferred struct{}\n\nfunc (Deferred) isResult() {}\n"
    (project / "state.go").write_text(broken)
    run([*check, "fmt"], project)
    output = run([*check, "lint"], project, success=False)
    for diagnostic in ("missing cases in switch", "missing keys in map", "gochecksumtype", "errcheck", "StateRetry", "Deferred"):
        assert diagnostic in output, (diagnostic, output)
    (project / "state.go").write_text(clean)

    (project / "race_test.go").write_text(RACE)
    output = run([*check, "test"], project, success=False)
    assert "DATA RACE" in output, output
    (project / "race_test.go").unlink()

    # Retrofit preserves the original gate and only budgets current lint debt.
    legacy = Path(temporary) / "existing Go project"
    legacy.mkdir()
    run(["git", "init", "--quiet"], legacy)
    (legacy / "go.mod").write_text("module example.invalid/retrofit\n\ngo 1.26.2\n")
    original_config = '''# The team's comments and policy stay unchanged.
version: "2"
linters:
  default: none
  enable: [unused, forbidigo]
  settings:
    exhaustive:
      explicit-exhaustive-switch: true
      explicit-exhaustive-map: true
      ignore-enum-types: '.*'
    forbidigo:
      forbid:
        - pattern: '^fmt\\.Println$'
          msg: use the team logger
formatters:
  enable: [gofmt]
issues:
  fix: true
'''
    (legacy / ".golangci.yaml").write_text(original_config)
    old_code = CODE.replace('_, err := io.WriteString(writer, "ok")\n\treturn err',
                            '_, _ = io.WriteString(writer, "ok")\n\treturn nil')
    old_code += '''
func Shadow(values []int) int {
	total := 1

	if len(values) > 0 {
		total := values[0]
		if total > 0 {
			return total
		}
	}

	return total
}
'''
    (legacy / "state.go").write_text(old_code)
    run(["gofmt", "-w", "state.go"], legacy)
    run(["git", "add", "."], legacy)
    run(["git", "-c", "user.name=Go acceptance", "-c", "user.email=go@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
         "commit", "-qm", "Existing source and policy"], legacy)
    run([str(SOURCE / "bin/repo-bootstrap"), "--repo", str(legacy), "--go",
         "--skills", "go", "--pr-template", "none"], SOURCE)
    assert (legacy / ".golangci.yaml").read_text() == original_config
    before_source = (legacy / "state.go").read_bytes()
    unformatted = before_source + b'\nfunc Extra()int{return 1}\n'
    (legacy / "state.go").write_bytes(unformatted)
    run([*check, "lint"], legacy, success=False)
    assert (legacy / "state.go").read_bytes() == unformatted, "legacy auto-fix mutated Go source during a check"
    (legacy / "state.go").write_bytes(before_source)
    (legacy / ".gitignore").write_text("ignored.go\n")
    (legacy / "ignored.go").write_text('package sample\n\nfunc Ignored() {}\n')
    output = run([*check, "baseline"], legacy, success=False)
    assert "requires committed Go source" in output, output
    (legacy / "ignored.go").unlink()
    run([*check, "baseline"], legacy)
    baseline = legacy / ".go-quality-baseline.json"
    original_baseline = baseline.read_bytes()
    assert json.loads(original_baseline)["issues"], "adoption did not capture existing findings"
    assert (legacy / "state.go").read_bytes() == before_source, "adoption rewrote existing Go code"
    run([*check, "lint"], legacy)

    # New source files never inherit the legacy budget, and it cannot grow.
    added = legacy / "new.go"
    added.write_text('package sample\nimport "io"\nfunc Bad(w io.Writer) error { _, _ = io.WriteString(w, "bad"); return nil }\n')
    run(["gofmt", "-w", "new.go"], legacy)
    assert "errcheck" in run([*check, "lint"], legacy, success=False)
    run([*check, "baseline"], legacy, success=False)
    run([*check, "ratchet"], legacy, success=False)
    assert baseline.read_bytes() == original_baseline
    added.unlink()

    # Changing an enum elsewhere must still reject untouched consumers.
    added.write_text("package sample\n\nconst StateRetry State = 42\n")
    output = run([*check, "lint"], legacy, success=False)
    assert "state.go:" in output and "StateRetry" in output and "exhaustive" in output, output
    added.unlink()

    # The requested readability defaults apply to new files too.
    added.write_text('package sample\nfunc Cuddled(a, b int) int {\n x := a + 1\n y := b + 1\n if x < y { return x }\n return y\n}\n')
    run(["gofmt", "-w", "new.go"], legacy)
    assert "wsl_v5" in run([*check, "lint"], legacy, success=False)
    run([*check, "fix", "."], legacy)
    run([*check, "lint"], legacy)
    added.unlink()

    # Moving existing findings does not force unrelated cleanup; fixing them
    # shrinks the budget, and they cannot then be reintroduced.
    (legacy / "state.go").write_text("// Existing source moved down.\n" + before_source.decode())
    run([*check, "lint"], legacy)
    (legacy / "state.go").write_text(clean)
    assert "baseline findings were fixed" in run([*check, "lint"], legacy, success=False)
    run([*check, "ratchet"], legacy)
    run([*check, "lint"], legacy)
    assert len(json.loads(baseline.read_text())["issues"]) < len(json.loads(original_baseline)["issues"])
    (legacy / "state.go").write_bytes(before_source)
    assert "errcheck" in run([*check, "lint"], legacy, success=False)
    (legacy / "state.go").write_text(clean)

    added.write_text('package sample\nimport "fmt"\nfunc Print() error { _, err := fmt.Println("x"); return err }\n')
    run(["gofmt", "-w", "new.go"], legacy)
    assert "team logger" in run([*check, "lint"], legacy, success=False)
    added.unlink()

    # Changed team policy requires regenerating its merged layer explicitly.
    (legacy / ".golangci.yaml").write_text(original_config + "\n# Policy revision.\n")
    assert "existing lint policy changed" in run([*check, "lint"], legacy, success=False)
    run([str(SOURCE / "bin/repo-bootstrap"), "--repo", str(legacy), "--go",
         "--skills", "go", "--pr-template", "none"], SOURCE)
    run([*check, "lint"], legacy)

print("PASS: strict Go checks, preserved project policy, and incremental adoption without growing lint debt")
