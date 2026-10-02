package main

import (
	"context"
	"flag"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"syscall"
	"time"
)

type idleConn struct {
	net.Conn
	idle time.Duration
}

func (c *idleConn) Read(p []byte) (int, error) {
	if err := c.Conn.SetReadDeadline(time.Now().Add(c.idle)); err != nil {
		return 0, err
	}
	return c.Conn.Read(p)
}

func (c *idleConn) Write(p []byte) (int, error) {
	// A reused socket may already be waiting for its next response. Reset
	// that read deadline when a fresh request starts, as well as on reads.
	deadline := time.Now().Add(c.idle)
	if err := c.Conn.SetReadDeadline(deadline); err != nil {
		return 0, err
	}
	if err := c.Conn.SetWriteDeadline(deadline); err != nil {
		return 0, err
	}
	return c.Conn.Write(p)
}

func main() {
	syscall.Umask(0077)
	executable, _ := os.Executable()
	configPath := flag.String("config", "", "Configuration file (default: config.json beside the binary, then embedded defaults)")
	checkConfig := flag.Bool("check-config", false, "Validate configuration and exit")
	port := flag.Int("port", 0, "Override the configured loopback port")
	state := flag.String("state-file", filepath.Join(filepath.Dir(executable), "sessions.sqlite3"), "Session affinity database")
	headerTimeout := flag.Duration("header-timeout", 0, "Override the configured maximum wait for upstream headers")
	streamIdle := flag.Duration("stream-idle-timeout", 0, "Override the configured maximum upstream silence")
	clientIdle := flag.Duration("client-write-timeout", 0, "Override the configured client write timeout")
	flag.Parse()
	log := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	path := *configPath
	if path == "" {
		adjacent := filepath.Join(filepath.Dir(executable), "config.json")
		if _, err := os.Stat(adjacent); !os.IsNotExist(err) {
			path = adjacent
		}
	}
	cfg, err := loadConfiguration(path)
	if err != nil {
		log.Error("invalid_config", "message", "Unable to load a valid configuration")
		os.Exit(1)
	}
	flag.Visit(func(f *flag.Flag) {
		switch f.Name {
		case "port":
			cfg.Port = *port
		case "header-timeout":
			cfg.HeaderTimeout = headerTimeout.String()
		case "stream-idle-timeout":
			cfg.StreamIdleTimeout = streamIdle.String()
		case "client-write-timeout":
			cfg.ClientWriteTimeout = clientIdle.String()
		}
	})
	if err := cfg.validate(); err != nil {
		log.Error("invalid_config", "message", err.Error())
		os.Exit(1)
	}
	if *checkConfig {
		log.Info("configuration_valid")
		return
	}
	*port = cfg.Port
	*headerTimeout, _ = time.ParseDuration(cfg.HeaderTimeout)
	*streamIdle, _ = time.ParseDuration(cfg.StreamIdleTimeout)
	*clientIdle, _ = time.ParseDuration(cfg.ClientWriteTimeout)
	// All requests share a transport, with no active-connection cap and no
	// whole-response deadline. Only silence, dial, and handshake are bounded.
	transport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: func(ctx context.Context, network, address string) (net.Conn, error) {
			conn, err := (&net.Dialer{Timeout: 30 * time.Second, KeepAlive: 30 * time.Second}).DialContext(ctx, network, address)
			if err != nil {
				return nil, err
			}
			return &idleConn{Conn: conn, idle: *streamIdle}, nil
		},
		ForceAttemptHTTP2: false, // Per-connection idle deadlines must not couple multiplexed streams.
		MaxIdleConns:      256, MaxIdleConnsPerHost: 128, IdleConnTimeout: 90 * time.Second,
		TLSHandshakeTimeout: 30 * time.Second, ResponseHeaderTimeout: *headerTimeout,
		ExpectContinueTimeout: time.Second, DisableCompression: true,
	}
	r, err := newRouter(*state, transport, log, cfg)
	if err != nil {
		log.Error("startup_failed", "component", "session_database")
		os.Exit(1)
	}
	defer r.routes.db.Close()
	defer transport.CloseIdleConnections()
	r.writeIdle = *clientIdle
	server := &http.Server{
		Addr: net.JoinHostPort("127.0.0.1", strconv.Itoa(*port)), Handler: r,
		ReadHeaderTimeout: 30 * time.Second, ReadTimeout: *streamIdle,
		IdleTimeout: 90 * time.Second, MaxHeaderBytes: 1 << 20,
	}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	drained := make(chan struct{})
	go func() {
		defer close(drained)
		<-ctx.Done()
		log.Info("shutdown_started")
		drain, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := server.Shutdown(drain); err != nil {
			log.Warn("shutdown_drain_timeout")
			_ = server.Close()
		}
	}()
	log.Info("listening", "host", "127.0.0.1", "port", *port, "header_timeout", headerTimeout.String(),
		"stream_idle_timeout", streamIdle.String(), "client_write_timeout", clientIdle.String())
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Error("listen_failed")
		os.Exit(1)
	}
	if ctx.Err() != nil {
		<-drained
	}
}
