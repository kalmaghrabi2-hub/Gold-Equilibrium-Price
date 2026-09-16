# Gold Institutional Data Upgrade

Purpose: improve genuine out-of-sample skill without weakening publication gates or tuning on the final OOS window.

## Point-in-time data policy

1. Every predictor must be available before the forecast week starts.
2. Final 260-week OOS is never used for factor, hyperparameter, or blend selection.
3. Revised macro/fundamental data may not be backfilled as if the revision had been historically known.
4. Daily snapshots are retained from activation onward to build an auditable point-in-time archive.
5. A candidate factor can affect the published price only after independent strict validation passes all gates.

## Priority institutional sources

| Factor | Series/source | Frequency | Role |
|---|---|---:|---|
| 10Y real yield | Federal Reserve/FRED `DFII10` | Daily | monetary opportunity cost |
| Broad USD | Federal Reserve/FRED `DTWEXBGS` | Daily | currency valuation channel |
| VIX | CBOE via FRED `VIXCLS` | Daily | risk regime |
| 10Y breakeven inflation | FRED `T10YIE` | Daily | inflation expectations |
| 10Y nominal Treasury | Federal Reserve/FRED `DGS10` | Daily | nominal rates/control |
| Gold ETF holdings/flows | World Gold Council | Weekly/monthly | investment demand |
| Central-bank holdings/purchases | World Gold Council | Monthly/quarterly | official-sector demand |
| Mine production/AISC | World Gold Council | Quarterly/annual | structural supply/cost |

## Research protocol

The research layer tests feature sets on training + validation only, freezes the selected specification, and evaluates once on the untouched final 260 weeks. Persistence remains the primary benchmark. Additional benchmarks will be added separately. No price clipping or cosmetic convergence toward spot is allowed.

The current published model remains `REFERENCE_ONLY` until the strict governance contract passes.
