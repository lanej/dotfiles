// SPDX-License-Identifier: GPL-3.0-only
package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/kovidgoyal/kitty/kittens/hints"
	"github.com/kovidgoyal/kitty/tools/tui"
)

func main() {
	mode := "select"
	if len(os.Args) == 2 {
		mode = strings.TrimPrefix(os.Args[1], "--")
	} else if len(os.Args) != 1 {
		fmt.Fprintln(os.Stderr, "usage: hint-native [--probe | --render]")
		os.Exit(2)
	}
	if err := hints.RunStyledHints(mode); err != nil {
		if mode == "select" {
			if output, encodeErr := tui.KittenOutputSerializer()(map[string]string{"error": err.Error()}); encodeErr == nil {
				fmt.Print(output)
			}
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
