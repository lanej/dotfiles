package main

import (
	"os"
	"os/exec"
	"slices"
	"strings"
	"testing"
)

func TestMatchRunes(t *testing.T) {
	const path = "~/src/payment-retries"
	for _, tc := range []struct {
		text, query, marked string
	}{
		{path, "pmt", "pmt"},
		{path, "'retry | 'retries", "retries"},
		{"~/src/café-界", "cafe 界", "café界"},
		{"~/src/payments retry dirty 3 Codex", "'Codex dirty", "dirtyCodex"},
		{"~/release notes", `release\ notes$`, "release notes"},
		{path, "!other", ""},
	} {
		positions, ok := parseQuery(tc.query).match(tc.text, nil)
		var marked strings.Builder
		for _, i := range positions {
			marked.WriteRune([]rune(tc.text)[i])
		}
		if !ok || marked.String() != tc.marked {
			t.Errorf("%q on %q underlined %q, want %q", tc.query, tc.text, marked.String(), tc.marked)
		}
	}
}

func TestFilterAgreesWithInstalledFzf(t *testing.T) {
	bin, err := exec.LookPath("fzf")
	if err != nil {
		t.Skip("fzf binary unavailable for comparison")
	}
	rows := []string{"~/src/payments", "~/src/payment-retries dirty 3 Codex", "café", "界-retry",
		"release notes", "release notes again", "Billing clean", "debit | credit", "it costs $", "my café"}
	for _, query := range []string{"pmt", "^~/src/ !dirty", "'retry | clean$", "'dirty' 'Codex", "cafe", "^café$",
		`release\ notes`, `release\ `, "!pay | !retry", "'notes'", "  ", "!", "$", "|", "||", "debit | | credit", "界"} {
		cmd := exec.Command(bin, "--no-sort", "--filter="+query)
		cmd.Env = append(os.Environ(), "FZF_DEFAULT_OPTS=", "FZF_DEFAULT_OPTS_FILE=")
		cmd.Stdin = strings.NewReader(strings.Join(rows, "\n"))
		out, err := cmd.Output()
		if err != nil && cmd.ProcessState.ExitCode() != 1 {
			t.Fatal(err)
		}
		expected := strings.FieldsFunc(string(out), func(r rune) bool { return r == '\n' })
		p := parseQuery(query)
		var got []string
		for _, row := range rows {
			if _, match := p.match(row, nil); match {
				got = append(got, row)
			}
		}
		if !slices.Equal(got, expected) {
			t.Errorf("query %q: got %q, fzf returned %q", query, got, expected)
		}
	}
}
