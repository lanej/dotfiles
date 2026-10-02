package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
)

// darwinLogPath resolves the LaunchAgent plist's StandardOutPath (or
// StandardErrorPath, when stderrFlag is set) — see launchAgent in
// install.go, which writes these same paths beside the installed binary.
func darwinLogPath(home string, stderrFlag bool) string {
	name := "router.log"

	if stderrFlag {
		name = "router.err.log"
	}

	return filepath.Join(home, ".codex", "bedrock-router", name)
}

// linuxUnitPath resolves the installed systemd user unit file's path — see
// install.go, which writes it at this same location. journald owns the log
// data itself (there's no log file to stat), but the unit file's presence
// is a reliable proxy for "is bedrock-router installed".
func linuxUnitPath(home string) string {
	return filepath.Join(home, ".config", "systemd", "user", systemdUnitName)
}

// logCommand is a pure, no-I/O function that builds the external command
// used to display the router's logs on the current platform. It performs
// no execution and touches no filesystem state, so it's trivially testable
// without invoking any real OS binary.
func logCommand(platform, home string, lines int, follow, stderrFlag bool) (name string, args []string, err error) {
	switch platform {
	case "darwin":
		path := darwinLogPath(home, stderrFlag)
		args := []string{"-n", strconv.Itoa(lines)}

		if follow {
			// BSD tail requires flags before the file operand: a trailing
			// -f after path is parsed as a second (nonexistent) file.
			args = append(args, "-f")
		}

		args = append(args, path)
		return "tail", args, nil
	case "linux":
		if stderrFlag {
			return "", nil, errors.New("--stderr is only meaningful on macOS; journald already combines stdout and stderr")
		}

		args := []string{"--user", "-u", systemdUnitName, "-n", strconv.Itoa(lines)}

		if follow {
			args = append(args, "-f")
		}

		return "journalctl", args, nil
	default:
		return "", nil, errors.New("logs supports macOS and Linux")
	}
}

// streamCommand runs name with args, copying its combined output to stdout
// as it's produced. This is the one deliberately real exec.Command call in
// this file, kept minimal and isolated: it must NOT go through
// installEnvironment.run, which buffers everything via CombinedOutput()
// until the child exits — with --follow that would hang forever with zero
// output ever reaching the terminal.
func streamCommand(stdout io.Writer, name string, args []string) error {
	cmd := exec.Command(name, args...)
	cmd.Stdout = stdout
	cmd.Stderr = stdout
	return cmd.Run()
}

// logsCmd implements `bedrock-router logs [--lines|-n N] [--follow|-f] [--stderr]`.
// No signal.Notify is installed here: SIGINT's default disposition
// terminates both this process and the foreground tail/journalctl child
// normally when the user hits Ctrl+C during --follow.
func logsCmd(args []string, env installEnvironment, stdout io.Writer) error {
	flags := flag.NewFlagSet("logs", flag.ContinueOnError)
	var lines int
	flags.IntVar(&lines, "lines", 50, "Number of lines to show")
	flags.IntVar(&lines, "n", 50, "Number of lines to show (shorthand)")
	var follow bool
	flags.BoolVar(&follow, "follow", false, "Follow log output as it's written")
	flags.BoolVar(&follow, "f", false, "Follow log output as it's written (shorthand)")
	var stderrFlag bool
	flags.BoolVar(&stderrFlag, "stderr", false, "Show the stderr log instead of stdout (macOS only)")

	if err := flags.Parse(args); err != nil {
		return err
	}

	if flags.NArg() != 0 {
		return errors.New("unexpected logs arguments")
	}

	name, cmdArgs, err := logCommand(env.platform, env.home, lines, follow, stderrFlag)
	if err != nil {
		return err
	}

	if env.platform == "darwin" {
		path := darwinLogPath(env.home, stderrFlag)

		if _, err := os.Stat(path); err != nil {
			return fmt.Errorf("no log file at %s — is bedrock-router installed and running?", path)
		}
	}

	if env.platform == "linux" {
		path := linuxUnitPath(env.home)

		if _, err := os.Stat(path); err != nil {
			return fmt.Errorf("no systemd unit at %s — is bedrock-router installed?", path)
		}
	}

	return streamCommand(stdout, name, cmdArgs)
}
