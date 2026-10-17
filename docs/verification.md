# Software verification

Checked locally on 17 October 2026. These checks cover application behavior, not detector accuracy.

| Check | Observed result |
| --- | --- |
| Backend regression suite | 44 passed in 33.74 seconds. Includes keyed/scoped access, persistent human review, immutable model results, malformed inputs, bounded evidence, worker fencing and process deadlines. One dependency deprecation warning from the test client. |
| Frontend contract tests | 5 passed. Missing/contradictory completed results, foreign jobs, invalid evidence timestamps and incomplete review receipts fail closed. Unicode review limits match the server's codepoint count. |
| Production frontend build | TypeScript and Vite build passed. Assets and fonts are bundled locally. |
| Desktop illustrated preview | Large verdict, event types, fractional-second evidence times, separate human assessment and notes rendered. Unsaved notes survived app navigation. Saving a negative human assessment left the positive synthetic model result unchanged. |
| Evidence viewer | Full-size dialog opened; zoom, arrow-key frame navigation, Escape and focus return worked. |
| Connection and playback recovery | Static review confirmed that a temporary retrieval failure retains the job and token, and retry performs a bounded status GET after the processing deadline. Stale playback rejections cannot update a replacement workspace; normal playback cancellation is ignored. |
| Russian and mobile preview | Russian controls and synthetic labels rendered at 390×844. Page width stayed inside the viewport; evidence uses a horizontal strip. Human-decision form saved in the preview. Temporary viewport override was reset. |
| Source-control inspection | No tracked MOV/XLSX/ONNX/NPZ/GGUF/safetensors/database/environment-secret files. Patch whitespace check passed. |

The preview and its screenshots contain only a purpose-built illustration. Its signals are explicitly synthetic. No restricted source footage was viewed through the browser during these checks. The real browser upload path was not exercised in this verification pass; it remains separate from unit/API tests and local model inference.

Historical real-recording service measurements in `service_verification.json` describe the failed original baseline. They do not establish new-model accuracy or latency. New detector qualification belongs in its model card and measured evaluation record; see `model_studies.md` and `qualification.md`.
