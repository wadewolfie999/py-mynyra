# WP-P2-ECON-001 — Economic-route acceptance criteria

**Phase:** P2 readiness; W1 owner discovery and W2 assessment preparation are
complete. The bounded W3 provider screen is complete; W4 records an unresolved
route rather than a provider approval.
**Authority:** Vahid/Wade explicitly approved Route B and opening this package in
the project conversation: “Yes, I approve. Proceed”. On 2026-09-15 the owner also
explicitly authorized implementation of the first working cycle, including this
bounded public provider screen. That later instruction does not authorize any
provider interaction, account action, spending, permission change, or order.
**Executor:** Codex. **Decision owner:** Vahid/Wade.
**Source baseline:** `8d5081131af3b88cb45f554a2d730d7108ca8ddb` plus the locally
approved [roadmap](EXECUTION_ROADMAP_BASELINE.md) and
[route decision](WP_P1_ROUTE_001.md). Repository publication remains pending.

## Decision and deliverables

Establish the criteria that an economic route would need to satisfy before a
bounded provider assessment is useful. This is P2 preparation, not P6 approval
for an economic attempt. A suitable account route would still need a strategy
and the later validation required by the roadmap.

Deliverables are an owner constraint record, the acceptance schema below, a bounded
assessment method, a readiness disposition, and the
[bounded provider findings](WP_P2_PROVIDER_SCREEN.md). Work already authorized by
the owner continues without repeated approval requests for routine preparation.

## Owner constraints and privacy

Owner discovery has established enough non-sensitive constraints to assess public
provider terms: the relevant operator jurisdiction, automated XAUUSD scope,
platform flexibility subject to explicit automation permission and a supported
execution interface, a payout-channel requirement, a near-term first-receipt
preference, and a zero-spend boundary for the assessment itself. The income
trajectory remains an aspiration rather than evidence of feasibility. Final loss,
funding, attempt and STOP limits remain provisional or unresolved. No personal
financial values are included in this document, and no answer grants permission
to spend.

If exact values later need to be persisted, record them only under ignored
`.local/economic-constraints/`, using owner-only directories and files (0700/0600),
and do not echo them in commands, tool output, versioned documents or provider
queries. The proposed path has been checked against Git ignore rules; no private
contract has been created. Record source, units, period and whether each value is
confirmed, provisional or unresolved. Preserve prior records when revising an
accepted constraint.

Public records can indicate whether the cash target, cost coverage, repeatability,
reserve, exposure, debt, attempt and STOP criteria are established. Avoid exact
thresholds or derived combinations that would disclose the private values.

## Acceptance schema

This table defines what later evidence must establish. It contains no finding
about any provider and does not require all personal completion criteria to be
settled before useful read-only work.

| Criterion | Required evidence or comparison | If missing or conflicting |
| --- | --- | --- |
| Operator eligibility | Official terms for the actual account holder's relevant jurisdiction and eligibility; obtain only necessary owner context. | Unresolved; do not infer eligibility from website access or demo access. |
| Automation and market | Official permission for the intended automated XAUUSD strategy, instrument availability, platform and API restrictions. | Unresolved; explicit incompatibility fails the criterion. |
| Account risk rules | Exact daily/total loss calculation, equity/balance basis, reset time, leverage, position and event restrictions. | Unresolved until the intended behavior can be checked against those rules. |
| Total personal exposure | All fees, subscriptions, resets, capital at risk and other obligations compared privately with owner limits. | Unresolved if liabilities are unbounded or not understood; known excess fails. |
| Cash receipt | Official payout eligibility, timing, minimums, deductions, permitted recipient/payment method and applicable operator restrictions. | Unresolved when receipt cannot be substantiated; dashboard profit is insufficient. |
| Operating viability | Full recurring costs, maintenance demand and recovery needs compared with the owner's accepted coverage and reserve requirements. | Record the specific missing input; do not invent expected strategy returns. |
| Attempts and STOP | Owner-defined attempt cap, debt rules and stop/revisit triggers mapped to proposed account terms. | No exposure-dependent decision until established. |

Use pass-for-stated-scope, fail, unresolved and not-applicable-with-reason for
each criterion. Include the evidence date, exact source and account product.
A pass on eligibility or terms establishes no profitability claim. A critical
unknown prevents a positive overall feasibility finding; it does not prevent
documenting known facts or ruling out a demonstrably incompatible option.

## Bounded assessment method

Working defaults for the later read-only screen: at most three distinct account
products and 60 minutes of active research before a findings checkpoint. These
are executor planning bounds, not owner cash limits. FeneFX remains excluded per
the existing project context. The completed screen and its exact product scope are
recorded in [WP_P2_PROVIDER_SCREEN.md](WP_P2_PROVIDER_SCREEN.md).

Use official product terms, eligibility restrictions, payout documentation and API
policies as primary evidence. Marketing and third-party comparisons can locate
sources but cannot override binding product terms. Record each page's URL,
retrieval date, effective date when present and exact product/version. Recheck
decisive terms when assembling the conclusion and before any later exposure
decision; there is no blanket freshness guarantee.

If official sources conflict, retain both references and the discrepancy. An
unresolved contradiction stays unresolved. Do not contact support or submit owner
information to resolve it during this package. Stop at the candidate/time limit,
a decisive incompatibility, or a need for prohibited interaction. Preserve a
partial result with a reason and a next evidence requirement.

Keep provider research separate from private threshold comparisons: public
research obtains terms; local private comparison determines compatibility. Do not
place personal limits or identifying details in search queries. No purchase,
account creation, login, identity submission, terms acceptance, provider contact,
order, sealed-data access or broker permission change is included.

## State and next action

| Dimension | Current state |
| --- | --- |
| Execution | readiness reconciliation and one three-product public screen complete |
| Evidence validity | two products decisively incompatible on eligibility; one exact product remains unresolved; no positive feasibility, strategy, income or payout finding |
| Evidence access | official public provider pages and repository records available; exact private values intentionally not persisted here; no account/login evidence used |
| Verification | official pages rechecked on 2026-09-15; product, URL, criterion and unresolved evidence recorded in the linked report |
| Decision | approve no provider or purchase; retain one exact FundedNext configuration only for a narrow payout-route evidence check |
| Authorization | the completed public screen was authorized; no further provider research, interaction, account creation, spending, permission change or trading authority follows automatically |

Recommended next action: do not widen the provider list. In a separately scoped
read-only step, use official public evidence to determine whether FundedNext's
jurisdiction-specific TC Pay route can deliver usable cash through a channel the
owner can legitimately access. Reject it if that cannot be supported without login
or contact. Even if supported, resolve final loss, funding, attempt and STOP limits
and establish a viable strategy before any purchase or exposure.

The readiness reconciliation and this first bounded screen are closed. The result
is useful but unresolved: no provider, strategy, profitability, account-purchase,
payout-receipt or trading approval has been established.
