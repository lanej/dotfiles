// SPDX-License-Identifier: GPL-3.0-only
package main

import (
	"fmt"
	"os"
	"strconv"

	"github.com/kovidgoyal/kitty/kittens/hints"
	"github.com/kovidgoyal/kitty/tools/tui"
)

func main(){
	if len(os.Args)!=3 {
		fmt.Fprintln(os.Stderr,"usage: hint-native url|hyperlink SOURCE_WINDOW_ID")
		os.Exit(2)
	}
	id,err:=strconv.ParseUint(os.Args[2],10,32)
	if err==nil {err=hints.RunDirectHints(os.Args[1],uint(id))}
	if err!=nil {
		fmt.Fprintln(os.Stderr,"Kitty hints:",err)
		if os.Getenv("KITTY_WINDOW_ID") != "" {tui.HoldTillEnter(true)}
		os.Exit(1)
	}
}
