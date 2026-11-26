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
