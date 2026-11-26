// SPDX-License-Identifier: GPL-3.0-only
package at

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"strconv"
	"time"

	"github.com/kovidgoyal/kitty/tools/utils"
)

// DotfilesSocketRequest uses the native remote-control serializer and reader.
// Only the inherited local socket is used; never discover or grant permissions.
func DotfilesSocketRequest(cmd string, payload any, noResponse bool) (json.RawMessage, error) {
	network, address, err := utils.ParseSocketAddress(os.Getenv("KITTY_LISTEN_ON"))
	if err != nil {
		return nil, fmt.Errorf("Kitty socket: %w", err)
	}
	if network != "unix" || address == "" {
		return nil, fmt.Errorf("styled hints require Kitty's existing local Unix socket")
	}
	conn, err := net.DialTimeout(network, address, 2*time.Second)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	if err = conn.SetWriteDeadline(time.Now().Add(2*time.Second)); err != nil {
		return nil, err
	}
	rc := &utils.RemoteControlCmd{Cmd: cmd, Version: ProtocolVersion, NoResponse: noResponse, Payload: payload}
	if id, err := strconv.ParseUint(os.Getenv("KITTY_WINDOW_ID"), 10, 32); err == nil {
		rc.KittyWindowId = uint(id)
	}
	data := rc_io_data{rc: rc, serializer: simple_serializer, timeout: 2*time.Second}
	raw, err := simple_socket_io(&conn, &data)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", cmd, err)
	}
	// send-text deliberately has no acknowledgement in Kitty's protocol.
	if noResponse {
		return nil, nil
	}
	var response struct {
		OK bool `json:"ok"`
		Data json.RawMessage `json:"data"`
		Error string `json:"error"`
	}
	if err = json.Unmarshal(raw, &response); err != nil {
		return nil, fmt.Errorf("%s response: %w", cmd, err)
	}
	if !response.OK {
		return nil, fmt.Errorf("%s: %s", cmd, response.Error)
	}
	return response.Data, nil
}
