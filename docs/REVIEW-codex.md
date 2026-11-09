# Pluggable pipeline review

Scope: `pipeline.py`, plugin/adapter/approval/audit APIs, the support ticket plugin,
extension guidance, and the JSON contracts. Ranked by severity.

1. **Critical — extension exceptions escaped the safety spine.** `rules`,
   `model_task`, `build_output`, `handoff_reasons`, and `adapter.complete` could
   raise directly. Requests then had no handoff envelope or final decision audit.
   A caller could retry or surface raw exception text. Catch at the pipeline
   boundary, emit a generic reason, and never include exception messages.
2. **Critical — model prompt was trusted after plugin construction.** The core
   passed `task.prompt` directly to adapters. A plugin could accidentally embed
   an unmasked personnummer despite receiving masked text. Re-run masking on the
   complete prompt and refuse the call if it changes.
3. **High — only plugin output was validated.** The chained-service envelope
   contract was not checked at the final boundary. Plugin metadata, malformed
   hook results, or future pipeline edits could produce an invalid envelope.
   Validate every returned result against `handoff_envelope.v1.schema.json`.
4. **High — model output was sanitized only after schema validation.** PII in
   model fields could reach plugin logic before masking. Mask parsed output before
   validation/use, and sanitize final output again before returning it.
5. **High — audit is a mutable in-memory list or append-only file, but write
   failures are not transactional.** A failed disk write can interrupt a request;
   the caller must treat audit storage availability as an operational dependency.
   The pipeline cannot honestly claim an audited result if the audit sink itself
   fails; production needs durable failure handling and monitoring.
6. **Medium — plugin protocol is structurally checked only at registration.**
   It has no capability/version negotiation, hook timeout, or runtime validation
   of `RuleResult`/`ModelTask`. A plugin can return malformed values or block.
   Validate hook inputs/outputs and isolate extensions where untrusted plugins
   are allowed.
7. **Medium — adapter failures collapse into abstention in built-in adapters.**
   `LocalAdapter` and `OpenCodeAdapter` swallow exceptions and return `None`,
   making outage indistinguishable from a deliberate model abstention. Preserve
   a safe internal error status without exposing provider details.
8. **Medium — the nested plugin schema is a small JSON Schema subset.** The
   validator ignores formats, references, and several standard keywords. The
   contract's current envelope is intentionally shallow, but external consumers
   should use a standards-compliant validator for richer contracts.
9. **Low — the plugin API permits drafts that are empty or not grounded.** The
   support ticket plugin relies on its own handoff hook for `no_grounded_draft`;
   omission or failure in a new plugin could leave an empty draft awaiting review.
   Consider core-owned checks for required user-facing artifacts per request type.

The implementation addresses items 1–4 for the shared pipeline. Audit sink
failure, process isolation/timeouts, richer schema support, and domain-specific
draft requirements remain architectural work.
