// SPDX-License-Identifier: GPL-3.0-only
package main
import (
	"fmt"
	"os"
	"github.com/kovidgoyal/kitty/kittens/hints"
)
func main(){
	if err:=hints.RunStyledHints();err!=nil{
		fmt.Fprintln(os.Stderr,err)
		os.Exit(1)
	}
}
