// SPDX-License-Identifier: GPL-3.0-only
// Compiled inside the pinned Kitty hints package. Reuse native matching, key
// allocation, Unicode width handling, event loop and result serialization.
package hints

import (
	"errors"
	"fmt"
	"math"
	"regexp"
	"sort"
	"strings"

	"github.com/kovidgoyal/kitty/tools/tui/loop"
	"github.com/kovidgoyal/kitty/tools/tui/sgr"
	"github.com/kovidgoyal/kitty/tools/wcswidth"
)

const styledAlphabet = "asdfghjkl"

type StyledRequest struct {
	ANSI string
	Cols, Rows int
	Type string
	Pane *FilePane
	URLPrefixes, URLExcludedCharacters string
	Foreground, Background, Target, KeyBG, KeyFG, Accent uint32
	Colors [256]uint32
	DimOpacity float64
}

type paint struct {
	fg, bg, underline uint32
	attrs, decoration uint8
}

type styleRun struct {
	start, end int
	style paint
}

type styledText struct {
	plain string
	runs []styleRun
}

var snapshotEscape = regexp.MustCompile("\x1b(?:\\[[0-9;:]*?m|\\][^\x1b]*?\x1b\\\\)")
var schemeRE = regexp.MustCompile("^[A-Za-z][A-Za-z0-9+.-]*://")

// Kitty's own SGR representation handles indexed/truecolor and attributes.
// Parse individual parameters because reset and semicolon-form extended colors
// must update the *persistent* state, not just the most recent SGR delta.
func applySnapshotSGR(state *sgr.SGR, raw string) {
	parts := strings.Split(raw, ";")
	for i := 0; i < len(parts); i++ {
		part := parts[i]
		if part == "" || part == "0" {
			*state = sgr.SGR{}
			continue
		}
		if part == "38" || part == "48" || part == "58" {
			if i+1 >= len(parts) { continue }
			n := 0
			switch parts[i+1] { case "2": n = 4; case "5": n = 2 }
			if n == 0 || i+n >= len(parts) { continue }
			part = strings.Join(parts[i:i+n+1], ":")
			i += n
		}
		// Ignore malformed extended color sequences rather than calling the
		// upstream parser with an empty color-argument slice.
		if strings.HasPrefix(part,"38:") || strings.HasPrefix(part,"48:") || strings.HasPrefix(part,"58:") {
			p := strings.Split(part,":")
			if len(p)<3 || (p[1]=="2" && len(p)<5) { continue }
		}
		state.ApplySGR(sgr.SGRFromCSI(part+"m"))
	}
}

func resolveColor(c sgr.ColorVal, fallback uint32, req *StyledRequest) uint32 {
	if !c.Is_set || c.Is_default { return fallback }
	if c.Val.Is_numbered { return req.Colors[c.Val.Red] }
	return uint32(c.Val.Red)<<16 | uint32(c.Val.Green)<<8 | uint32(c.Val.Blue)
}

func resolvedPaint(state sgr.SGR, req *StyledRequest) paint {
	fg, bg := resolveColor(state.Foreground,req.Foreground,req), resolveColor(state.Background,req.Background,req)
	if state.Reverse.Val { fg,bg=bg,fg }
	if state.Dim.Val { fg=blend(fg,bg,req.DimOpacity) }
	p := paint{fg:fg,bg:bg,decoration:uint8(state.Underline_style.Val)}
	if state.Bold.Val { p.attrs |= 1 }
	if state.Italic.Val { p.attrs |= 2 }
	if state.Strikethrough.Val { p.attrs |= 4 }
	if p.decoration != 0 { p.underline=resolveColor(state.Underline_color,fg,req) }
	return p
}

// One allocation per SGR run, not one per visible cell. Matching offsets are
// byte offsets in the same plain text used by the native matcher.
func parseStyledText(input string, req *StyledRequest) (styledText,error) {
	var state sgr.SGR
	var plain strings.Builder
	plain.Grow(len(input))
	runs := make([]styleRun,0,64)
	add := func(s string) {
		if s=="" { return }
		start := plain.Len()
		plain.WriteString(s)
		p := resolvedPaint(state,req)
		if n:=len(runs); n>0 && runs[n-1].style==p { runs[n-1].end=plain.Len() } else {
			runs=append(runs,styleRun{start,plain.Len(),p})
		}
	}
	last:=0
	for _, loc := range snapshotEscape.FindAllStringIndex(input,-1) {
		add(input[last:loc[0]])
		e:=input[loc[0]:loc[1]]
		if strings.HasPrefix(e,"\x1b[") { applySnapshotSGR(&state,e[2:len(e)-1]) }
		last=loc[1]
	}
	add(input[last:])
	text:=plain.String()
	if strings.ContainsRune(text,27) || strings.ContainsRune(text,'\t') {
		return styledText{},fmt.Errorf("unsupported control in ANSI snapshot")
	}
	return styledText{text,runs},nil
}

var linear = func() (v [256]float64) {
	for i:=range v {
		x:=float64(i)/255
		if x<=.04045 {v[i]=x/12.92} else {v[i]=math.Pow((x+.055)/1.055,2.4)}
	}
	return
}()

func lum(c uint32) float64 {
	return .2126*linear[c>>16&255]+.7152*linear[c>>8&255]+.0722*linear[c&255]
}
func ratio(f,b uint32) float64 {
	a,z:=lum(f)+.05,lum(b)+.05
	return max(a,z)/min(a,z)
}
func channels(c uint32) [3]float64 {
	return [3]float64{float64(c>>16&255),float64(c>>8&255),float64(c&255)}
}
func pack(c [3]float64) uint32 {
	return uint32(math.RoundToEven(c[0]))<<16|uint32(math.RoundToEven(c[1]))<<8|uint32(math.RoundToEven(c[2]))
}
func blend(f,b uint32,t float64) uint32 {
	a,z:=channels(f),channels(b)
	for i:=range a {a[i]=a[i]*t+z[i]*(1-t)}
	return pack(a)
}

type contrastKey struct { fg,bg uint32; minimum float64; dim bool }
type colorPolicy map[contrastKey]uint32

// Keep the current overlay's WCAG floor. Kitty's GPU contrast setting is
// global and applied before alpha dimming; do not change the user's shader
// options. This bounded per-frame policy operates on unique style runs.
func (cache colorPolicy) correct(f,b uint32, minimum float64, dim bool) uint32 {
	key:=contrastKey{f,b,minimum,dim}
	if x,ok:=cache[key];ok{return x}
	best:=f
	if ratio(f,b)>=minimum {
		if dim {
			if x:=blend(f,b,.55);ratio(x,b)>=minimum {best=x} else {
				lo,hi:=.55,1.0
				for range 12 {mid:=(lo+hi)/2;x:=blend(f,b,mid);if ratio(x,b)>=minimum{hi,best=mid,x}else{lo=mid}}
			}
		}
	} else {
		// HSL midpoint: vary lightness while retaining hue and saturation.
		a:=channels(f)
		loC,hiC:=min(a[0],a[1],a[2])/255,max(a[0],a[1],a[2])/255
		l:=(loC+hiC)/2
		midpoint:=[3]float64{.5,.5,.5}
		if hiC>loC {
			sat:=(hiC-loC)/(1-math.Abs(2*l-1))
			for i:=range a {midpoint[i]=.5+((a[i]/255-loC)/(hiC-loC)-.5)*sat}
		}
		at:=func(light float64) uint32 {
			z:=midpoint
			for i:=range z {if light<=.5 {z[i]*=light*510}else{z[i]=255-(1-z[i])*(1-light)*510}}
			return pack(z)
		}
		distance:=math.Inf(1)
		for _,end:=range []float64{0,1} {
			extreme:=at(end)
			if ratio(extreme,b)<minimum {continue}
			lo,hi,answer:=0.0,1.0,extreme
			for range 12 {
				m:=(lo+hi)/2;x:=at(l+(end-l)*m)
				if ratio(x,b)>=minimum {hi,answer=m,x}else{lo=m}
			}
			if d:=math.Abs(end-l)*hi;d<distance {distance,best=d,answer}
		}
	}
	if len(cache)<65536 {cache[key]=best}
	return best
}

type styledMark struct { Mark; label string }
type span struct { start,end,mark int; kind byte; text string }

type styledFrame struct {
	req *StyledRequest
	text styledText
	marks []styledMark
	cache colorPolicy
}

func newStyledFrame(req *StyledRequest) (*styledFrame,error) {
	input:=convert_text(req.ANSI,req.Cols)
	styled,err:=parseStyledText(input,req)
	if err!=nil{return nil,err}
	frame:=&styledFrame{req:req,text:styled,cache:make(colorPolicy)}
	plain, links := process_escape_codes(input)
	if plain!=styled.plain {return nil,fmt.Errorf("ANSI and native matcher offsets diverged")}
	var marks []Mark
	if req.Type=="hyperlink" {
		marks=links
		if req.Pane!=nil {
			marks=fileMarks(plain,links,*req.Pane)
		}
	} else {
		prefixes,excluded:=req.URLPrefixes,req.URLExcludedCharacters
		if prefixes=="" {prefixes="default"}
		if excluded=="" {excluded="default"}
		opts:=&Options{Type:req.Type,Alphabet:styledAlphabet,Ascending:true,PrefixFree:true,
			MinimumMatchLength:3,UrlPrefixes:prefixes,UrlExcludedCharacters:excluded}
		_,marks,_,err=find_marks(input,opts)
		var none *ErrNoMatches
		if errors.As(err,&none) {return frame,nil}
		if err!=nil{return nil,err}
	}
	sort.SliceStable(marks,func(i,j int)bool{return marks[i].Start<marks[j].Start})
	offset:=hints_to_skip(len(marks),len(styledAlphabet))
	lastEnd:=0
	for _,m:=range marks {
		if m.Start<lastEnd||m.End>len(plain)||m.End<=m.Start {continue}
		m.Index=len(frame.marks)+offset
		frame.marks=append(frame.marks,styledMark{m,encode_hint(m.Index,styledAlphabet)})
		lastEnd=m.End
	}
	return frame,nil
}

func (f *styledFrame) spans(prefix string) []span {
	out:=make([]span,0,len(f.marks)*4)
	for i,m:=range f.marks {
		if !strings.HasPrefix(m.label,prefix){continue}
		label:=strings.TrimPrefix(m.label,prefix)
		if label=="" {continue}
		text:=f.text.plain[m.Start:m.End]
		scheme:=schemeRE.FindString(text)
		start,end:=m.Start,m.Start
		if scheme!="" && len(text)>len(scheme) && strings.HasPrefix(strings.ToLower(m.Text),strings.ToLower(scheme)) {
			end=m.Start+len(scheme)
			if strings.ToLower(scheme)!="https://" {start=end-3}
			if end-start<len(label) {start,end=m.Start,m.Start}
		}
		add:=func(a,b int,kind byte,text string) {if a<b {out=append(out,span{a,b,i,kind,text})}}
		if end>start {
			add(m.Start,start,'t',"")
			padding:=min(2,end-start-len(label))
			badge:=label
			if padding>0 {badge+=" "}
			if padding==2 {badge=" "+badge}
			add(start,end-len(badge),'h',"")
			add(end-len(badge),end,'k',badge)
			add(end,m.End,'t',"")
			continue
		}
		// For a hyperlink without a visible scheme consume whole native
		// grapheme cells, not bytes or runes; preserve subsequent columns.
		line:=text
		if at:=strings.IndexAny(line,"\r\n\x00");at>=0 {line=line[:at]}
		iter:=wcswidth.NewCellIterator(line)
		width,consumed:=0,0
		for width<len(label) && iter.Forward() {
			s:=iter.Current();consumed+=len(s);width+=wcswidth.Stringwidth(s)
		}
		if width==0 {add(m.Start,m.End,'t',"");continue}
		badge:=label[:min(len(label),width)]
		badge+=strings.Repeat(" ",width-len(badge))
		add(m.Start,m.Start+consumed,'k',badge)
		add(m.Start+consumed,m.End,'t',"")
	}
	return out
}

func writePaint(b *strings.Builder,p paint) {
	fmt.Fprintf(b,"\x1b[0;38;2;%d;%d;%d;48;2;%d;%d;%d",p.fg>>16&255,p.fg>>8&255,p.fg&255,p.bg>>16&255,p.bg>>8&255,p.bg&255)
	if p.attrs&1!=0 {b.WriteString(";1")}
	if p.attrs&2!=0 {b.WriteString(";3")}
	if p.attrs&4!=0 {b.WriteString(";9")}
	if p.decoration!=0 {fmt.Fprintf(b,";4:%d;58:2::%d:%d:%d",p.decoration,p.underline>>16&255,p.underline>>8&255,p.underline&255)}
	b.WriteByte('m')
}
var cleanRows=strings.NewReplacer("\x00"," ","\r","\r\n","\n","\r\n")

// Sweep the two sorted lists of style runs and mark spans. No reconstruction
// of a cell grid, no per-URL selection bitmap, no repeated whole-screen splice.
func (f *styledFrame) render(prefix string) string {
	var b strings.Builder
	b.Grow(len(f.text.plain)*2)
	b.WriteString("\x1b[0m")
	spans:=f.spans(prefix)
	ri,si,pos:=0,0,0
	var last paint
	havePaint:=false

	put:=func(p paint,text string) {
		if p.decoration==0 {p.underline=0}
		if !havePaint || p!=last {writePaint(&b,p);last=p;havePaint=true}
		b.WriteString(text)
	}
	for pos<len(f.text.plain) && ri<len(f.text.runs) {
		r:=f.text.runs[ri]
		if pos>=r.end{ri++;continue}
		for si<len(spans)&&spans[si].end<=pos {si++}
		next:=r.end
		p:=r.style
		kind:=byte('c')
		if si<len(spans){
			s:=spans[si]
			if pos<s.start {next=min(next,s.start)} else {
				next=min(next,s.end);kind=s.kind
				if kind=='k' {
					// A badge replaces the whole span, regardless of SGR
					// boundaries inside the consumed scheme/graphemes.
					amber:=true
					for _,ch:=range s.text {
						fg:=f.req.Foreground
						if ch!=' '&&amber{fg=f.req.KeyFG;amber=false}
						put(paint{fg:f.cache.correct(fg,f.req.KeyBG,4.5,false),bg:f.req.KeyBG,attrs:1},string(ch))
					}
					pos=s.end
					continue
				}
			}
		}
		text:=f.text.plain[pos:next]
		switch kind {
		case 'h':
			text=strings.Repeat(" ",len(text));p.attrs=0;p.decoration=0
		case 't':
			if p.bg==f.req.Background {p.bg=f.req.Target}else{p.bg=blend(f.req.Target,p.bg,.65)}
			p.fg=f.cache.correct(p.fg,p.bg,4.5,false)
			if p.decoration==0{p.decoration=1}
			p.underline=f.cache.correct(f.req.Accent,p.bg,3,false)
		default:
			p.fg=f.cache.correct(p.fg,p.bg,4.5,true)
			if p.decoration!=0{p.underline=f.cache.correct(p.underline,p.bg,3,true)}
		}
		put(p,cleanRows.Replace(text))
		pos=next
	}
	b.WriteString("\x1b[0m")
	return b.String()
}

func (f *styledFrame) hit(prefix string,x,y int) int {
	start:=0
	for range y {
		i:=strings.IndexAny(f.text.plain[start:],"\r\n")
		if i<0{return -1};start+=i+1
	}
	end:=len(f.text.plain)
	if i:=strings.IndexAny(f.text.plain[start:],"\r\n");i>=0{end=start+i}
	for _,s:=range f.spans(prefix) {
		if s.kind=='h'||s.end<=start||s.start>=end{continue}
		left:=wcswidth.Stringwidth(strings.ReplaceAll(f.text.plain[start:max(start,s.start)],"\x00"," "))
		right:=left+wcswidth.Stringwidth(strings.ReplaceAll(f.text.plain[max(start,s.start):min(end,s.end)],"\x00"," "))
		if x>=left&&x<right{return s.mark}
	}
	return -1
}

// Entry called by the separately built, opt-in native helper. No modification
// to installed Kitty binaries, and no resident process.
// pick uses Kitty's native event loop and returns the exact selected mark.
func (f *styledFrame) pick() (*Mark,error) {
	if len(f.marks)==0{return nil,nil}
	lp,err:=loop.New(loop.NoAlternateScreen,loop.OnlyDisambiguateKeys);if err!=nil{return nil,err}
	lp.MouseTrackingMode(loop.BUTTONS_ONLY_MOUSE_TRACKING)
	prefix:=""
	chosen:=-1
	draw:=func(){
		lp.StartAtomicUpdate()
		lp.ClearScreen()
		lp.QueueWriteString(f.render(prefix))
		lp.EndAtomicUpdate()
	}
	choose:=func(i int){chosen=i;lp.Quit(0)}
	lp.OnInitialize=func()(string,error){
		lp.SetCursorVisible(false);lp.AllowLineWrapping(false);draw();lp.SendOverlayReady();return "",nil
	}
	lp.OnFinalize=func()string{lp.SetCursorVisible(true);return ""}
	lp.OnResize=func(_, current loop.ScreenSize)error{
		if int(current.WidthCells)!=f.req.Cols || int(current.HeightCells)!=f.req.Rows {lp.Quit(1)}
		return nil
	}
	lp.OnText=func(text string,_,paste bool)error{
		if paste{return nil}
		changed:=false
		for _,ch:=range text{
			candidate:=prefix+string(ch)
			found:=-1
			for i,m:=range f.marks{
				if strings.HasPrefix(m.label,candidate){found=i}
			}
			if found<0{continue}
			prefix=candidate;changed=true
			if f.marks[found].label==prefix{choose(found);return nil}
		}
		if changed{draw()};return nil
	}
	lp.OnKeyEvent=func(ev *loop.KeyEvent)error{
		if ev.MatchesPressOrRepeat("esc"){ev.Handled=true;lp.Quit(1)}
		if ev.MatchesPressOrRepeat("backspace"){ev.Handled=true;if len(prefix)>0{prefix=prefix[:len(prefix)-1];draw()}}
		return nil
	}
	lp.OnMouseEvent=func(ev *loop.MouseEvent)error{
		if ev.Event_type==loop.MOUSE_CLICK && ev.Buttons&loop.LEFT_MOUSE_BUTTON!=0 {
			if i:=f.hit(prefix,ev.Cell.X,ev.Cell.Y);i>=0{choose(i)}
		}
		return nil
	}
	if err=lp.Run();err!=nil{return nil,err}
	if chosen>=0{return &f.marks[chosen].Mark,nil}
	return nil,nil
}
