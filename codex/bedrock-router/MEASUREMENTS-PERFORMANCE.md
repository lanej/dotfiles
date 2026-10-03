# Measurements contention benchmark

Measured on October 3, 2026, on an Apple M3 Pro running macOS arm64 and
Go 1.27.1.

The measurements mutex has a modest cost in a sustained small-chunk streaming
workload. With eight concurrent streams and ten health scrapes per second,
the current implementation was slower in all six paired runs, with about
6% median overhead. Other workloads were less consistent. These results support
keeping the current implementation for now; they do not establish a production
bottleneck or evaluate whether channels would improve performance.

## Method

The experiment used an isolated copy of the router and its real HTTP handler
through a loopback HTTP server. An in-memory upstream supplied valid SSE events
without generation delays. Each request transferred 64 KiB of output followed
by a completion event.

Two compiled benchmark binaries differed only in this streaming-loop section:

```go
r.stats.Lock()
r.stats.Bytes += uint64(written)
r.stats.Unlock()
```

The comparison binary omitted those three lines. Request counters, stream
gauges, logging, SSE inspection, routing, and the monitoring handler remained
enabled in both binaries. This comparison isolates per-chunk byte accounting;
it does not measure the cost of all instrumentation.

The benchmark varied:

- Chunk size: 256 bytes or 16 KiB, producing 256 or four byte-accounting
  updates per request, plus the completion event.
- Concurrency: one worker with `GOMAXPROCS=1`, or eight workers with
  `GOMAXPROCS=8`.
- Health scrapes: disabled or requested every 100 ms, approximately ten per
  second.

There were six paired rounds. Each benchmark ran for a target of one second,
and the order of the two binaries alternated between rounds. Response status,
byte count, and completed-request count were checked. Profiling ran separately
from the throughput comparisons.

## Throughput results

Throughput is in decimal MB/s, calculated from the median `ns/op` for each
binary. Overhead is the median of the six within-round ratios:
`(current ns/op / comparison ns/op - 1) × 100`.
Positive overhead means the current implementation was slower.
Parallel `ns/op` measures aggregate throughput, not individual request latency.

| Chunk size | Concurrent streams | Health scrapes/sec | Current MB/s | Without byte accounting MB/s | Paired median overhead | Current slower in |
|---|---:|---:|---:|---:|---:|---:|
| 256 B | 1 | 0 | 51.6 | 53.9 | +4.0% | 3/6 runs |
| 256 B | 8 | 0 | 115.6 | 120.7 | +4.2% | 4/6 runs |
| 256 B | 1 | 10 | 52.1 | 51.9 | +2.5% | 4/6 runs |
| 256 B | 8 | 10 | 116.4 | 122.6 | +6.0% | 6/6 runs |
| 16 KiB | 1 | 0 | 147.1 | 152.4 | +2.6% | 3/6 runs |
| 16 KiB | 8 | 0 | 475.2 | 520.6 | +15.6% | 4/6 runs |
| 16 KiB | 1 | 10 | 148.6 | 151.9 | −0.1% | 2/6 runs |
| 16 KiB | 8 | 10 | 499.3 | 495.5 | −3.7% | 1/6 runs |

The large-chunk concurrent results varied substantially. Without scrapes,
individual paired differences ranged from −36.0% to +94.2%; with scrapes,
they ranged from −15.3% to +40.9%. Those medians are not reliable estimates of
a stable penalty.

The small-chunk concurrent case without scrapes ranged from −5.1% to +12.9%.
With scrapes, all paired differences were positive, but ranged from +1.1% to
+38.1%. The approximately 6% result is a descriptive median, not a precise
production estimate or a formal significance claim.

## Mutex profile

A separate run used the current binary, eight concurrent streams, 256-byte
chunks, ten health scrapes per second, and a five-second benchmark target.
Mutex profiling sampled every contention event. The final measured benchmark
iteration completed 10,662 requests and 63 health scrapes; the profile also
includes benchmark calibration.

| Lock release site | Attributed aggregate waiter delay |
|---|---:|
| Per-chunk byte accounting in `ServeHTTP` | 154.91 ms |
| Monitoring handler's deferred measurements unlock | 84.75 ms |

The monitoring handler holds the measurements mutex while querying SQLite and
writing the response. The profile confirms that both this handler and byte
accounting contribute to contention.

These figures sum waiting across goroutines. They are neither elapsed request
delays nor CPU time, and should not be interpreted as percentages of wall time.
The complete mutex profile recorded 2.30 seconds of aggregate delay across all
locks, including runtime and HTTP internals.

## Limits and decision

This is an unpaced throughput stress test. It excludes Bedrock generation time,
upstream network latency, and production stream timing. The HTTP socket writes
and flushes remain real, but the results do not predict end-user latency.
Changing `GOMAXPROCS` along with concurrency also means the serial and concurrent
rows are different execution conditions, not a pure concurrency scaling test.
The temporary benchmark harness and raw profiles are not checked into the
repository.

Keep the mutex design for now. If production profiling later identifies it as
a bottleneck, first consider shortening the monitoring critical section or
reducing the frequency of byte-accounting updates. The experiment did not
compare channels, atomics, or batching. No production implementation was changed.
