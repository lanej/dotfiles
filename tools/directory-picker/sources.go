package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"slices"
	"strconv"
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

func (m *picker) filter() error {
	focused := m.selected()
	query := m.query.Value()
	if query == "" {
		m.matches = slices.Clone(m.scope)
	} else {
		var data strings.Builder
		for _, id := range m.scope {
			e := m.entries[id]
			fmt.Fprintf(&data, "%d\t%s\x00", id, strings.Join(append([]string{e.label}, e.fields()...), " "))
		}
		cmd := exec.CommandContext(m.ctx, "fzf", "--no-sort", "--read0", "--print0", "--delimiter=\t", "--nth=2..", "--filter="+query)
		cmd.Env = append(os.Environ(), "FZF_DEFAULT_OPTS=", "FZF_DEFAULT_OPTS_FILE=")
		cmd.Stdin = strings.NewReader(data.String())
		out, err := cmd.Output()
		var exit *exec.ExitError
		if err != nil && !(errors.As(err, &exit) && exit.ExitCode() == 1) {
			return fmt.Errorf("fzf filter: %w", err)
		}
		m.matches = nil
		for record := range strings.SplitSeq(strings.TrimSuffix(string(out), "\x00"), "\x00") {
			if record == "" {
				continue
			}
			field, _, _ := strings.Cut(record, "\t")
			id, err := strconv.Atoi(field)
			if err != nil || id < 0 || id >= len(m.entries) {
				return fmt.Errorf("invalid fzf result %q", field)
			}
			m.matches = append(m.matches, id)
		}
	}
	m.pos = max(0, slices.Index(m.matches, focused))
	m.measureSpacing()
	return nil
}

type previewKey struct {
	id, width, height int
	observed          bool
}
type previewResult struct {
	width  int
	key    previewKey
	lines  []string
	useful bool
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
		cmd := helper(ctx, script, "--preview", selected.token, snapshot, "--inline")
		cmd.Env = append(os.Environ(), fmt.Sprintf("FZF_PREVIEW_COLUMNS=%d", key.width), fmt.Sprintf("FZF_PREVIEW_LINES=%d", key.height))
		raw, err := cmd.Output()
		if ctx.Err() != nil {
			return nil
		}
		if err != nil {
			raw = append(raw, []byte("\nPreview unavailable")...)
		}
		content := strings.TrimRight(cleanPreview(string(raw)), "\n ")
		useful := content != ""
		if !useful {
			content = selected.label + "  (empty directory)"
		}
		lines := strings.Split(content, "\n")
		width := 0
		for _, line := range lines {
			width = max(width, ansi.StringWidth(strings.TrimRight(line, " ")))
		}
		return previewResult{key: key, width: width, lines: lines, useful: useful}
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
