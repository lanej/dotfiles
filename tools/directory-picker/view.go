package main

import (
	"fmt"
	"image/color"
	"os"
	"slices"
	"strings"
	"unicode/utf8"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	"github.com/lanej/charmed/layout"
)

// Match positions refer to the original runes, before clipping or spacing the columns.
func matchedField(value string, matched []int, offset, limit int, style lipgloss.Style) string {
	if limit <= 0 {
		return ""
	}
	original := value
	var prefix, suffix string
	if n := ansi.StringWidth(value); n > limit {
		// Keep a matched fragment visible when it would otherwise be clipped off the left.
		value = ansi.TruncateLeft(original, n-limit+1, "")
		skipped := utf8.RuneCountInString(original) - utf8.RuneCountInString(value)
		at, _ := slices.BinarySearch(matched, offset)
		if at < len(matched) && matched[at] < offset+skipped {
			runes := []rune(original)
			start := matched[at] - offset
			if start > 0 && limit >= 3 {
				prefix = style.Render("…")
			}
			if limit > 1 {
				suffix = style.Render("…")
			}
			value = ansi.Truncate(string(runes[start:]), limit-ansi.StringWidth(prefix+suffix), "")
			offset += start
		} else {
			prefix = style.Render("…")
			offset += skipped
		}
	}
	var out strings.Builder
	out.WriteString(prefix)
	at, _ := slices.BinarySearch(matched, offset)
	start := 0
	underlined := false
	for i := range value {
		match := at < len(matched) && matched[at] == offset
		if match != underlined {
			out.WriteString(style.Underline(underlined).UnderlineSpaces(underlined).Render(value[start:i]))
			start, underlined = i, match
		}
		if match {
			at++
		}
		offset++
	}
	out.WriteString(style.Underline(underlined).UnderlineSpaces(underlined).Render(value[start:]))
	out.WriteString(suffix)
	return out.String()
}

func (m *picker) cell(e entry, width int, selected bool) string {
	mark := "  "
	base := lipgloss.NewStyle()
	monochrome := os.Getenv("NO_COLOR") != ""
	if selected {
		mark = "› "
		if m.palette.ASCII {
			mark = "> "
		}
		if !monochrome {
			base = base.Background(m.palette.SelectionBackground)
		}
	}
	styleFor := func(fg color.Color) lipgloss.Style {
		if monochrome {
			return base
		}
		return base.Foreground(fg)
	}
	field := func(value string, offset, width int, fg color.Color) string {
		return matchedField(value, e.matched, offset, width, styleFor(fg))
	}
	pathColor := m.palette.Foreground
	if selected {
		pathColor = m.palette.SelectionForeground
	}
	branch := e.branchLabel()
	room := max(1, width-2)
	labelRoom := room
	if fields := e.fields(); len(fields) > 0 {
		labelRoom = min(e.size.label, max(min(18, room/2), room-gap-ansi.StringWidth(strings.Join(fields, "  "))))
	}
	row := styleFor(m.palette.Accent).Render(mark) + field(e.label, 0, labelRoom, pathColor)
	offset := utf8.RuneCountInString(e.label) + 1
	if branch != "" {
		branchRoom := width - ansi.StringWidth(row) - gap
		for _, trailing := range []string{e.Status, e.Agents} {
			if trailing != "" {
				branchRoom -= gap + ansi.StringWidth(trailing)
			}
		}
		if branchRoom > 0 {
			row += base.Render("  ") + field(branch, offset, branchRoom, m.palette.Muted)
		}
		offset += utf8.RuneCountInString(branch) + 1
	}
	if e.Status != "" {
		fg := m.palette.Warning
		if e.Status == "clean" {
			fg = m.palette.Success
		}
		row += base.Render("  ") + field(e.Status, offset, width-ansi.StringWidth(row)-gap, fg)
		offset += utf8.RuneCountInString(e.Status) + 1
	}
	if e.Agents != "" {
		row += base.Render("  ") + field(e.Agents, offset, width-ansi.StringWidth(row)-gap, m.palette.Accent)
	}
	if selected {
		row += base.Render(strings.Repeat(" ", max(0, width-ansi.StringWidth(row))))
	}
	return layout.Fit(row, layout.Size{Width: width, Height: 1})
}

func (m *picker) list(g geometry) string {
	if len(m.matches) == 0 {
		return m.subtle("No matches")
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

func (m *picker) subtle(value string) string {
	if os.Getenv("NO_COLOR") != "" {
		return value
	}
	return m.palette.Subtle().Render(value)
}

func (m *picker) divider(height int) string {
	rule := " │ "
	if m.palette.ASCII {
		rule = " | "
	}
	return m.subtle(strings.TrimSuffix(strings.Repeat(rule+"\n", height), "\n"))
}

func (m *picker) previewWindow(g geometry) (string, int, int) {
	p := m.preview
	if len(p.details) == 0 {
		return ansi.Truncate(m.subtle("Reading "+m.entries[m.selected()].label+"…"), g.previewWidth, ""), 1, 1
	}
	window := func(lines []string, width int) string {
		offset := min(m.scroll, max(0, len(lines)-g.previewHeight))
		end := min(len(lines), offset+g.previewHeight)
		return layout.Fit(strings.Join(lines[offset:end], "\n"), layout.Size{Width: width, Height: end - offset})
	}
	if p.split > 0 && g.previewWidth >= p.split+4 {
		h := min(p.length(), g.previewHeight)
		return layout.Row(window(p.context, p.split), m.divider(h), window(p.details, g.previewWidth-p.split-3)), h, p.length()
	}
	lines := p.details
	if len(p.context) > 0 {
		lines = slices.Concat(lines, []string{""}, p.context)
	}
	h := min(len(lines), g.previewHeight)
	return window(lines, g.previewWidth), h, len(lines)
}

func (m *picker) View() tea.View {
	if m.finished || m.width < 1 || m.height < 1 {
		return tea.NewView("")
	}
	g := m.displayGeometry()
	body := m.list(g)
	count := fmt.Sprintf("%d/%d", len(m.matches), len(m.scope))
	if g.previewWidth > 0 {
		detail, height, total := m.previewWindow(g)
		if total > g.previewHeight {
			start := min(m.scroll, total-g.previewHeight)
			count += fmt.Sprintf("  preview %d-%d/%d", start+1, start+height, total)
		}
		if g.below {
			if len(g.visible())+g.previewHeight+1 < m.height {
				rule := "─"
				if m.palette.ASCII {
					rule = "-"
				}
				body = layout.Column(body, m.subtle(strings.Repeat(rule, min(m.width, max(g.width, m.preview.width)))))
			}
			body = layout.Column(body, detail)
		} else {
			body = layout.Row(body, m.divider(max(len(g.visible()), height)), detail)
		}
	}
	if m.detailsUnavailable {
		count += " · details unavailable"
	}
	query := m.query
	query.Resize(max(1, min(m.width-ansi.StringWidth(count)-2, ansi.StringWidth(query.Prompt)+ansi.StringWidth(query.Value())+1)))
	queryView := query.View()
	if os.Getenv("NO_COLOR") != "" {
		queryView = ansi.Strip(queryView)
	}
	header := ansi.Truncate(queryView+"  "+m.subtle(count), m.width, "")
	rendered := header
	if m.height > 1 {
		rendered += "\n" + body
	}
	return tea.NewView(rendered)
}
