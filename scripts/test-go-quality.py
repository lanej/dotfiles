#!/usr/bin/env python3
"""Exercise the installed Go gate with real analyzers and the race detector."""

from pathlib import Path
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
    assert "Formatting differs" in output, output
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

print("PASS: installed Go checks accept clean code and reject new variants, discarded errors, and a data race")
