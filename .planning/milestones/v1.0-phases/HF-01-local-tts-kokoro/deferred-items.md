# Deferred Items — HF-01

## Out-of-scope pre-existing test failures

### tests/contracts/test_phase3_contracts.py::TestCapabilityMetadata::test_registry_catalog_views
- **Discovered during:** plan 01-02 regression run.
- **Cause:** the test hardcodes the TTS provider set as `{"elevenlabs", "google_tts", "openai", "piper"}`. The registry now also discovers `kokoro` (added in plan 01-01) and `doubao` (pre-existing), so the exact-equality assertion fails.
- **Confirmed pre-existing:** fails with plan 01-02's changes stashed; not caused by the selector logic edit (selector changes cannot add providers to the registry catalog).
- **Why not fixed here:** out of the plan's declared file scope (tts_selector.py, test_tts_selector_downgrade.py, PROJECT_CONTEXT.md); the stale set belongs to the kokoro/doubao provider additions. Editing this contract test risks colliding with parallel plan 01-03.
- **Fix owed:** update the expected set to include `kokoro` and `doubao` (a phase-cleanup or 01-03 concern).
