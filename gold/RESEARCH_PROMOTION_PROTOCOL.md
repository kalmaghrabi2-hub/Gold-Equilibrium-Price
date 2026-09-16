# Gold Research-to-Publication Promotion Protocol

## Purpose
Prevent data-snooping after the final OOS results have been inspected while continuing model research.

## Locked facts
- The existing weekly final 260-week OOS has already been evaluated and is no longer eligible to be reused as a pristine promotion holdout for newly invented model families.
- Cyclical research generation v1 has been evaluated and rejected for publication.
- Historical FRED CSV data are current-vintage; they are not sufficient evidence of what was known on each historical forecast date.

## Research track
New feature sets, rolling windows, nonlinear/regime specifications and extra benchmarks may be explored only as RESEARCH_ONLY. They may use training/validation and historical diagnostic periods, but their results cannot automatically promote a model into the published price.

## Promotion requirements
A future model may affect the published reference/fair value only after all of the following are satisfied:
1. Predictor data are point-in-time, release-lag aware and revision-aware. FRED macro history must use ALFRED/realtime vintages where revisions matter, or a sufficiently long committed forward archive.
2. Model family, features, transformations, training window, hyperparameter grid and benchmark set are frozen before the promotion holdout is opened.
3. The promotion holdout has not been used to choose the model.
4. Weekly hard gates remain unchanged: MSE skill >=2%, relative MAPE improvement >=1%, one-sided HAC DM p<=0.05, >=4/5 positive 52-week regimes, direction >=52.5%, R2>=0.60, MAPE<=12%.
5. Persistence remains mandatory. Additional benchmarks should include random-walk-with-drift and a simple predeclared metal-specific benchmark.
6. No market-relative clipping or cosmetic override is allowed.
7. Any WGC physical overlay has a separate point-in-time price-effect validation gate. Until then its effective price weight is zero.

## Forward evidence
Daily committed institutional snapshots beginning 2026-09-16 create an auditable forward point-in-time archive. This archive may be used for future shadow validation without reconstructing unavailable historical vintages.

## Current publication rule
Until a candidate satisfies the complete promotion protocol, the production system remains REFERENCE_ONLY whenever the strict gate fails.
