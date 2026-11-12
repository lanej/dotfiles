package main

import (
	"fmt"
	"image/color"
	"os"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	"github.com/lanej/charmed/layout"
)

func (m *picker) cell(e entry, width int, selected bool) string {
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
		labelRoom = min(e.size.label, max(min(18, room/2), room-gap-ansi.StringWidth(strings.Join(fields, "  "))))
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
	rows := make([]string, 0, len(g.visible()))
	for _, row := range g.visible() {
		var line strings.Builder
		right := 0
		for c, cell := range row.slots {
			i := row.start + c
			e := m.entries[m.matches[i]]
			line.WriteString(strings.Repeat(" ", cell.x-right))
			line.WriteString(m.cell(e, cell.width, i == m.pos))
			right = cell.x + cell.width
		}
		rows = append(rows, line.String())
	}
	return strings.Join(rows, "\n")
}

func (m *picker) View() tea.View {
	if m.finished || m.err != nil || m.width < 1 || m.height < 1 {
		return tea.NewView("")
	}
	g := m.displayGeometry()
	body := m.list(g)
	count := fmt.Sprintf("%d/%d", len(m.matches), len(m.scope))
	if g.previewWidth > 0 {
		lines := m.preview.lines
		offset := min(m.scroll, max(0, len(lines)-g.previewHeight))
		end := min(len(lines), offset+g.previewHeight)
		detail := layout.Fit(strings.Join(lines[offset:end], "\n"), layout.Size{Width: g.previewWidth, Height: end - offset})
		if len(lines) > g.previewHeight {
			count += fmt.Sprintf("  preview %d-%d/%d", offset+1, end, len(lines))
		}
		if g.below {
			rule := "─"
			if m.palette.ASCII {
				rule = "-"
			}
			body = layout.Column(body, m.palette.Subtle().Render(strings.Repeat(rule, min(m.width, max(g.width, m.preview.width)))), detail)
		} else {
			rule := " │ "
			if m.palette.ASCII {
				rule = " | "
			}
			h := max(len(g.visible()), end-offset)
			border := m.palette.Subtle().Render(strings.TrimSuffix(strings.Repeat(rule+"\n", h), "\n"))
			body = layout.Row(body, border, detail)
		}
	}
	if m.detailsUnavailable {
		count += " · details unavailable"
	}
	query := m.query
	query.Resize(min(m.width-ansi.StringWidth(count)-2, ansi.StringWidth(query.Prompt)+ansi.StringWidth(query.Value())+1))
	header := ansi.Truncate(query.View()+"  "+m.palette.Subtle().Render(count), m.width, "")
	rendered := header
	if m.height > 1 {
		rendered += "\n" + body
	}
	if os.Getenv("NO_COLOR") != "" {
		rendered = ansi.Strip(rendered)
	}
	return tea.NewView(rendered)
}
