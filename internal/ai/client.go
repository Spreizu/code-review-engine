package ai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

// Client calls an OpenAI-compatible POST {base_url}/chat/completions endpoint.
type Client struct {
	BaseURL     string
	Model       string
	APIKey      string // resolved from the env var named in config; never logged
	Temperature float64
	JSONMode    bool
	Headers     map[string]string
	HTTP        *http.Client
}

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatRequest struct {
	Model          string            `json:"model"`
	Messages       []chatMessage     `json:"messages"`
	Temperature    float64           `json:"temperature"`
	ResponseFormat map[string]string `json:"response_format,omitempty"`
}

type chatResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Usage map[string]any `json:"usage"`
}

func (c *Client) endpoint() string {
	u := strings.TrimRight(c.BaseURL, "/")
	if strings.HasSuffix(u, "/chat/completions") {
		return u
	}
	return u + "/chat/completions"
}

var envRef = regexp.MustCompile(`\$\{([A-Za-z_][A-Za-z0-9_]*)\}`)

// Confirm sends one batch and returns verdicts keyed by item id.
func (c *Client) Confirm(ctx context.Context, b *Batch) (map[string]Verdict, map[string]any, error) {
	payload := *b
	payload.Instructions = "" // sent once as the system message
	user, err := json.Marshal(payload)
	if err != nil {
		return nil, nil, err
	}
	req := chatRequest{Model: c.Model, Temperature: c.Temperature, Messages: []chatMessage{{"system", SystemPrompt}, {"user", string(user)}}}
	if c.JSONMode {
		req.ResponseFormat = map[string]string{"type": "json_object"}
	}
	var last error
	for attempt := range 4 {
		if attempt > 0 {
			select {
			case <-ctx.Done():
				return nil, nil, ctx.Err()
			case <-time.After(time.Duration(1<<attempt) * time.Second):
			}
		}
		content, usage, status, err := c.post(ctx, req)
		if err == nil {
			v, perr := parseVerdicts(content, b)
			if perr == nil {
				return v, usage, nil
			}
			last = perr // malformed answer: retry once more
			continue
		}
		last = err
		if status == http.StatusBadRequest && req.ResponseFormat != nil {
			req.ResponseFormat = nil // some compatible servers reject response_format
			continue
		}
		if status != 0 && status != http.StatusTooManyRequests && status < 500 {
			break
		}
	}
	return nil, nil, last
}

func (c *Client) post(ctx context.Context, cr chatRequest) (string, map[string]any, int, error) {
	body, _ := json.Marshal(cr)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.endpoint(), bytes.NewReader(body))
	if err != nil {
		return "", nil, 0, err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
	}
	for k, v := range c.Headers {
		req.Header.Set(k, envRef.ReplaceAllStringFunc(v, func(m string) string { return os.Getenv(envRef.FindStringSubmatch(m)[1]) }))
	}
	hc := c.HTTP
	if hc == nil {
		hc = &http.Client{Timeout: 120 * time.Second}
	}
	resp, err := hc.Do(req)
	if err != nil {
		return "", nil, 0, err
	}
	defer resp.Body.Close()
	rb, err := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if err != nil {
		return "", nil, resp.StatusCode, fmt.Errorf("chat/completions: reading response: %w", err)
	}
	if resp.StatusCode/100 != 2 {
		msg := strings.TrimSpace(string(rb))
		if len(msg) > 300 {
			msg = msg[:300]
		}
		return "", nil, resp.StatusCode, fmt.Errorf("chat/completions: HTTP %d: %s", resp.StatusCode, msg)
	}
	var out chatResponse
	if err := json.Unmarshal(rb, &out); err != nil {
		return "", nil, resp.StatusCode, fmt.Errorf("chat/completions: bad JSON: %w", err)
	}
	if len(out.Choices) == 0 {
		return "", nil, resp.StatusCode, fmt.Errorf("chat/completions: no choices")
	}
	return out.Choices[0].Message.Content, out.Usage, resp.StatusCode, nil
}

var fence = regexp.MustCompile("(?s)^\\s*```(?:json)?\\s*(.*?)\\s*```\\s*$")

// parseVerdicts accepts {"results":[...]}, a bare array, or JSONL of verdicts.
func parseVerdicts(content string, b *Batch) (map[string]Verdict, error) {
	if m := fence.FindStringSubmatch(content); m != nil {
		content = m[1]
	}
	vs, err := ParseVerdicts([]byte(content))
	if err != nil {
		return nil, err
	}
	ids := map[string]bool{}
	for _, it := range b.Items {
		ids[it.ID] = true
	}
	out := map[string]Verdict{}
	for _, v := range vs {
		if !ids[v.ID] {
			continue
		}
		if !validVerdict(v.Verdict) {
			v.Verdict, v.Confidence = "uncertain", "low"
		}
		if len(v.Rationale) > 1200 {
			v.Rationale = v.Rationale[:1200]
		}
		out[v.ID] = v
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("response contained no verdicts for this batch")
	}
	return out, nil
}

// ParseVerdicts decodes any accepted response shape.
func ParseVerdicts(b []byte) ([]Verdict, error) {
	b = bytes.TrimSpace(b)
	var r Response
	if json.Unmarshal(b, &r) == nil && len(r.Results) > 0 {
		return r.Results, nil
	}
	var arr []Verdict
	if json.Unmarshal(b, &arr) == nil && len(arr) > 0 {
		return arr, nil
	}
	var out []Verdict
	for _, line := range bytes.Split(b, []byte("\n")) {
		line = bytes.TrimSpace(line)
		if len(line) == 0 {
			continue
		}
		var rr Response
		if json.Unmarshal(line, &rr) == nil && len(rr.Results) > 0 {
			out = append(out, rr.Results...)
			continue
		}
		var v Verdict
		if err := json.Unmarshal(line, &v); err != nil || v.ID == "" {
			return nil, fmt.Errorf("unrecognised verdict line: %.120s", line)
		}
		out = append(out, v)
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("no verdicts found")
	}
	return out, nil
}

// RunStats summarises an API run.
type RunStats struct {
	Batches, Sent, Resolved, Failed int
	Errors                          []string
	PromptTokens, CompletionTokens  int
}

// Run confirms items through the API with bounded concurrency (no budget cap) and caches results.
func Run(ctx context.Context, c *Client, batches []*Batch, cache Cache, concurrency int) RunStats {
	if concurrency <= 0 {
		concurrency = 4
	}
	var mu sync.Mutex
	st := RunStats{Batches: len(batches)}
	sem := make(chan struct{}, concurrency)
	var wg sync.WaitGroup
	for _, b := range batches {
		wg.Add(1)
		sem <- struct{}{}
		go func(b *Batch) {
			defer wg.Done()
			defer func() { <-sem }()
			vs, usage, err := c.Confirm(ctx, b)
			mu.Lock()
			defer mu.Unlock()
			st.Sent += len(b.Items)
			if err != nil {
				st.Failed += len(b.Items)
				st.Errors = append(st.Errors, fmt.Sprintf("batch %s: %v", b.BatchID, err))
				return
			}
			if usage != nil {
				st.PromptTokens += toInt(usage["prompt_tokens"])
				st.CompletionTokens += toInt(usage["completion_tokens"])
			}
			for _, it := range b.Items {
				v, ok := vs[it.ID]
				if !ok {
					st.Failed++
					continue
				}
				e := CacheEntry{Verdict: v, Via: "api", Model: c.Model, RuleID: it.Rule, Created: time.Now().UTC()}
				it.Apply(e)
				_ = cache.Put(it.key, e)
				st.Resolved++
			}
		}(b)
	}
	wg.Wait()
	return st
}

func toInt(v any) int {
	if f, ok := v.(float64); ok {
		return int(f)
	}
	return 0
}
