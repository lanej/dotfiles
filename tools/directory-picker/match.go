package main

import (
	"slices"
	"strings"

	"github.com/junegunn/fzf/src/algo"
	"github.com/junegunn/fzf/src/util"
)

// A space joins required groups. A standalone | joins alternatives within one group.
type searchTerm struct {
	match                         algo.Algo
	pattern                       []rune
	inverse, exactCase, normalize bool
}

type queryPattern [][]searchTerm

func init() { algo.Init("default") }

func parseQuery(query string) queryPattern {
	var groups queryPattern
	var group []searchTerm
	startGroup, afterBar := false, false
	for _, token := range strings.Split(strings.ReplaceAll(query, `\ `, "\t"), " ") {
		if token == "" {
			continue
		}
		if token == "|" && len(group) > 0 && !afterBar {
			startGroup, afterBar = false, true
			continue
		}
		token = strings.ReplaceAll(token, "\t", " ")
		lower := strings.ToLower(token)
		t := searchTerm{match: algo.FuzzyMatchV2, exactCase: token != lower,
			normalize: string(algo.NormalizeRunes([]rune(lower))) == lower}
		if !t.exactCase {
			token = lower
		}
		if t.inverse = strings.HasPrefix(token, "!"); t.inverse {
			t.match = algo.ExactMatchNaive
			token = token[1:]
		}
		suffix := len(token) > 1 && strings.HasSuffix(token, "$")
		if suffix {
			t.match = algo.SuffixMatch
			token = strings.TrimSuffix(token, "$")
		}
		switch {
		case len(token) > 2 && strings.HasPrefix(token, "'") && strings.HasSuffix(token, "'"):
			t.match, token = algo.ExactMatchBoundary, token[1:len(token)-1]
		case strings.HasPrefix(token, "'"):
			t.match, token = algo.ExactMatchNaive, token[1:]
			if t.inverse {
				t.match = algo.FuzzyMatchV2
			}
		case strings.HasPrefix(token, "^"):
			t.match, token = algo.PrefixMatch, token[1:]
			if suffix {
				t.match = algo.EqualMatch
			}
		}
		if token != "" {
			if startGroup {
				groups = append(groups, group)
				group = nil
			}
			t.pattern = []rune(token)
			group = append(group, t)
			startGroup = true
		}
		afterBar = false
	}
	if len(group) > 0 {
		groups = append(groups, group)
	}
	return groups
}

// fzf supplies rune positions for fuzzy terms and a contiguous range for exact terms.
func (p queryPattern) match(value string, slab *util.Slab) ([]int, bool) {
	input := util.ToChars([]byte(value))
	var positions []int
	for _, alternatives := range p {
		matched := false
		for _, term := range alternatives {
			res, pos := term.match(term.exactCase, term.normalize, true, &input, term.pattern, true, slab)
			if term.inverse {
				matched = matched || res.Start < 0
				continue
			}
			if res.Start >= 0 {
				matched = true
				if pos != nil {
					positions = append(positions, *pos...)
				} else {
					for i := res.Start; i < res.End; i++ {
						positions = append(positions, i)
					}
				}
				break
			}
		}
		if !matched {
			return nil, false
		}
	}
	slices.Sort(positions)
	return slices.Compact(positions), true
}

func (m *picker) filter() {
	focused := m.selected()
	query := parseQuery(m.query.Value())
	m.matches = m.matches[:0]
	for _, id := range m.scope {
		e := &m.entries[id]
		e.matched = nil
		if len(query) > 0 {
			text := strings.Join(append([]string{e.label}, e.fields()...), " ")
			positions, ok := query.match(text, m.slab)
			if !ok {
				continue
			}
			e.matched = positions
		}
		m.matches = append(m.matches, id)
	}
	m.pos = max(0, slices.Index(m.matches, focused))
	m.measureSpacing()
}
