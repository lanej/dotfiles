package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestLegacyFilesystemJSON(t *testing.T) {
	t.Parallel()

	cases := []struct{ name, encoded, want string }{
		{"raw filename byte", `"/tmp/repo-\udcff"`, "/tmp/repo-\xff"},
		{"Unicode and newline", `"/tmp/\u2603\nrepo"`, "/tmp/☃\nrepo"},
		{"surrogate pair", `"/tmp/\ud83d\ude00"`, "/tmp/😀"},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			t.Parallel()

			var path gitText
			if err := json.Unmarshal([]byte(item.encoded), &path); err != nil {
				t.Fatal(err)
			}

			if string(path) != item.want {
				t.Fatalf("path bytes %q, want %q", path, item.want)
			}

			encoded, err := json.Marshal(path)
			if err != nil {
				t.Fatal(err)
			}

			if !json.Valid(encoded) {
				t.Fatalf("invalid registry JSON: %s", encoded)
			}

			if strings.Contains(item.encoded, `\udcff`) && !strings.Contains(string(encoded), `\udcff`) {
				t.Fatalf("lost legacy byte escape: %s", encoded)
			}
		})
	}
}

func TestBudgetUnitsAndPrecision(t *testing.T) {
	t.Parallel()

	for _, item := range []struct{ input, want string }{{"2KiB", "2048"}, {"2KB", "2000"}, {"0B", "0"}, {"1000000000000000000000000GiB", "1073741824000000000000000000000000"}} {
		t.Run(item.input, func(t *testing.T) {
			t.Parallel()

			actual, err := parseSize(item.input)
			if err != nil {
				t.Fatal(err)
			}

			if actual.String() != item.want {
				t.Fatalf("budget %s, want %s", actual, item.want)
			}
		})
	}
}
