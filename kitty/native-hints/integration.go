// SPDX-License-Identifier: GPL-3.0-only
package hints

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/kovidgoyal/kitty/tools/cmd/at"
	"github.com/kovidgoyal/kitty/tools/config"
)

const (
	receiverRequest = "\x1b[24;7~"
	receiverBuilding = "dotfiles-hints-building"
	receiverFailed = "dotfiles-hints-error"
)

var (
	receiverPattern = regexp.MustCompile("^dotfiles-hints(-v2)?://([0-9a-f]{32})/([0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)/([0-9]+)$")
	cursorReport = regexp.MustCompile("\x1b\\[([0-9]+);([0-9]+)H")
)

type windowState struct {
	ID uint `json:"id"`
	PID int `json:"pid"`
	Lines int `json:"lines"`
	Columns int `json:"columns"`
	Alternate bool `json:"in_alternate_screen"`
	UserVars map[string]string `json:"user_vars"`
	Foreground []struct{ Cmdline []string `json:"cmdline"` } `json:"foreground_processes"`
}

type kittyClient struct {
	id uint
	match string
}

func (c kittyClient) text(command string, payload map[string]any) (string,error) {
	raw, err := at.DotfilesSocketRequest(command,payload,false)
	if err != nil {return "",err}
	var text string
	err=json.Unmarshal(raw,&text)
	return text,err
}

func (c kittyClient) window() (windowState,error) {
	var tree []struct{ Tabs []struct{ Windows []windowState } }
	raw,err:=c.text("ls",map[string]any{"match":c.match})
	if err!=nil{return windowState{},err}
	if err=json.Unmarshal([]byte(raw),&tree);err!=nil{return windowState{},err}
	for _,osw:=range tree{for _,tab:=range osw.Tabs{for _,w:=range tab.Windows{if w.ID==c.id{return w,nil}}}}
	return windowState{},fmt.Errorf("source window %d no longer exists",c.id)
}

func (w windowState) zellij() bool {
	if !w.Alternate{return false}
	for _,p:=range w.Foreground {
		if len(p.Cmdline)==0{continue}
		switch filepath.Base(p.Cmdline[0]) {
		case "zellij": return true
		case "ssh": if w.UserVars["dotfiles_zellij"]!=""{return true}
		}
	}
	return false
}

func (c kittyClient) send(data string) error {
	_,err:=at.DotfilesSocketRequest("send-text",map[string]any{
		"match":c.match,"data":"base64:"+base64.StdEncoding.EncodeToString([]byte(data)),
		"bracketed_paste":"disable",
	},true)
	return err
}

func paletteRequest(ansi, mode, pipe, colors string) (StyledRequest,error) {
	req:=StyledRequest{ANSI:ansi,Type:mode,DimOpacity:.4}
	var scrolled,x,y int
	n,err:=fmt.Sscanf(pipe,"%d:%d,%d:%d,%d",&scrolled,&x,&y,&req.Rows,&req.Cols)
	if err!=nil||n!=5||req.Cols<1||req.Rows<1||req.Cols>10000||req.Rows>10000{
		return req,fmt.Errorf("invalid KITTY_PIPE_DATA geometry: %q",pipe)
	}
	values:=make(map[string]uint32,264)
	for _,line:=range strings.Split(colors,"\n") {
		p:=strings.Fields(line)
		if len(p)!=2||!strings.HasPrefix(p[1],"#"){continue}
		v,err:=strconv.ParseUint(p[1][1:],16,24)
		if err==nil{values[p[0]]=uint32(v)}
	}
	roles:=[]struct{name string;value *uint32}{
		{"foreground",&req.Foreground},{"background",&req.Background},{"color0",&req.Target},
		{"selection_background",&req.KeyBG},{"color3",&req.KeyFG},{"url_color",&req.Accent},
	}
	for _,role:=range roles{
		v,ok:=values[role.name];if !ok{return req,fmt.Errorf("missing live color %s",role.name)}
		*role.value=v
	}
	for i:=range req.Colors{
		v,ok:=values[fmt.Sprintf("color%d",i)]
		if !ok{return req,fmt.Errorf("missing live color%d",i)}
		req.Colors[i]=v
	}
	return req,nil
}

// These are the actual foreground settings read by the native Go matcher.
// Never alter global Kitty configuration from the picker.
func configuredPolicy(req *StyledRequest) (string,error) {
	hyperlinks:="yes"
	err:=config.ReadKittyConfig(func(key,value string)error{
		switch key{
		case "dim_opacity":
			v,err:=strconv.ParseFloat(value,64);if err!=nil||v<0||v>1{return fmt.Errorf("invalid dim_opacity %q",value)}
			req.DimOpacity=v
		case "allow_hyperlinks": hyperlinks=strings.ToLower(strings.TrimSpace(value))
		}
		return nil
	})
	return hyperlinks,err
}

type receiverState struct {
	marker,ticket string
	x,y int
	pane FilePane
}

func markerAtCursor(ansi string, cols int)(receiverState,error){
	var result receiverState
	loc:=cursorReport.FindAllStringSubmatchIndex(ansi,-1)
	if len(loc)==0{return result,fmt.Errorf("Kitty did not report the source cursor")}
	m:=loc[len(loc)-1]
	y,err:=strconv.Atoi(ansi[m[2]:m[3]]);if err!=nil{return result,err}
	x,err:=strconv.Atoi(ansi[m[4]:m[5]]);if err!=nil{return result,err}
	result.x,result.y=x-1,y-1
	// get-text --cursor appends cursor visibility and position controls after
	// the snapshot. They are not part of the display text or matching offsets.
	body:=ansi[:m[0]]
	body=strings.TrimSuffix(strings.TrimSuffix(body,"\x1b[?25h"),"\x1b[?25l")
	plain,links:=process_escape_codes(convert_text(body,cols))
	rows:=displayRows(plain)
	if result.y<0||result.y>=len(rows){return result,nil}
	for _,cell:=range rows[result.y].cells {
		if result.x<cell.x||result.x>=cell.x+cell.width{continue}
		for _,link:=range links{
			if link.Start<=cell.start&&cell.start<link.End{result.marker=link.Text;break}
		}
		break
	}
	matches:=receiverPattern.FindStringSubmatch(result.marker)
	if matches==nil{return result,nil}
	nums:=make([]int,6)
	for i:=range nums{
		num,err:=strconv.Atoi(matches[i+3]);if err!=nil||num<0||num>10000{return receiverState{},fmt.Errorf("invalid receiver geometry")}
		nums[i]=num
	}
	result.ticket=matches[2]
	result.pane=FilePane{Left:max(0,nums[0]+result.x-nums[4]),Top:max(0,nums[1]+result.y-nums[5]),Width:nums[2],Height:nums[3],Files:matches[1]!=""}
	if result.pane.Width<1||result.pane.Height<1{return receiverState{},fmt.Errorf("empty receiver pane")}
	return result,nil
}

func (c kittyClient) marker(cols int)(receiverState,error){
	raw,err:=c.text("get-text",map[string]any{"match":c.match,"extent":"screen","ansi":true,"wrap_markers":true,"cursor":true})
	if err!=nil{return receiverState{},err}
	return markerAtCursor(raw,cols)
}

func (c kittyClient) acquireReceiver(req *StyledRequest)(*receiverState,error){
	previous,err:=c.marker(req.Cols);if err!=nil{return nil,err}
	// Never start a second receiver over an existing one.
	if previous.ticket!=""||previous.marker==receiverBuilding||previous.marker==receiverFailed{
		return nil,fmt.Errorf("a file receiver is already active")
	}
	if err=c.send(receiverRequest);err!=nil{return nil,err}
	start:=time.Now()
	deadline:=start.Add(5*time.Second)
	for time.Now().Before(deadline) {
		state,err:=c.marker(req.Cols);if err!=nil{return nil,err}
		switch state.marker{
		case receiverFailed:return nil,fmt.Errorf("Zellij file helper update failed")
		case receiverBuilding:deadline=start.Add(300*time.Second)
		}
		if state.ticket!=""&&state.marker!=previous.marker {
			if err=c.send("!");err!=nil{return nil,err}
			return &state,nil
		}
		time.Sleep(50*time.Millisecond)
	}
	// The original receiver may be unavailable on an older/unmanaged session.
	// It will release itself if no ACK arrives. Never send a file without a ticket.
	return nil,nil
}

func (c kittyClient) releaseReceiver(req *StyledRequest, original windowState, receiver *receiverState, target *fileTarget)error{
	current,err:=c.window();if err!=nil{return err}
	if current.PID!=original.PID||current.Lines!=req.Rows||current.Columns!=req.Cols{
		return fmt.Errorf("source window changed; file selection was not sent")
	}
	now,err:=c.marker(req.Cols);if err!=nil{return err}
	if now.marker!=receiver.marker{
		return fmt.Errorf("receiver changed; file selection was not sent")
	}
	payload:=""
	if target!=nil{
		data,err:=json.Marshal(target);if err!=nil{return err}
		payload=base64.RawURLEncoding.EncodeToString(data)
		if len(receiver.ticket)+len(payload)+1>16*1024{return fmt.Errorf("file selection exceeds receiver protocol limit")}
	}
	// The receiver independently validates its ticket, originating pane, cwd
	// and Zellij server. A successful socket write is not a confirmed file open.
	return c.send(receiver.ticket+payload+".")
}

func (c kittyClient) openLink(target string, hyperlink bool, permission string)error{
	u,err:=url.Parse(target)
	if err!=nil||u.Scheme==""||hasControl(target){return fmt.Errorf("invalid link destination")}
	if hyperlink && permission!="yes" && permission!="true" && permission!="1"{
		return fmt.Errorf("Kitty hyperlink policy %q requires native handling; link was not opened",permission)
	}
	if u.Scheme=="file"&&u.Host!=""&&u.Host!="localhost"{
		hostname,err:=os.Hostname()
		if err!=nil||!strings.EqualFold(u.Hostname(),hostname){return fmt.Errorf("remote file requires a Zellij receiver")}
	}
	// The action parser uses a Python string literal. Encode every rune to
	// preserve quotes, backslashes and whitespace exactly, without shell syntax.
	var encoded strings.Builder
	for _,r:=range target{fmt.Fprintf(&encoded,"\\U%08x",r)}
	_,err=at.DotfilesSocketRequest("action",map[string]any{"match_window":c.match,"action":"open_url "+encoded.String()},false)
	return err
}

// RunDirectHints is the only production entrypoint. Kitty supplies the ANSI
// snapshot and source id via launch; all routing and effects are owned by Go.
func RunDirectHints(mode string,id uint) (err error){
	if mode!="url"&&mode!="hyperlink"||id==0{return fmt.Errorf("expected url or hyperlink and a source window id")}
	c:=kittyClient{id:id,match:fmt.Sprintf("id:%d",id)}
	ansi,err:=io.ReadAll(os.Stdin);if err!=nil{return err}
	colors,err:=c.text("get-colors",map[string]any{"match":c.match});if err!=nil{return err}
	req,err:=paletteRequest(string(ansi),mode,os.Getenv("KITTY_PIPE_DATA"),colors);if err!=nil{return err}
	permission,err:=configuredPolicy(&req);if err!=nil{return err}
	f,err:=newStyledFrame(&req);if err!=nil{return err}
	var receiver *receiverState
	var original windowState
	if mode=="hyperlink"{
		original,err=c.window();if err!=nil{return err}
		if original.zellij() {
			probe:=req
			probe.Pane=&FilePane{Width:req.Cols,Height:req.Rows,Files:true}
			candidate,err:=newStyledFrame(&probe);if err!=nil{return err}
			marks:=make([]Mark,0,len(candidate.marks))
			for _,mark:=range candidate.marks{marks=append(marks,mark.Mark)}
			if hasFileMarks(marks){
				receiver,err=c.acquireReceiver(&req);if err!=nil{return err}
				if receiver!=nil{
					// On cancellation, render error or stale selection, release
					// only the original receiver, never the newly active pane.
					defer func(){if receiver!=nil{err=errors.Join(err,c.releaseReceiver(&req,original,receiver,nil))}}()
					req.Pane=&receiver.pane
					f,err=newStyledFrame(&req);if err!=nil{return err}
				}
			}
		}
	}
	chosen,err:=f.pick();if err!=nil{return err}
	if chosen==nil{return nil}
	if receiver!=nil{
		target,ok:=chosen.Groupdict["file"].(fileTarget)
		r:=receiver
		receiver=nil // never repeat an uncertain send
		if ok{return c.releaseReceiver(&req,original,r,&target)}
		if err=c.releaseReceiver(&req,original,r,nil);err!=nil{return err}
	}
	return c.openLink(chosen.Text,mode=="hyperlink",permission)
}

