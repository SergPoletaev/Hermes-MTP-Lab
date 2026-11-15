# Hermes MTP Lab v0.3.3 — result fields

Hermes MTP Lab performs an A/B test on the **selected compatible local GGUF model**. Its output folder contains:

- `summary.md` — model ID, selected MTP mode, comparable OFF/ON conditions, aggregate measurements and restoration state.
- `results.csv` — one row per measured task and phase, with decoding rate and speculative-token counters where available.
- `results.json` — structured per-request metrics and aggregate results suitable for scripts.

## Core metrics

| Field | Meaning |
|---|---|
| OFF tok/s | Observed decoding throughput with MTP disabled |
| ON tok/s | Observed decoding throughput with MTP enabled |
| Drafted tokens | Candidate tokens proposed by MTP during the ON phase |
| Accepted tokens | Proposed tokens accepted by speculative decoding |
| Speedup | Ratio of median ON and OFF decoding throughput for a comparable workload |
| Comparable | Whether the measured runtime parameters could be checked as equal in both phases |
| Restored | Whether the original Hermes preset was restored after the run |

Four text workloads are measured for a text-only GGUF. With a linked, readable `mmproj` the benchmark also runs two image workloads using the bundled reference image.

Use the generated reports for actual values; this documentation contains no fabricated performance measurements or model-specific assertions.
