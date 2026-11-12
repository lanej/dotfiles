package main

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/charmbracelet/x/ansi"
)

func TestInlineGridFitsContentAndReleasesShellRows(t *testing.T) {
	m := newPicker(context.Background(), config{Title: "Directories"})
	m.width, m.height = 204, 54
	for i := range 81 {
		e := entry{label: fmt.Sprintf("~/src/project-%02d", i)}
		if i == 0 {
			e.observation = observation{Branch: "feature/long-branch-name", Status: "dirty 3", Agents: "Codex"}
		}
		e.measure()
		m.entries = append(m.entries, e)
		m.scope = append(m.scope, i)
	}
	if err := m.filter(); err != nil {
		t.Fatal(err)
	}
	screen := m.View()
	body := ansi.Strip(screen.Content)
	if screen.AltScreen || strings.Count(body, "\n") > 12 {
		t.Fatalf("81 results claimed more than 12 inline rows:\n%s", body)
	}
	for _, e := range m.entries {
		if !strings.Contains(body, e.label) {
			t.Fatalf("%q missing from the visible grid", e.label)
		}
	}
	if cmd := m.requestPreview(); cmd == nil {
		t.Fatal("Git and directory previews must start before the agent snapshot is ready")
	}
	m.stopPreview()

	m.matches = m.matches[1:7]
	m.pos = 0
	m.measureSpacing()
	body = ansi.Strip(m.View().Content)
	if strings.Count(body, "\n") != 1 {
		t.Fatalf("six short results should fit below the query in one row:\n%s", body)
	}
	m.pos = 3
	m.width = 19
	grid := m.displayGeometry()
	if grid.count() != 6 || grid.vertical(m.pos, 1) != 4 || grid.vertical(m.pos, -1) != 2 {
		t.Fatal("vertical navigation lost its position after reflow")
	}
}
