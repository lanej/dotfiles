// SPDX-License-Identifier: GPL-3.0-only
package hints

import (
	"strings"
	"testing"
	"math/rand"
)

func testRequest(ansi string)*StyledRequest{
	r:=&StyledRequest{ANSI:ansi,Cols:80,Type:"url",Foreground:0xd8dee9,Background:0x2e3440,
		Target:0x3b4252,KeyBG:0x434c5e,KeyFG:0xebcb8b,Accent:0x88c0d0,DimOpacity:.4}
	r.Colors[2]=0xa3be8c;r.Colors[3]=0xebcb8b;r.Colors[6]=0x88c0d0
	return r
}
func TestDotfilesStyledANSI(t *testing.T){
	r:=testRequest("\x1b[33mwarning\x1b[0m  \x1b[36mhttps://example.org/\x1b[32mpath\x1b[0m")
	f,e:=newStyledFrame(r);if e!=nil{t.Fatal(e)}
	if len(f.marks)!=1||f.marks[0].Text!="https://example.org/path"{t.Fatalf("wrong marks: %#v",f.marks)}
	p:=f.spans("")
	if len(p)!=3||p[0].kind!='h'||p[1].text!=" a "||p[2].start!=17{t.Fatalf("wrong scheme spans: %#v",p)}
	out:=f.render("")
	if strings.Contains(out,"https://")||!strings.Contains(out,"example.org/")||!strings.Contains(out,"38;2;136;192;208")||!strings.Contains(out,"38;2;163;190;140"){t.Fatalf("wrong rendered colors or scheme: %q",out)}
}
func TestDotfilesContrast(t *testing.T){
	rng:=rand.New(rand.NewSource(429));p:=make(colorPolicy)
	for range 4000{
		f,b:=uint32(rng.Intn(1<<24)),uint32(rng.Intn(1<<24))
		for _,dim:=range []bool{false,true}{if x:=p.correct(f,b,4.5,dim);ratio(x,b)<4.5{t.Fatalf("%06x/%06x -> %06x %.4f",f,b,x,ratio(x,b))}}
	}
}
func TestDotfilesNativeHyperlink(t *testing.T){
	r:=testRequest("\x1b]8;;https://example.org/exact\x1b\\\x1b[36m測 release notes\x1b[0m\x1b]8;;\x1b\\")
	r.Type="hyperlink"
	f,e:=newStyledFrame(r);if e!=nil{t.Fatal(e)}
	if len(f.marks)!=1||f.marks[0].Text!="https://example.org/exact"{t.Fatalf("wrong OSC 8 target: %#v",f.marks)}
	p:=f.spans("")
	if len(p)<1||p[0].text!="a " {t.Fatalf("wide glyph replacement did not preserve width: %#v",p)}
}

func TestDotfilesFilePolicy(t *testing.T) {
	for _, tc := range []struct {
		text, path string
		line, column int
	}{
		{"src/main.rs:42:7:", "src/main.rs",42,7},
		{"file:///tmp/source%20file.lua#L8C3","/tmp/source file.lua",8,3},
		{"file://localhost/tmp/a.py#L9-L12","/tmp/a.py",9,0},
		{"README","README",0,0},
		{".zshrc",".zshrc",0,0},
		{"https://example.org/code.rs:42","",0,0},
		{"file:///tmp/a%0Ab.rs","",0,0},
	} {
		target,ok:=parseFileTarget(tc.text)
		if ok!=(tc.path!="") || target.Path!=tc.path || target.Line!=tc.line || target.Column!=tc.column {t.Fatalf("%q: %#v, %t",tc.text,target,ok)}
	}
}
func TestDotfilesFilePane(t *testing.T) {
	r:=testRequest(strings.Repeat(" ",15)+"(docs/screenshots/fixture-   │ other/worktree.png\n"+
		"  running-overview.png).\n"+
		"\x1b]8;;https://example.org/exact?q=yes\x1b\\release notes\x1b]8;;\x1b\\\n"+
		"\x1b]8;;file:///tmp/space%20here.png\x1b\\thumbnail\x1b]8;;\x1b\\\n"+
		"測 \"screenshots/a b.png\"\n"+
		"src/main.rs:42:7")
	r.Cols=80
	r.Type="hyperlink"
	// End the first fragment close to the pane's right edge.
	r.Pane=&FilePane{Width:43,Height:6,Files:true}
	f,err:=newStyledFrame(r)
	if err!=nil {t.Fatal(err)}
	got:=map[string]bool{}
	for _,m:=range f.marks{
		if target,ok:=m.Groupdict["file"].(fileTarget);ok{got[target.Path]=true}
	}
	for _,path:=range []string{"docs/screenshots/fixture-running-overview.png","/tmp/space here.png","screenshots/a b.png","src/main.rs"} {
		if !got[path]{t.Fatalf("missing %q from %#v",path,got)}
	}
	if got["other/worktree.png"] {t.Fatal("routed a file outside the originating pane")}
	r.Pane.Files=false
	f,err=newStyledFrame(r)
	if err!=nil {t.Fatal(err)}
	for _,m:=range f.marks{if target,ok:=m.Groupdict["file"].(fileTarget);ok&&target.Path=="src/main.rs"{t.Fatal("offered a source file to an image-only receiver")}}
}
