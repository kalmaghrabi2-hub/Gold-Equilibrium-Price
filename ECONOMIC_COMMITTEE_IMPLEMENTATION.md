# Economic Committee → Engineering Committee Implementation Standard

## Scope
The system must keep three horizons separate: short-term Market Reference, medium-term Cyclical Fair Value, and long-term Structural/Physical Equilibrium. A forecasting layer cannot validate a structural equilibrium claim.

## Non-negotiable rules
- `100 - MAPE` is an **OOS Fit Score**, not probability or equilibrium accuracy.
- Final OOS data cannot be used for hyperparameter/model selection.
- No look-ahead and no imputation of critical fundamentals.
- Any failed/unvalidated layer has zero price weight.
- No market-relative clipping or cosmetic guardrail may force P* toward spot.
- If the strict gate fails: `model_status=REFERENCE_ONLY`, `equilibrium_claim=WITHHELD_NOT_VALIDATED`.

## Weekly hard gate
All must pass: non-zero model weight; MSE skill >=2%; relative MAPE improvement >=1%; one-sided Diebold-Mariano p<=0.05; positive skill in >=4/5 contiguous 52-week regimes; direction accuracy >=52.5%; R²>=0.60; MAPE<=12%; untouched final OOS >=260 weeks.

## Gold fundamentals gate
WGC quarterly/physical factors may affect price only after their own point-in-time OOS test beats persistence and demonstrates stable performance across regimes. Failed WGC overlays remain visible only as diagnostics with effective multiplier 1.0.

## Required production sequence
Compile → calibrate → independent strict validation → update latest inputs → apply publication gate → assert publication contract → commit outputs → deploy Pages after successful update.

## Engineering principle
Do not reduce a market/model gap merely because it looks implausible. Validate it or withhold the equilibrium claim.
