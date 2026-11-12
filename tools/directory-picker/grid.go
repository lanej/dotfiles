package main

import (
	"slices"

	"github.com/charmbracelet/x/ansi"
)

const gap = 2

type cellSize struct{ width, label int }

func (e *entry) measure() {
	e.size.label = ansi.StringWidth(e.label)
	e.size.width = 2 + e.size.label
	for _, field := range e.fields() {
		e.size.width += gap + ansi.StringWidth(field)
	}
}

// Set the grid spacing from the current path labels. An annotated worktree or an
// unusually long path spans extra slots only in its own row.
func (m *picker) measureSpacing() {
	if len(m.matches) == 0 {
		m.spacing = 1
		return
	}
	widths := make([]int, len(m.matches))
	for i, id := range m.matches {
		widths[i] = m.entries[id].size.label + 2 + gap
	}
	slices.Sort(widths)
	m.spacing = widths[len(widths)-1-len(widths)/10]
}

type slot struct{ x, width int }
type resultRow struct {
	start int
	slots []slot
}
type geometry struct {
	rows                        []resultRow
	top, bottom, active, width  int
	previewWidth, previewHeight int
	below                       bool
}

func (g geometry) visible() []resultRow { return g.rows[g.top:g.bottom] }
func (g geometry) count() int {
	if g.bottom == g.top {
		return 0
	}
	last := g.rows[g.bottom-1]
	return last.start + len(last.slots) - g.rows[g.top].start
}

func (m *picker) grid(width, height int) geometry {
	width, height = max(1, width), max(1, height)
	g := geometry{}
	if len(m.matches) == 0 {
		return g
	}
	spacing := max(1, m.spacing)
	total := -gap
	for _, id := range m.matches {
		total += m.entries[id].size.width + gap
		if total > width {
			break
		}
	}
	if total <= width {
		spacing = 1 // A single row needs only the gutter between actual labels.
	}

	x := 0
	for i, id := range m.matches {
		w := min(width, m.entries[id].size.width)
		if i == 0 || x+w > width {
			g.rows = append(g.rows, resultRow{start: i})
			x = 0
		}
		r := &g.rows[len(g.rows)-1]
		r.slots = append(r.slots, slot{x, w})
		if i == m.pos {
			g.active = len(g.rows) - 1
		}
		x += (w + gap + spacing - 1) / spacing * spacing
	}
	g.top = g.active / height * height
	g.bottom = min(len(g.rows), g.top+height)
	for _, row := range g.visible() {
		last := row.slots[len(row.slots)-1]
		g.width = max(g.width, last.x+last.width)
	}
	return g
}

// Move to the closest horizontal position in the destination row.
func (g geometry) vertical(pos, delta int) int {
	if len(g.rows) == 0 {
		return pos
	}
	row := g.rows[g.active]
	x := row.slots[pos-row.start].x
	target := g.rows[max(0, min(len(g.rows)-1, g.active+delta))]
	distance := func(other int) int {
		return max(other-x, x-other)
	}
	best := 0
	for i, cell := range target.slots {
		if distance(cell.x) < distance(target.slots[best].x) {
			best = i
		}
	}
	return target.start + best
}

func (m *picker) arrange() geometry {
	w, h := max(1, m.width), max(1, m.height-1)
	if m.previewMode < 0 || len(m.matches) == 0 {
		return m.grid(w, h)
	}
	stack := m.grid(w, max(1, h/2))
	const readablePreview = 64 // A commit subject and its file and line counts.
	if listWidth := w - readablePreview - 3; listWidth >= 20 {
		side := m.grid(listWidth, h)
		if len(side.visible()) > 3 && side.count() >= stack.count() {
			side.previewWidth, side.previewHeight = w-side.width-3, h
			return side
		}
	}
	remaining := h - len(stack.visible()) - 1
	if remaining > 0 && (m.previewMode > 0 || remaining >= 4 && (h >= 20 || stack.count() == len(m.matches))) {
		stack.below = true
		stack.previewWidth, stack.previewHeight = w, remaining
		return stack
	}
	return m.grid(w, h)
}

func (m *picker) displayGeometry() geometry {
	g := m.arrange()
	if g.previewWidth == 0 {
		return g
	}
	if len(m.preview.lines) == 0 || m.previewMode == 0 && !m.preview.useful {
		return m.grid(m.width, m.height-1)
	}
	if !g.below {
		// A directory listing can be much narrower than a formatted Git preview.
		pw := min(g.previewWidth, max(1, m.preview.width))
		g = m.grid(m.width-pw-3, m.height-1)
		g.previewWidth, g.previewHeight = pw, max(1, m.height-1)
	}
	return g
}
