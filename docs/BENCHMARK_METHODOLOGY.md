# Benchmark methodology

## Protocol

The benchmark submits the same eligible tasks to one **user-selected MTP-compatible, Hermes-managed local GGUF model** twice: **MTP OFF**, then **MTP ON**. Models without a vision projector use **four text tasks** (8 requests for one repeat or 24 for three repeats); models with a valid mmproj use **six tasks** (12 or 36 requests respectively). A short warm-up request occurs in each phase and is excluded from measured totals. The bundled original reference photograph (`data/benchmark_scene.jpg`) is used for both vision tasks when supported.

The two phases use identical task inputs, fixed random seed (12345), `temperature=0`, `top_p=1`, output cap (260 tokens), and a temporarily pinned context window equal to the **lesser of the selected preset context and 32768**. The original selected preset bytes (including MTP and context settings) are restored after the run. No architecture, quantization, or particular model name is hardcoded; MTP support must be established separately for each model and companion combination.

## Measurements

For each request the local child server provides cumulative Prometheus-style `/metrics` counters before and after generation. The plugin calculates token and time deltas, plus count of drafted and accepted speculative tokens, and stores them in JSON and CSV. **Decode tokens/s** is reported as `generated_token_delta / decode_seconds_delta` when both are valid. Group speedups compare median OFF and ON throughput values; aggregate speedups should account for total tokens and decode duration rather than averaging speedup ratios.

- `draft_accepted / draft_generated` is a token-acceptance fraction, **not** an accuracy score.
- UI rendering latency, network-to-localhost overhead, first-token latency and complete user-chat orchestration are **not** measured.
- The generated reply is truncated at a maximum of 260 tokens; no claim is made about long-context or long-generation performance.
- Reports store output digests, not raw responses; this avoids leaking response contents but also limits later output-quality checks.

## Interpretation and caveats

- OFF/ON must be checked for context, KV types, Flash Attention, batching and projector configuration. If any effective parameter is unconfirmed or different, improvements are observational rather than caused exclusively by MTP.
- `mmap`/disk caching, GPU offload, dynamic context planning, prompt caching and background system load may affect results.
- In particular, six tasks run repeatedly against the same image, so repeated image prompts may benefit from the backend cache.
- Cold-load time of GGUF weights is **not** the metric of these decode tests.
- The tasks are **types of inference workloads**, not Hermes user-chat modes Auto/Native/Text. There is no separate Vision chat mode in the measured Hermes UI.

## Test coverage

The GitHub Actions pipeline runs Python, JavaScript and packaging checks. The benchmark itself reports acceptance and OFF/ON speed on the active local runtime.

## Any compatible local model (v0.3.3)

The selected model is taken from Hermes native managed presets, not from any hardcoded GGUF name or quantization. For models with no projector only the four text tasks run (8 quick / 24 full measurements). With a valid mmproj all six tasks are eligible (12 quick / 36 full). MTP requires either an explicitly linked compatible separate head or verified embedded MTP metadata/preset. A successful MTP launch and accepted draft tokens are required for valid ON results. OFF/ON use matching launch context, at most the smaller of the existing context and 32768. Original preset bytes are restored.

## Companion discovery and MTP evidence (v0.3.3)

The UI suggests mmproj and MTP-head GGUFs next to the exact user-selected Hermes model, inspecting the GGUF file signature and ranking filenames. The user must confirm and save the chosen companion. Another directory for either GGUF can be selected with the Hermes Desktop folder-picker; no filesystem-wide scan or inferred binding is performed. Vision tests are enabled only for a linked readable projector. Filename similarity alone cannot guarantee architectural compatibility.

MTP is shown as **verified embedded** only if the main GGUF's `nextn_predict_layers` metadata is detected by the Hermes metadata reader or GGUF header inspection. An already configured native `draft-mtp` preset without that metadata is displayed as configured but unverified. A linked external head has its own state. Compatibility and performance still require a real OFF/ON test.
