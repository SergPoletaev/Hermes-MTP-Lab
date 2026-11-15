# Security policy

**Local machine access is required.** The plugin can restart the local Hermes-managed llama.cpp backend and temporarily update the selected Hermes model preset; explicit companion configuration also updates its local mapping. Do not expose Hermes' local API or the llama.cpp metrics endpoint to untrusted hosts.

- The plugin refuses to switch a runtime that is not confirmed to be owned by the current Hermes backend.
- The installer invokes the official Hermes CLI to enable this plugin; review the source before granting consent.
- The benchmark stores local performance metrics and a SHA-256 digest of output, but not generated text, chats, images or API keys.
- The source package must never contain `config.yaml`, `model-companions.json`, server credentials, logs or personal reports.
- Do not paste private diagnostic logs containing authentication headers, absolute personal paths or model prompts into public issues.

For suspected security issues, report privately through GitHub Security Advisories when available. Otherwise contact the repository owner through a private channel; do **not** publish exploit details in a public Issue.

Only this release's project files are covered by this repository's license; Hermes and GGUF model components retain their own terms.
