// SPDX-License-Identifier: GPL-3.0-only
package hints

import (
	"net/url"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode"

	"github.com/kovidgoyal/kitty/tools/wcswidth"
)

// FilePane is the originating Zellij pane, in zero-based Kitty cells.
// A nil pane means no receiver is available; only real OSC 8 links are offered.
type FilePane struct {
	Left, Top, Width, Height int
	Files bool
}

type fileTarget struct {
	Path string  `json:"path"`
	Host *string `json:"host,omitempty"`
	Line int     `json:"line,omitempty"`
	Column int   `json:"column,omitempty"`
}

var (
	imageEnd = regexp.MustCompile("(?i)\\.(?:png|jpe?g|webp|gif|bmp|tiff?|avif|ico|svg|heic|jxl)$")
	filePosition = regexp.MustCompile("^(.*?):([1-9][0-9]*)(?::([1-9][0-9]*))?$")
	fileFragment = regexp.MustCompile("^(?:L)?([1-9][0-9]*)(?:C([1-9][0-9]*))?(?:-(?:L)?[1-9][0-9]*)?$")
	baseName = regexp.MustCompile("^[^/]+\\.[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
	dotFile = regexp.MustCompile("^\\.[a-zA-Z0-9_][\\p{L}\\p{N}_.-]*$")
	quotedPosition = "(?::[1-9][0-9]*(?::[1-9][0-9]*)?:?)?"
	pathPattern = regexp.MustCompile("\"([^\"\\n]+)\""+quotedPosition+"|'([^'\\n]+)'"+quotedPosition+"|"+string(rune(96))+"([^"+string(rune(96))+"\\n]+)"+string(rune(96))+quotedPosition+"|([^\\s\\p{Z}<>\"'"+string(rune(96))+"()\\[\\]{},;│┃]+)")
)

func hasControl(s string) bool {
	return strings.IndexFunc(s, func(r rune) bool { return r < 32 }) >= 0
}

func positionNumbers(match []string, target *fileTarget) bool {
	line, err := strconv.Atoi(match[1])
	if err != nil || line < 1 {
		return false
	}
	target.Line = line
	if match[2] != "" {
		column, err := strconv.Atoi(match[2])
		if err != nil || column < 1 {
			return false
		}
		target.Column = column
	}
	return true
}

func parseFileTarget(value string) (fileTarget, bool) {
	var target fileTarget
	if strings.HasPrefix(value, "file:") {
		u, err := url.Parse(value)
		if err != nil || !strings.HasPrefix(u.Path, "/") || hasControl(u.Path) {
			return target, false
		}
		host := strings.ToLower(u.Hostname())
		target.Path, target.Host = u.Path, &host
		if u.Fragment != "" {
			match := fileFragment.FindStringSubmatch(u.Fragment)
			if match == nil || !positionNumbers(match, &target) {
				return fileTarget{}, false
			}
		}
		return target, true
	}
	if strings.Contains(value, "://") || strings.HasPrefix(value, "mailto:") || strings.HasPrefix(value, "dotfiles-") {
		return target, false
	}
	value = strings.TrimRight(value, ".,;!?")
	if match := filePosition.FindStringSubmatch(strings.TrimSuffix(value, ":")); match != nil {
		value = match[1]
		if !positionNumbers(match[1:], &target) {
			return fileTarget{}, false
		}
	}
	if value == "" || hasControl(value) {
		return fileTarget{}, false
	}
	switch value {
	case "Makefile", "Dockerfile", "Containerfile", "README", "LICENSE", "COPYING", "Justfile", "Gemfile", "Rakefile":
	default:
		if !strings.Contains(value, "/") && !baseName.MatchString(value) && !dotFile.MatchString(value) {
			return fileTarget{}, false
		}
	}
	target.Path = value
	return target, true
}

type displayCell struct {
	text string
	start, end, x, width int
}

type displayRow struct {
	cells []displayCell
	start, end int
}

func displayRows(plain string) []displayRow {
	var rows []displayRow
	for start := 0; start <= len(plain); {
		end := len(plain)
		if i := strings.IndexAny(plain[start:], "\r\n"); i >= 0 {
			end = start + i
		}
		line := strings.ReplaceAll(plain[start:end], "\x00", " ")
		row := displayRow{start: start, end: end}
		ascii := true
		for i := range len(line) {
			if line[i] >= 128 {
				ascii = false
				break
			}
		}
		if ascii {
			for i := range len(line) {
				row.cells = append(row.cells, displayCell{line[i:i+1], start+i, start+i+1, i, 1})
			}
		} else {
			iter := wcswidth.NewCellIterator(line)
			offset, x := start, 0
			for iter.Forward() {
				g := iter.Current()
				width := wcswidth.Stringwidth(g)
				row.cells = append(row.cells, displayCell{g, offset, offset+len(g), x, width})
				offset += len(g)
				x += width
			}
		}
		rows = append(rows, row)
		if end == len(plain) {
			break
		}
		start = end + 1
	}
	return rows
}

type sourceByte struct {
	offset, row int
}

func paneText(rows []displayRow, links []Mark, pane FilePane) (string, []sourceByte) {
	var text strings.Builder
	var positions []sourceByte
	joinNext := false
	linkIndex := 0
	for y, row := range rows {
		if y < pane.Top || y-pane.Top >= pane.Height {
			continue
		}
		var line strings.Builder
		var points []sourceByte
		for _, cell := range row.cells {
			if cell.x < pane.Left || cell.x-pane.Left+cell.width > pane.Width {
				continue
			}
			for linkIndex < len(links) && links[linkIndex].End <= cell.start {
				linkIndex++
			}
			if linkIndex < len(links) && links[linkIndex].Start < cell.end {
				line.WriteString(strings.Repeat(" ", cell.width))
				for range cell.width {
					points = append(points, sourceByte{-1, y})
				}
				continue
			}
			line.WriteString(cell.text)
			for i := range len(cell.text) {
				points = append(points, sourceByte{cell.start+i, y})
			}
		}
		raw := line.String()
		content := strings.TrimRightFunc(raw, unicode.IsSpace)
		start := 0
		if joinNext {
			start = len(content) - len(strings.TrimLeftFunc(content, unicode.IsSpace))
		} else {
			text.WriteByte('\n')
			positions = append(positions, sourceByte{-1, y})
		}
		text.WriteString(content[start:])
		positions = append(positions, points[start:len(content)]...)
		words := strings.Fields(content)
		joinNext = false
		if len(words) != 0 {
			last := words[len(words)-1]
			joinNext = len(raw)-len(content) <= 4 &&
				(strings.Contains(last, "/") || strings.ContainsRune("-_.", rune(last[len(last)-1]))) &&
				!imageEnd.MatchString(last) &&
				!filePosition.MatchString(strings.TrimSuffix(last, ":")) &&
				!strings.ContainsRune(")]}\"'"+string(rune(96))+",;", rune(last[len(last)-1]))
		}
	}
	return text.String(), positions
}

func allowedFile(value string, pane FilePane) (fileTarget, bool) {
	target, ok := parseFileTarget(value)
	return target, ok && (pane.Files || imageEnd.MatchString(target.Path))
}

func containedLink(rows []displayRow, mark Mark, pane FilePane) bool {
	found := false
	for y, row := range rows {
		if mark.End <= row.start || mark.Start >= row.end {
			continue
		}
		for _, cell := range row.cells {
			if cell.end <= mark.Start || cell.start >= mark.End {
				continue
			}
			found = true
			if y < pane.Top || y-pane.Top >= pane.Height || cell.x < pane.Left || cell.x-pane.Left+cell.width > pane.Width {
				return false
			}
		}
	}
	return found
}

func fileMarks(plain string, links []Mark, pane FilePane) []Mark {
	rows := displayRows(plain)
	marks := append([]Mark(nil), links...)
	for i := range marks {
		m := &marks[i]
		if target, ok := allowedFile(m.Text, pane); ok && containedLink(rows, *m, pane) {
			m.Groupdict = map[string]any{"file": target}
		}
	}
	text, positions := paneText(rows, links, pane)
	for _, match := range pathPattern.FindAllStringSubmatchIndex(text, -1) {
		for group := 1; group <= 4; group++ {
			start, end := match[2*group], match[2*group+1]
			if start < 0 || start == end {
				continue
			}
			value := text[start:end]
			if group != 4 && end < match[1] {
				value += text[end+1:match[1]]
			}
			target, ok := allowedFile(value, pane)
			if !ok || positions[start].offset < 0 {
				break
			}
			first := positions[start]
			last := first.offset
			// A hard-wrapped file has a single hint on the first fragment.
			for _, point := range positions[start:end] {
				if point.row != first.row || point.offset < 0 {
					break
				}
				last = point.offset
			}
			marks = append(marks, Mark{Start: first.offset, End: last+1, Text: target.Path, Groupdict: map[string]any{"file": target}})
			break
		}
	}
	sort.SliceStable(marks, func(i, j int) bool { return marks[i].Start < marks[j].Start })
	return marks
}

func hasFileMarks(marks []Mark) bool {
	for _, m := range marks {
		if _, ok := m.Groupdict["file"]; ok {
			return true
		}
	}
	return false
}
