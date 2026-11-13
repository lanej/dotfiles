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
	m.spacing = widths[(len(widths)-1)*9/10]
}

type slot struct{ x, width int }
type resultRow struct {
	start int
	slots []slot
}
type geometry struct {
	rows                                   []resultRow
	top, bottom, active, width, pageHeight int
	previewWidth, previewHeight            int
	below                                  bool
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
	g := geometry{pageHeight: height}
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
	if m.previewHidden || len(m.matches) == 0 || h < 2 {
		return m.grid(w, h)
	}
	// Leave two readable preview columns when the matches can fit beside them.
	const previewPair = 42*2 + 3
	const divider = 3
	if w >= max(24, min(40, m.spacing))+divider+previewPair {
		budget := min(max(w/3, m.spacing-gap), w-previewPair-divider)
		if len(m.matches) <= 3 {
			for _, id := range m.matches {
				budget = max(budget, min(w-previewPair-divider, m.entries[id].size.width))
			}
		}
		side := m.grid(budget, h)
		// In a long history, spare width can surface more matches while keeping
		// enough room for a commit subject and its diff statistics.
		if wider := w - 2*52 - 2*divider; len(side.rows) > h/2 && wider > budget {
			side = m.grid(wider, h)
		}
		side.previewWidth, side.previewHeight = w-side.width-divider, h
		return side
	}
	stack := m.grid(w, max(1, h/2))
	if w >= 84 && len(stack.rows) > 3 {
		side := m.grid(w-48-divider, h)
		side.previewWidth, side.previewHeight = w-side.width-divider, h
		return side
	}
	stack.below = true
	stack.previewWidth = w
	stack.previewHeight = h - len(stack.visible())
	if stack.previewHeight > 1 {
		stack.previewHeight-- // separator above the preview
	}
	return stack
}

func (m *picker) displayGeometry() geometry {
	g := m.arrange()
	if g.previewWidth == 0 || g.below || len(m.preview.details) == 0 || len(m.preview.context) > 0 {
		return g
	}
	// A short filesystem listing can give the rest of its width back to matches.
	width := min(g.previewWidth, max(1, m.preview.width))
	g = m.grid(m.width-width-3, max(1, m.height-1))
	g.previewWidth, g.previewHeight = width, max(1, m.height-1)
	return g
}
