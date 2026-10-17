# Implementation decisions

## Local runtime

The working environment is Windows with a CPU and no available GPU or Docker command. SQLite provides a durable local queue and review records, with private files for media. The worker uses claim tokens, leases, hard deadlines and isolated native decoding. This replaces the suggested self-hosted Supabase/PostgreSQL stack while preserving the external API. No hosted database is configured or represented as deployed.

The backend serves the built frontend and locally bundled fonts. Preparing dependencies or public model weights may use the network; inference has no remote AI fallback or model download. Publishing code to the user's GitHub repository does not publish private source videos or runtime artifacts.

## Results and human review

The integration contract has two completed verdicts. Technical failures remain failures. The interface explains coverage limitations alongside results, keeps human decisions and notes separate, and never presents a missing or invalid result as a successful negative.

The old reference-label comparison has been removed. Source labels are used only in private training and evaluation. Human review feedback does not automatically become ground truth or update model weights.

## Evaluation and semantics

There are 42 source recordings but only 40 unique content groups. Exact duplicates stay together. One duplicate positive recording has two different supplied timestamps; both are preserved as ambiguous annotations. Binary labels and isolated time points do not establish event types or complete intervals.

The original eight-clip test was inspected during the first baseline evaluation. Later work may describe evaluation on those clips only as exploratory. It cannot provide a new untouched test merely by changing a model, threshold or random seed. Development validation is also small and increasingly reused; model selection results need an independent future check.

Models are compared using per-class errors, specificity and recall. All-positive and all-negative predictors are rejected as useful detectors. A larger backbone is promoted only when measured development behavior and hardware limits support it. Human-reviewed intervals/types and new-camera data are needed before broad semantic claims.

## Rules and presentation

The verified official source provides background context. It does not establish that a model-selected moment breaches an applicable rule. Legal-claim mappings remain disabled until a supported observable action, applicable obligation and counterexamples are reviewed.

User instructions remove event-specific and reference-provider presentation. The product retains Cash Review, larger evidence and a separate human decision workspace. The requested magenta palette is a visual choice and does not assert affiliation or legal authority.
