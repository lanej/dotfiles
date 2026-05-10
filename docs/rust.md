# Rust Development

Disk space management for Rust projects:

## Configuration

- `sccache` enabled in `~/.cargo/config.toml` for shared compilation caching
- Optimized debug builds with reduced debug info (`debug = 1`)
- Split debug info on macOS to reduce binary sizes

## Cleanup Aliases

```sh
cargo-clean-all      # Remove ALL target/ directories
cargo-clean-debug    # Remove only debug builds, keep release
cargo-clean-old      # Clean builds older than 30 days
cargo-cache-clean    # Clean ~/.cargo cache
rust-disk            # Show top 20 largest target dirs
sccache-stats        # Show sccache hit/miss stats
```

## Maintenance

- Run `cargo-clean-debug` monthly
- Use `cargo-clean-old` for automatic cleanup
- Check `sccache-stats` to monitor cache effectiveness
