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
	m.filter()
	m.preview = previewResult{details: []string{"~/src/project-00", "Empty directory"}, width: 16}
	screen := m.View()
	body := ansi.Strip(screen.Content)
	if screen.AltScreen || strings.Count(body, "\n") > 16 || !strings.Contains(body, "Empty directory") {
		t.Fatalf("81 results did not share the inline terminal with their preview:\n%s", body)
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
	m.preview = previewResult{details: []string{"~/src/project-01", "Empty directory"}, width: 16}
	body = ansi.Strip(m.View().Content)
	if strings.Count(body, "\n") != 2 || !strings.Contains(body, "Empty directory") {
		t.Fatalf("six short results should share a row alongside their preview:\n%s", body)
	}
	m.pos = 3
	m.width = 19
	grid := m.displayGeometry()
	if grid.count() != 6 || grid.vertical(m.pos, 1) != 4 || grid.vertical(m.pos, -1) != 2 {
		t.Fatal("vertical navigation lost its position after reflow")
	}
}

func TestLongPathOnlyWidensItsOwnRow(t *testing.T) {
	m := newPicker(context.Background(), config{})
	for i, label := range []string{"a", "b", "c", strings.Repeat("界", 30), "d", "e", "f"} {
		e := entry{label: label}
		e.measure()
		m.entries = append(m.entries, e)
		m.matches = append(m.matches, i)
	}
	m.measureSpacing()
	m.pos = 6
	g := m.grid(20, 2)
	if len(g.rows) != 3 || len(g.rows[0].slots) != 3 || len(g.rows[2].slots) != 3 {
		t.Fatalf("short paths did not pack on either side of the wide path: %+v", g.rows)
	}
	if g.vertical(m.pos, -g.pageHeight) != 2 {
		t.Fatal("Page Up from a partial final page should return to the corresponding column")
	}
}

func TestWidePreviewScrollsLongReadmeAndKeepsGitVisible(t *testing.T) {
	m := newPicker(context.Background(), config{})
	m.preview = previewResult{context: []string{"README.md", "First", "Second", "Last"}, details: []string{"main", "Working tree clean"}, split: 45}
	m.scroll = 2
	body, height, total := m.previewWindow(geometry{previewWidth: 94, previewHeight: 2})
	lines := strings.Split(ansi.Strip(body), "\n")
	if height != 2 || total != 4 || !strings.Contains(lines[0], "Second") || !strings.Contains(lines[0], "main") ||
		!strings.Contains(lines[1], "Last") || !strings.Contains(lines[1], "Working tree clean") {
		t.Fatalf("Git moved out of view while scrolling the README:\n%s", body)
	}
}
