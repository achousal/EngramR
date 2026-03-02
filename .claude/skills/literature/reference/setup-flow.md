# Literature Setup Flow

Reference document for inline literature API key configuration. Read by `/literature`, `/onboard`, and other orchestrators when `check_literature_readiness()` returns `ready: False`.

---

## When to Use

- `/literature` triggers this when `result.ready` is False or `--setup` is in arguments
- `/onboard` triggers this inline during Turn 3 (after domain profile activation)
- Any orchestrator can read this to present the interactive setup loop

---

## Step 1: Present Setup Status

```
=== Literature Search Setup ===

Configured sources: {result.sources}
{for each source: source name -- status (ready / missing: {vars})}

Enrichment: {result.enrichers or "none configured"}
{for each enricher: enricher name -- status}
```

---

## Step 2: Profile-Specific Guidance

Read the active domain profile from `ops/config.yaml` (`domain_profile` field). If a profile is active, load its `env_vars` block and explain WHY each source matters for the user's domain.

| Domain Signal | Guidance |
|---|---|
| Biomedical / bioinformatics profile | "PubMed is the primary database for biomedical literature -- most of your searches will start here. NCBI_API_KEY raises your rate limit from 3 to 10 requests/second." |
| Any profile with `semantic_scholar` enabled | "Semantic Scholar provides citation graphs and influence scores -- useful for identifying high-impact papers and tracing research lineage." |
| Any profile with `openalex` enabled | "OpenAlex covers broad interdisciplinary literature and provides open-access metadata." |
| Enrichment configured | "CrossRef/Unpaywall enrichment adds citation counts and open-access PDF links to your search results." |

For sources/enrichers NOT in the active profile, skip guidance -- only explain what the user's configuration actually uses.

---

## Step 3: Show Export Commands

For each missing required variable, show a ready-to-paste export command:

```
Set these in another terminal (or add to ~/.zshenv_secrets for persistence):

  export NCBI_API_KEY="your-key-here"       # https://www.ncbi.nlm.nih.gov/account/settings/
  export NCBI_EMAIL="you@institution.edu"    # Your institutional email
  {only show vars that are actually missing}
```

**URL reference table (show for all missing vars):**

| Variable | Where to get it |
|---|---|
| `NCBI_API_KEY` | https://www.ncbi.nlm.nih.gov/account/settings/ |
| `NCBI_EMAIL` | Your institutional email |
| `OPENALEX_API_KEY` | https://openalex.org/ |
| `S2_API_KEY` | https://www.semanticscholar.org/product/api |
| `LITERATURE_ENRICHMENT_EMAIL` | Your institutional email |

Only include rows for variables that are actually missing.

---

## Step 4: Interactive Re-Check Loop

After presenting status and export commands:

```
Paste these exports in another terminal, then say "check".
Or "skip" to configure later via /literature --setup.
```

**On "check":** Re-run `check_literature_readiness('ops/config.yaml')` and compare against the previous result:

```
uv run --directory {vault_root}/_code python -c "
import json, sys; sys.path.insert(0, 'src')
from engram_r.search_interface import check_literature_readiness
print(json.dumps(check_literature_readiness('ops/config.yaml')))
"
```

- If new vars are now set: report which ones were detected ("NCBI_API_KEY: set, NCBI_EMAIL: set")
- If all required vars are now set: "Literature search: ready. All configured sources available."
- If some still missing: show remaining missing vars and repeat the loop

**On "skip":** Proceed without setup. The caller handles what happens next (e.g., `/onboard` moves to Generate Approval, `/literature` continues with available sources only).

---

## Step 5: Additional Setup Options

Offer these if relevant conditions are met:

- If `pubmed` is not in configured sources but `NCBI_EMAIL` is set in the environment:
  "PubMed is not in your configured sources, but NCBI_EMAIL is set. Add PubMed to your search sources?"

- If no enrichment is configured but `LITERATURE_ENRICHMENT_EMAIL` is set:
  "CrossRef/Unpaywall enrichment is not configured, but your email is set. Enable enrichment for citation counts and open-access links?"

---

## Caller Integration Notes

**`/literature`:** If `--setup` only (no query), stop after setup is complete. If `--setup` with query, proceed to search after setup.

**`/onboard`:** Store the final ready state. Use it in Phase 5 summary to decide whether to include the `/literature --setup` nudge in "What's Next".

**`/init`:** Does NOT use this file -- it only prints a one-line readiness nudge. No interactive loop.
