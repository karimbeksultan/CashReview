# Normative mapping

Cash Review currently attaches **regulatory context**, not a verified finding that a specific rule was breached. This distinction is part of the result contract and must remain visible in the interface and explanations.

## Registry and current mapping

`backend/rules/registry.json` is a versioned offline registry. Its root contains `version` and `rules`. Each rule has `id`, `title`, `issuer`, `url`, `section`, `verified`, `enabled_for_legal_claim`, `summary`, `applicability`, `visual_evidence`, and `limitations`. The last two fields are arrays of strings; the two flags are booleans; remaining fields are strings.

| Detector output | Registry ID | Verified scope | Legal claim enabled |
| --- | --- | --- | --- |
| `visual_review_signal` | `CR-001` | Official source and general cash-operation context | **No** |

`verified: true` means the cited official source supports the contextual proposition described in the entry. It does not certify a detected event, legal applicability, the current consolidated text of an entire act, or compliance with ForteBank policy. The independent `enabled_for_legal_claim: false` prevents a contextual citation from being presented as proof of a breach.

The initial detector learns from video-level binary labels. Those labels do not identify event types, actors' authority, a breached rule, or complete event boundaries. A highlighted fragment is therefore a candidate for review; `visual_review_signal` is not a semantic violation category. A schema-compatible result alone does not meet the case's substantive classification and rule-grounding goals.

## Sources checked on 17 October 2026

The [National Bank's official message of 20 December 2024](https://nationalbank.kz/ru/news/informacionnye-soobshcheniya/17232), under its heading about cash operations with foreign currency, identifies receiving cash from and issuing cash to clients as banking cash operations and cites Board Resolution No. 231 of 29 November 2019. This supports the domain context in `CR-001`; it supplies no verified video-triggered breach predicate for this build.

The act's official reference is [Adilet record V1900019680](https://adilet.zan.kz/rus/docs/V1900019680), with the [official history record](https://adilet.zan.kz/rus/docs/V1900019680/history). Adilet's main text required JavaScript during this research, and its legacy page did not load reliably. The full current consolidated clauses and their effective dates were not independently verified. The registry intentionally names no invented clause. The National Bank message is an official explanatory source, not a substitute for checking operative legal text.

No internal ForteBank cashier policy was supplied. No other bank's policy is represented as binding on ForteBank. No legal rule was inferred from a dataset filename, timestamp or binary label.

## Gate for enabling a semantic rule

Before setting `enabled_for_legal_claim` to `true`, retain all of the following in a reviewed registry revision:

1. An official Kazakhstan act, actual provision, relevant revision and effective dates; local reviewed text and source retrieval date.
2. A narrow statement of the obligation and why it applies to the visible setting, rather than merely to a bank in general.
3. A complete observable event predicate, temporal opportunity window where relevant, visibility limits and counterexamples.
4. Reviewed event-type annotations with uncertainty, separate from the original labels; normal clips reviewed as counterexamples.
5. Evidence that the detector identifies that predicate on held-out content groups, including false alarms and misses.
6. A plain explanation linking visible facts to that obligation, with uncertainty and human review preserved.

Keep unsupported entries disabled. A visible door, person, cash-like object or pause cannot on its own establish unauthorized access, unsecured custody, a required recount omission or an accounting error. These are candidate research topics, not capabilities claimed by this version.

## Runtime boundary

The registry is loaded locally; analysis must not browse for laws or send video content to a remote model. Evidence frames are private job outputs. Public repository documentation contains source links and implementation limits, never dataset frames or jury media.
