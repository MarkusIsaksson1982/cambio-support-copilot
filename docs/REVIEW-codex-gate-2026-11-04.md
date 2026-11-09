# Gate review findings

- Span proposals were accepted whenever they appeared as any substring. A model could therefore propose `Tova` from `xTova`, `Tova2`, or `Tova_name` and get a partial token masked. The gate now requires token boundaries around a match; matching remains exact and case sensitive.
- Citation checking attempted set membership before validating the citation type, so list/object citations raised `TypeError`. Non-string or empty citations now fail closed, and an empty or malformed KB ID collection cannot ground a response.
- Approval returned the stored reply draft without a final masking pass. A result assembled outside the normal pipeline could send a recognizable identifier in that draft. The approval path now masks the reply before returning it.
- Regression tests cover whitespace/case mismatches and a Cyrillic lookalike as exact-match rejection cases. These were already rejected by exact substring matching; tests preserve that behavior.

Verification: `python3 -m pytest -q` — 104 passed, 1 skipped, 11 xfailed.
