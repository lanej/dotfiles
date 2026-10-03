package main

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"errors"
	"io"
	"strings"
	"sync"
	"time"
)

// Retain only a session hash and expiry, never the failed query or response.
// Hints are consumed by the next request; Codex owns retries and turn history.
type webRecovery struct {
	sync.Mutex
	pending map[string]time.Time
}

func (r *webRecovery) record(session string) {
	r.Lock()
	defer r.Unlock()

	now := time.Now()
	for key, expiry := range r.pending {
		if now.After(expiry) {
			delete(r.pending, key)
		}
	}

	if r.pending == nil {
		r.pending = make(map[string]time.Time)
	}

	// Bound memory even when clients abandon failed sessions.
	if len(r.pending) >= 1024 {
		var oldest string
		for key, expiry := range r.pending {
			if oldest == "" || expiry.Before(r.pending[oldest]) {
				oldest = key
			}
		}

		delete(r.pending, oldest)
	}

	r.pending[session] = now.Add(15 * time.Minute)
}

func (r *webRecovery) take(session string) bool {
	r.Lock()
	defer r.Unlock()

	expiry, ok := r.pending[session]
	delete(r.pending, session)
	return ok && time.Now().Before(expiry)
}

const webRecoveryHint = "The previous response failed during built-in web browsing with: " +
	"Access denied: web search is not authorized for this identity. " +
	"Web search remains enabled and may work for other calls. Do not repeat the same failing " +
	"search or URL-open call unchanged. Use the bedrock_browse MCP tool if available, with a " +
	"self-contained research task; it uses a separate browsing model and region. Continue the task using completed work; try a different " +
	"search approach or another available tool when useful. If access remains denied, explain " +
	"the limitation and continue what you can without repeatedly attempting the denied call."

func addWebRecoveryHint(body []byte, encoding string) ([]byte, error) {
	compressed := strings.EqualFold(encoding, "gzip")
	if compressed {
		reader, err := gzip.NewReader(bytes.NewReader(body))
		if err != nil {
			return nil, err
		}

		body, err = io.ReadAll(io.LimitReader(reader, maxBodyBytes+1))
		reader.Close()

		if err != nil {
			return nil, err
		}
	}

	var object map[string]json.RawMessage
	if err := json.Unmarshal(body, &object); err != nil {
		return nil, err
	}

	var input []json.RawMessage

	if raw := object["input"]; len(raw) > 0 && string(raw) != "null" {
		var text string
		if json.Unmarshal(raw, &text) == nil {
			item, _ := json.Marshal(map[string]string{"role": "user", "content": text})
			input = append(input, item)
		} else if err := json.Unmarshal(raw, &input); err != nil {
			return nil, err
		}
	}

	hint, _ := json.Marshal(map[string]string{"role": "developer", "content": webRecoveryHint})
	input = append(input, hint)
	object["input"], _ = json.Marshal(input)

	updated, err := json.Marshal(object)
	if err != nil {
		return nil, err
	}

	if len(updated) > maxBodyBytes {
		return nil, errors.New("recovery hint exceeds request limit")
	}

	if compressed {
		var output bytes.Buffer

		writer := gzip.NewWriter(&output)
		if _, err := writer.Write(updated); err != nil {
			return nil, err
		}

		if err := writer.Close(); err != nil {
			return nil, err
		}

		updated = output.Bytes()
	}

	return updated, nil
}
