// directory-picker-ui draws on the controlling terminal and returns one opaque path token.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/lanej/charmed/theme"
)

type config struct {
	Title, Query, Helper, Snapshot string
	Rows                           []string
	Theme                          struct {
		Symbols string
		Roles   map[string]string
	}
}

type entry struct {
	token, label, detail string
	size                 cellSize
	matched              []int
	observation
}

func (e entry) branchLabel() string {
	if e.detail != "" {
		return e.detail
	}
	return e.Branch
}

func (e entry) fields() []string {
	var fields []string
	for _, field := range []string{e.branchLabel(), e.Status, e.Agents} {
		if field != "" {
			fields = append(fields, field)
		}
	}
	return fields
}

func (c config) palette() theme.Theme {
	t := theme.New(theme.Dark)
	r := c.Theme.Roles
	t.ASCII = c.Theme.Symbols == "ascii"
	t.Foreground = lipgloss.Color(r["text"])
	t.Muted = lipgloss.Color(r["text.muted"])
	t.Accent = lipgloss.Color(r["accent"])
	t.Warning = lipgloss.Color(r["status.warning"])
	t.Success = lipgloss.Color(r["status.success"])
	t.Border = lipgloss.Color(r["border"])
	t.SelectionForeground = lipgloss.Color(r["selection.fg"])
	t.SelectionBackground = lipgloss.Color(r["selection.bg"])
	return t
}

func run() (int, error) {
	var c config
	if err := json.NewDecoder(os.Stdin).Decode(&c); err != nil {
		return 2, err
	}
	tty, err := os.OpenFile("/dev/tty", os.O_RDWR, 0)
	if err != nil {
		return 2, err
	}
	defer tty.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	m := newPicker(ctx, c)
	for _, row := range c.Rows {
		fields := strings.Split(row, "\t")
		if len(fields) != 3 {
			return 2, fmt.Errorf("invalid directory row")
		}
		id := len(m.entries)
		m.byToken[fields[0]] = id
		e := entry{token: fields[0], label: fields[1], detail: fields[2]}
		e.measure()
		m.entries = append(m.entries, e)
		m.scope = append(m.scope, id)
	}
	m.filter()
	program := tea.NewProgram(m, tea.WithInput(tty), tea.WithOutput(tty))
	done := make(chan struct{})
	go func() {
		defer close(done)
		readObservations(ctx, c, program.Send)
	}()
	_, err = program.Run()
	cancel()
	<-done
	if err != nil {
		return 2, err
	}
	if m.chosen == "" {
		return 130, nil
	}
	_, err = fmt.Fprintln(os.Stdout, m.chosen)
	return 0, err
}

func main() {
	status, err := run()
	if err != nil {
		fmt.Fprintln(os.Stderr, "directory-picker:", err)
		os.Exit(2)
	}
	os.Exit(status)
}
