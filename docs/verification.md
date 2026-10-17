# Software verification

Checked locally on 17 October 2026. These checks cover application behavior, not detector accuracy.

| Check | Observed result |
| --- | --- |
| Backend regression suite | 44 passed in 33.74 seconds. Includes keyed/scoped access, persistent human review, immutable model results, malformed inputs, bounded evidence, worker fencing and process deadlines. One dependency deprecation warning from the test client. |
| Frontend contract tests | 8 passed. Missing/contradictory completed results, foreign jobs, invalid evidence timestamps and incomplete review receipts fail closed. Review-note input truncation, counter and receipt validation count Unicode codepoints, including mixed emoji/ASCII at the 4,000-point boundary. Job quality notices use the recorded model status instead of inheriting a replacement runtime's status. |
| Production frontend build | TypeScript and Vite build passed after the final notice text edit; Vite completed in 23.05 seconds. Assets and fonts are bundled locally. |
| Experimental training workflow | 68 media-free contract assertions passed, plus local comparison of nine numerical functions with the executed experiment and compilation of five modules. Checks cover source-unit timestamps, grouped splits, immutable run contracts, cache integrity and uncertainty-safe thresholds; no model or source footage was loaded. |
| Desktop illustrated preview | Large verdict, event types, fractional-second evidence times, separate human assessment and notes rendered. Unsaved notes survived app navigation. Saving a negative human assessment left the positive synthetic model result unchanged. |
| Evidence viewer | Full-size dialog opened; zoom, arrow-key frame navigation, Escape and focus return worked. |
| Connection and playback recovery | Static review confirmed that a temporary retrieval failure retains the job and token, and retry performs a bounded status GET after the processing deadline. Stale playback rejections cannot update a replacement workspace; normal playback cancellation is ignored. |
| Model quality disclosure | The upload/results flow displays an English or Russian notice for `failed_baseline`, including all four normal test clips being flagged and the need for an independent human decision. Both languages were observed in the browser. The System page uses current runtime status; historical job metadata remains authoritative for its own result. See the [desktop notice](status-preview.jpg) and [mobile notice](status-mobile-preview.jpg). |
| Unicode editor browser check | In the built-in illustrated preview, pasting 4,001 emoji plus trailing ASCII retained 4,000 complete emoji (8,000 UTF-16 units), displayed the correct count and saved the human assessment. The synthetic positive model result remained unchanged. This was tab-local preview behavior, with no file upload or server review write. |
| Russian and mobile preview | Russian controls and synthetic labels rendered at 390×844. Page width stayed inside the viewport; evidence uses a horizontal strip. Human-decision form saved in the preview. Temporary viewport override was reset. |
| Source-control inspection | No tracked MOV/XLSX/ONNX/NPZ/GGUF/safetensors/database/environment-secret files. Patch whitespace check passed. |

The preview and its screenshots contain only a purpose-built illustration. Its signals are explicitly synthetic. No restricted source footage was viewed through the browser during these checks. The real browser upload path was not exercised in this verification pass; it remains separate from unit/API tests and local model inference.

Historical real-recording service measurements in `service_verification.json` describe the failed original baseline. They do not establish new-model accuracy or latency. New detector qualification belongs in its model card and measured evaluation record; see `model_studies.md` and `qualification.md`.
