# Example three-repeat benchmark (2026-11-15)

This is a **sanitized result summary**, measured in the earlier **v0.2.1** plugin on a local Windows Hermes Desktop system with a compatible Gemma 4 12B model and `mtp-gemma-4-12B-it.gguf`. No personal paths, process identifiers, API keys, prompts, responses, logs, or attachments are included here.

| Workload group | OFF median tok/s | ON median tok/s | Observed speedup | Draft accepted / proposed |
|---|---:|---:|---:|---:|
| Text | 30.49 | 69.75 | 2.288× | 990 / 1,679 |
| Code and data | 30.03 | 83.40 | 2.777× | 1,081 / 1,409 |
| Image description | 29.60 | 71.11 | 2.402× | 523 / 758 |
| Visual details | 28.77 | 79.36 | 2.758× | 543 / 695 |

All **36/36** individual requests completed successfully (18 OFF, 18 ON). Aggregate accepted draft tokens: **3,137 / 4,541 = 69.1%**. For 4,680 total output tokens per phase, measured decode times were approximately **157.16 seconds OFF** and **61.74 seconds ON**, corresponding to an overall **2.55× observed speedup in decoding time**.

**Important limitations:** The benchmark reported `Parameters identical across OFF/ON: False`. Both phases used context 32768, KV `q8_0/q8_0`, Flash Attention and mmproj. However `batch-size` and `ubatch-size` were explicit as 2048 in OFF but **not reported in ON**, so effective values were not verified. Thus **the gain cannot be attributed exclusively to MTP**. The run also used a short 260-token output cap, and repeated image inputs may have benefited from prompt caching. These data do not measure the Auto / Native / Text modes of Hermes Desktop or the UI's end-to-end responsiveness.

v0.2.3 adds RU/EN localization to the improved progress UI. This historical v0.2.1 result does not validate v0.2.3 in a live Desktop installation.
