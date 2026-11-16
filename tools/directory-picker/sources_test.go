package main

import "testing"

func TestCleanPreview(t *testing.T) {
	input := "\x1b[31mred\x1b[0m\tfile\x1b]0;title\a\n界\x1b[2J"
	want := "\x1b[31mred\x1b[0m    file\n界"
	if got := cleanPreview(input); got != want {
		t.Errorf("cleanPreview() = %q, want %q", got, want)
	}
}
