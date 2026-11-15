# Contributing

Thanks for helping improve Hermes MTP Lab. Please open an Issue describing the observed behavior before submitting a substantial change.

1. Keep the working model and llama.cpp setup unchanged unless a change is explicitly part of the proposal.
2. Extend tests for any changes to MTP switching, runtime ownership, recovery or benchmark metric validation.
3. Use `python -m unittest discover -s hermes-mtp-lab/tests -p "test_*.py" -v`, `node hermes-mtp-lab/tests/test_desktop_registration.cjs`, and `python tools/verify_repo.py`.
4. Use the GitHub pull-request workflow. The CI suite is mock-based and does not prove live Windows behavior.
5. Never attach actual `model-companions.json`, `config.yaml`, tokens, personally identifying filesystem paths, private conversations or GGUF weights.

When reporting a failure, include the plugin version, Hermes version, Python version, llama.cpp binary build, sanitized error text, and whether the model is managed by this backend. Mention if MTP was restored after the test.
