package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"syscall"
	"time"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
)

type observation struct {
	Ready                         bool
	Token, Branch, Status, Agents string
}
type observationError struct{ err error }

// Helpers may start Git and rendering subprocesses. Cancel the whole invocation on a new focus or exit.
func helper(ctx context.Context, args ...string) *exec.Cmd {
	cmd := exec.CommandContext(ctx, args[0], args[1:]...)
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		err := syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		if errors.Is(err, syscall.ESRCH) {
			return os.ErrProcessDone
		}
		return err
	}
	cmd.WaitDelay = time.Second
	return cmd
}

func readObservations(ctx context.Context, c config, send func(tea.Msg)) {
	cmd := helper(ctx, c.Helper, "--summaries", c.Snapshot)
	var tokens strings.Builder
	for _, row := range c.Rows {
		token, _, _ := strings.Cut(row, "\t")
		tokens.WriteString(token + "\n")
	}
	cmd.Stdin = strings.NewReader(tokens.String())
	out, err := cmd.StdoutPipe()
	if err == nil {
		err = cmd.Start()
	}
	if err == nil {
		decoder := json.NewDecoder(out)
		for {
			var update observation
			err = decoder.Decode(&update)
			if err != nil {
				break
			}
			send(update)
		}
		if !errors.Is(err, io.EOF) {
			_ = cmd.Cancel()
		}
		waitErr := cmd.Wait()
		if errors.Is(err, io.EOF) {
			err = waitErr
		}
	}
	if err != nil && ctx.Err() == nil {
		send(observationError{err})
	}
}

type previewKey struct {
	id, width, height int
	observed          bool
}
type previewResult struct {
	key              previewKey
	context, details []string
	width, split     int
}

func (p previewResult) length() int {
	if p.split > 0 {
		return max(len(p.context), len(p.details))
	}
	if len(p.context) == 0 {
		return len(p.details)
	}
	return len(p.context) + 1 + len(p.details)
}

func (m *picker) requestPreview() tea.Cmd {
	g := m.arrange()
	key := previewKey{id: m.selected(), width: g.previewWidth, height: g.previewHeight, observed: m.ready || m.detailsUnavailable}
	if m.width == 0 || key == m.requested {
		return nil
	}
	if m.stopPreview != nil {
		m.stopPreview()
	}
	if m.requested.id != key.id {
		m.preview = previewResult{}
		m.scroll = 0
	}
	m.requested = key
	if key.id < 0 || key.width == 0 || key.height == 0 {
		return nil
	}
	ctx, cancel := context.WithCancel(m.ctx)
	m.stopPreview = cancel
	selected, script := m.entries[key.id], m.config.Helper
	snapshot := ""
	if key.observed {
		snapshot = m.config.Snapshot
	}
	return func() tea.Msg {
		// Avoid launching Git while a user is moving quickly through the list.
		select {
		case <-ctx.Done():
			return nil
		case <-time.After(35 * time.Millisecond):
		}
		cmd := helper(ctx, script, "--preview-json", selected.token, snapshot)
		cmd.Env = append(os.Environ(), fmt.Sprintf("FZF_PREVIEW_COLUMNS=%d", key.width), fmt.Sprintf("FZF_PREVIEW_LINES=%d", key.height))
		raw, err := cmd.Output()
		if ctx.Err() != nil {
			return nil
		}
		var data struct {
			Context, Details []string
			Split            int
		}
		if err != nil || json.Unmarshal(raw, &data) != nil || len(data.Details) == 0 {
			data.Details = []string{selected.label, "Preview unavailable"}
		}
		result := previewResult{key: key, context: data.Context, details: data.Details, split: data.Split}
		for _, pane := range [][]string{result.context, result.details} {
			for i, line := range pane {
				pane[i] = cleanPreview(line)
				result.width = max(result.width, ansi.StringWidth(strings.TrimRight(pane[i], " ")))
			}
		}
		return result
	}
}

// Preserve styles emitted by the preview and discard terminal controls from filenames or file contents.
func cleanPreview(s string) string {
	var b strings.Builder
	var state byte
	for len(s) > 0 {
		seq, width, n, next := ansi.DecodeSequence(s, state, nil)
		state, s = next, s[n:]
		switch {
		case width > 0 || seq == "\n":
			b.WriteString(seq)
		case seq == "\t":
			b.WriteString("    ")
		case strings.HasPrefix(seq, "\x1b[") && strings.HasSuffix(seq, "m"):
			b.WriteString(seq)
		}
	}
	return b.String()
}
