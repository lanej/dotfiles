package main

import (
	"fmt"
	"image/color"
	"os"
	"slices"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	"github.com/lanej/charmed/layout"
)

const gap = 2

type geometry struct {
	rows, cols, listWidth, listHeight int
	previewWidth, previewHeight       int
	below                             bool
}

func (m *picker) cellWidth() int {
	widths := make([]int, 0, len(m.matches))
	for _, id := range m.matches {
		e := m.entries[id]
		width := 2 + ansi.StringWidth(e.label)
		for _, field := range e.fields() {
			width += gap + ansi.StringWidth(field)
		}
		widths = append(widths, width)
	}
	if len(widths) == 0 {
		return 12
	}
	slices.Sort(widths)
	// One unusually long path can be shortened without forcing every other path into one column.
	return max(12, widths[len(widths)-1-len(widths)/10])
}

func (m *picker) grid(width, height, cell int) geometry {
	height = max(1, height)
	needed := max(1, (len(m.matches)+height-1)/height)
	cols := min(needed, max(1, (width+gap)/(cell+gap)))
	rows := max(1, min(height, (len(m.matches)+cols-1)/cols))
	return geometry{cols: cols, rows: rows, listWidth: width, listHeight: height}
}

// Plan from the current matches before rendering a width-dependent preview.
// The preview can surrender unused space without triggering a render/measure loop.
func (m *picker) arrange() geometry {
	w, h := m.width, max(1, m.height-1)
	cell := m.cellWidth()
	g := m.grid(w, h, cell)
	if m.previewMode < 0 || len(m.matches) == 0 {
		return g
	}
	natural := g.cols*cell + (g.cols-1)*gap
	// On wide panes a very long label may still scroll within its cell.
	if w-natural-3 >= 36 || (w >= 96 && g.cols == 1) {
		list := min(natural, w-39)
		g = m.grid(list, h, cell)
		g.previewWidth, g.previewHeight = w-list-3, h
		return g
	}
	if m.height >= 32 || m.previewMode > 0 {
		ph := max(1, min(h-2, h*2/5))
		g = m.grid(w, h-ph-1, cell)
		g.previewWidth, g.previewHeight, g.below = w, ph, true
	}
	return g
}

func (m *picker) displayGeometry() geometry {
	g := m.arrange()
	if g.previewWidth == 0 {
		return g
	}
	if m.previewMode == 0 && !m.preview.useful {
		return m.grid(m.width, max(1, m.height-1), m.cellWidth())
	}
	if !g.below && m.preview.width > 0 {
		pw := min(g.previewWidth, max(12, m.preview.width))
		g = m.grid(m.width-pw-3, g.listHeight, m.cellWidth())
		g.previewWidth, g.previewHeight = pw, g.listHeight
	} else if g.below && len(m.preview.lines) > 0 {
		ph := min(g.previewHeight, len(m.preview.lines))
		g = m.grid(m.width, max(1, m.height-ph-2), m.cellWidth())
		g.previewWidth, g.previewHeight, g.below = m.width, ph, true
	}
	return g
}

func (m *picker) cell(e entry, width, pathWidth int, selected bool) string {
	mark := "  "
	base := lipgloss.NewStyle()
	if selected {
		mark = "› "
		if m.palette.ASCII {
			mark = "> "
		}
		base = base.Background(m.palette.SelectionBackground)
	}
	paint := func(value string, fg color.Color) string { return base.Foreground(fg).Render(value) }
	pathColor := m.palette.Foreground
	if selected {
		pathColor = m.palette.SelectionForeground
	}
	branch := e.branchLabel()
	room := max(1, width-2)
	labelRoom := room
	fields := e.fields()
	if len(fields) > 0 {
		labelRoom = min(pathWidth, max(min(18, room/2), room-gap-ansi.StringWidth(strings.Join(fields, "  "))))
	}
	label := e.label
	if n := ansi.StringWidth(label); n > labelRoom {
		label = ansi.TruncateLeft(label, n-labelRoom+1, "…")
	}
	row := paint(mark, m.palette.Accent) + paint(layout.Fit(label, layout.Size{Width: labelRoom, Height: 1}), pathColor)
	if branch != "" {
		row += paint("  "+branch, m.palette.Muted)
	}
	if e.Status != "" {
		fg := m.palette.Warning
		if e.Status == "clean" {
			fg = m.palette.Success
		}
		row += paint("  "+e.Status, fg)
	}
	if e.Agents != "" {
		row += paint("  "+e.Agents, m.palette.Accent)
	}
	if selected {
		row += base.Render(strings.Repeat(" ", max(0, width-ansi.StringWidth(row))))
	}
	return layout.Fit(row, layout.Size{Width: width, Height: 1})
}

func (m *picker) list(g geometry) string {
	if len(m.matches) == 0 {
		return m.palette.Subtle().Render("No matches")
	}
	start := (m.pos / (g.rows * g.cols)) * g.rows * g.cols
	width := max(1, (g.listWidth-(g.cols-1)*gap)/g.cols)
	pathWidth := 0
	for _, id := range m.matches[start:min(len(m.matches), start+g.cols*g.rows)] {
		pathWidth = max(pathWidth, ansi.StringWidth(m.entries[id].label))
	}
	rows := make([]string, 0, g.rows)
	for r := 0; r < g.rows; r++ {
		cells := make([]string, 0, g.cols)
		for c := 0; c < g.cols; c++ {
			i := start + c*g.rows + r
			if i >= len(m.matches) {
				break
			}
			cells = append(cells, m.cell(m.entries[m.matches[i]], width, pathWidth, i == m.pos))
		}
		rows = append(rows, strings.Join(cells, strings.Repeat(" ", gap)))
	}
	return strings.Join(rows, "\n")
}

func (m *picker) View() tea.View {
	g := m.displayGeometry()
	body := m.list(g)
	if g.previewWidth > 0 {
		lines := m.preview.lines
		offset := min(m.scroll, len(lines))
		detail := layout.Fit(strings.Join(lines[offset:min(len(lines), offset+g.previewHeight)], "\n"), layout.Size{Width: g.previewWidth, Height: g.previewHeight})
		body = layout.Fit(body, layout.Size{Width: g.listWidth, Height: g.listHeight})
		if g.below {
			rule := "─"
			if m.palette.ASCII {
				rule = "-"
			}
			body = layout.Column(body, m.palette.Subtle().Render(strings.Repeat(rule, m.width)), detail)
		} else {
			rule := " │ "
			if m.palette.ASCII {
				rule = " | "
			}
			border := m.palette.Subtle().Render(strings.TrimSuffix(strings.Repeat(rule+"\n", g.listHeight), "\n"))
			body = layout.Row(body, border, detail)
		}
	}
	count := fmt.Sprintf(" %d/%d", len(m.matches), len(m.scope))
	if m.detailsUnavailable {
		count += " · details unavailable"
	}
	header := layout.Fit(m.query.View(), layout.Size{Width: max(1, m.width-ansi.StringWidth(count)), Height: 1}) + m.palette.Subtle().Render(count)
	rendered := layout.Fit(header+"\n"+body, layout.Size{Width: m.width, Height: m.height})
	if os.Getenv("NO_COLOR") != "" {
		rendered = ansi.Strip(rendered)
	}
	v := tea.NewView(rendered)
	v.AltScreen = true
	return v
}
