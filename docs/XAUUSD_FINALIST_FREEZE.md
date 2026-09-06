# Frozen finalists: XAUUSD M1 v1

Frozen on 2026-09-06 after all 672 registered development/selection cases and an independent ledger audit. No evaluation-period prices or results were loaded by the strategy runner.

**Finalists: none. April remains sealed.** All five candidates failed predeclared economic gates; there was no discretionary replacement, tuning or layer search.

| Candidate | Decision | Failed gates |
| --- | --- | --- |
| sma_cross | rejected | nonpositive:mid|0.58|0.05:signal; nonpositive:mid|0.58|0.15:signal; nonpositive:bid|0.58|0.15:signal; nonpositive:ask|0.58|0.15:signal; nonpositive_bootstrap_lower; nonpositive_march_half |
| channel_break | rejected | nonpositive:mid|0.48|0.05:signal; nonpositive:mid|0.48|0.05:account; nonpositive:mid|0.58|0.05:signal; nonpositive:mid|0.58|0.05:account; nonpositive:mid|0.58|0.15:signal; nonpositive:mid|0.58|0.15:account; nonpositive:bid|0.58|0.15:signal; nonpositive:bid|0.58|0.15:account; nonpositive:ask|0.58|0.15:signal; nonpositive:ask|0.58|0.15:account; nonpositive_bootstrap_lower; nonpositive_march_half |
| hour_momentum | rejected | nonpositive:mid|0.48|0.05:signal; nonpositive:mid|0.48|0.05:account; nonpositive:mid|0.58|0.05:signal; nonpositive:mid|0.58|0.05:account; nonpositive:mid|0.58|0.15:signal; nonpositive:mid|0.58|0.15:account; nonpositive:bid|0.58|0.15:signal; nonpositive:bid|0.58|0.15:account; nonpositive:ask|0.58|0.15:signal; nonpositive:ask|0.58|0.15:account; nonpositive_bootstrap_lower; nonpositive_march_half |
| band_reentry | rejected | nonpositive:mid|0.48|0.05:signal; nonpositive:mid|0.48|0.05:account; nonpositive:mid|0.58|0.05:signal; nonpositive:mid|0.58|0.05:account; nonpositive:mid|0.58|0.15:signal; nonpositive:mid|0.58|0.15:account; nonpositive:bid|0.58|0.15:signal; nonpositive:bid|0.58|0.15:account; nonpositive:ask|0.58|0.15:signal; nonpositive:ask|0.58|0.15:account; nonpositive_bootstrap_lower; nonpositive_march_half |
| rsi_reentry | rejected | nonpositive:mid|0.48|0.05:signal; nonpositive:mid|0.48|0.05:account; nonpositive:mid|0.58|0.05:signal; nonpositive:mid|0.58|0.05:account; nonpositive:mid|0.58|0.15:signal; nonpositive:mid|0.58|0.15:account; nonpositive:bid|0.58|0.15:signal; nonpositive:bid|0.58|0.15:account; nonpositive:ask|0.58|0.15:signal; nonpositive:ask|0.58|0.15:account; nonpositive_bootstrap_lower; nonpositive_march_half |

## Temporal and content evidence

- Preregistration commit: `d3c664a` (before implementation/results).
- Simulator commit: `8445601` (before historical runs).
- Additional audit/test commit: `1cee2cb` (no numerical implementation changes).
- Private finalist manifest SHA-256: `f13616e61ec6360be7bca2adcb8d0e9629701b5bc63f3c926eb3a92854fc3ffb`.
- Screen index SHA-256: `5454250a38b492b511ba478ed23c84ccb1bdde3b3a2d9e3bc1e5ce460c3f0ff0`.
- config_sha256: `26880725fa66c4cf5d7ec03d60ef9f7891b5789f1384b0c07c890be064f54f6c`.
- protocol_sha256: `0bdad5d75a88c46ab2b26ecdc8ed5dff7e5257f00f205f16121f8835006d86bf`.
- implementation_sha256: `40fc1a8e82e3295ba984d3348aacd6d4eed92241731e978b53ee3fcc3f03d19e`.
- Input SHA-256: `ef8398e0b732bc43f1bb9137fac0cab56c579eda51e7800df198a3fc52d53310`.
- Loaded strategy prefix: 69,846 rows; last label 2026-03-31 23:59 UTC.

The hash-bearing private manifest includes the source-file hashes, Python version, ranking values, bootstrap bounds and all failed gates. It is retained at `.local/experiments/finalists_v1.json`. This sanitized Git record is committed before the evaluation command records its no-finalist skip.

The economic conclusion applies to these exact rules, cost assumptions and periods. No-trade remains a zero-return reference, not evidence of a cash-generating strategy. See the [protocol](XAUUSD_COMPARISON_PROTOCOL.md) and [reproduction workflow](COMPARISON_WORKFLOW.md).
