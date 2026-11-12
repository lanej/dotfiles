package main

import (
	"context"
	"slices"
	"time"

	tea "charm.land/bubbletea/v2"
	"github.com/lanej/charmed/input"
	"github.com/lanej/charmed/theme"
)

type picker struct {
	ctx                context.Context
	config             config
	palette            theme.Theme
	query              input.Text
	entries            []entry
	byToken            map[string]int
	scope, matches     []int
	pos, width, height int
	ready              bool
	refreshPending     bool
	detailsUnavailable bool
	previewMode        int // 0 automatic, 1 explicitly open, -1 explicitly closed
	requested          previewKey
	stopPreview        context.CancelFunc
	preview            previewResult
	scroll             int
	chosen             string
	err                error
}

type refreshMatches struct{}

func newPicker(ctx context.Context, c config) *picker {
	palette := c.palette()
	query := input.NewText(input.TextOptions{Value: c.Query, Width: 40, Theme: palette})
	query.Prompt = c.Title + " > "
	query.CursorEnd()
	return &picker{ctx: ctx, config: c, palette: palette, query: query, byToken: make(map[string]int), requested: previewKey{id: -1}}
}

func (m *picker) Init() tea.Cmd { return m.query.Focus() }

func (m *picker) selected() int {
	if m.pos >= len(m.matches) {
		return -1
	}
	return m.matches[m.pos]
}

func (m *picker) applyFilter() tea.Cmd {
	if err := m.filter(); err != nil {
		m.err = err
		return tea.Quit
	}
	return m.requestPreview()
}

func (m *picker) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		m.query.Resize(max(1, m.width-12))
		return m, m.requestPreview()
	case observation:
		if msg.Ready {
			m.ready = true
			return m, m.requestPreview()
		}
		if id, ok := m.byToken[msg.Token]; ok {
			m.entries[id].observation = msg
			if m.query.Value() == "" {
				return m, m.requestPreview()
			}
			if !m.refreshPending {
				m.refreshPending = true
				// A burst of Git results needs one matcher invocation for the current query.
				return m, tea.Tick(25*time.Millisecond, func(time.Time) tea.Msg { return refreshMatches{} })
			}
			return m, nil
		}
	case refreshMatches:
		m.refreshPending = false
		return m, m.applyFilter()
	case observationError:
		m.detailsUnavailable = true
	case previewResult:
		if msg.key == m.requested {
			m.preview = msg
		}
	case tea.KeyPressMsg:
		g := m.displayGeometry()
		step := 0
		switch msg.String() {
		case "enter":
			if id := m.selected(); id >= 0 {
				m.chosen = m.entries[id].token
				return m, tea.Quit
			}
			return m, nil
		case "esc", "ctrl+c":
			return m, tea.Quit
		case "up", "ctrl+p":
			step = -1
		case "down", "ctrl+n":
			step = 1
		case "pgup":
			step = -g.rows * g.cols
		case "pgdown":
			step = g.rows * g.cols
		case "left", "right":
			if g.cols > 1 {
				step = g.rows
				if msg.String() == "left" {
					step = -step
				}
			}
		case "ctrl+space", "ctrl+@":
			if len(m.matches) > 0 {
				m.scope = slices.Clone(m.matches)
				m.query.SetValue("")
				return m, m.applyFilter()
			}
			return m, nil
		case "ctrl+/", "ctrl+_":
			if g.previewWidth > 0 {
				m.previewMode = -1
			} else {
				m.previewMode = 1
			}
			return m, m.requestPreview()
		case "ctrl+j", "ctrl+k":
			if msg.String() == "ctrl+j" {
				m.scroll = min(max(0, len(m.preview.lines)-g.previewHeight), m.scroll+1)
			} else {
				m.scroll = max(0, m.scroll-1)
			}
			return m, nil
		}
		if step != 0 {
			m.pos = max(0, min(len(m.matches)-1, m.pos+step))
			return m, m.requestPreview()
		}
	}
	value := m.query.Value()
	var cmd tea.Cmd
	m.query, cmd = m.query.Update(msg)
	if value != m.query.Value() {
		return m, tea.Batch(cmd, m.applyFilter())
	}
	return m, cmd
}
