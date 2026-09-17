# WP-P2 bounded provider screen — 2026-09-15

## Scope and disposition

This report records one zero-spend, read-only screen of three distinct simulated
account products. Active discovery and review remained below 20 minutes, within
the 60-minute limit. FeneFX was excluded before selection. Only official public
provider pages were used; no account, login, identity submission, provider contact,
purchase, terms acceptance, permission change, order, or private value entered a
search or public record.

**Disposition:** two products are incompatible because their official eligibility
rules exclude the recorded operator jurisdiction. One product remains unresolved
and may be worth one more evidence check, but it is not approved for purchase or
an economic attempt. Nothing here establishes strategy viability, profitability,
income, or the ability to receive a payout.

The products were selected as recognizable CFD evaluation routes with public
documentation relevant to XAUUSD and automation. A decisive eligibility failure
ended review of that product, as required by the assessment method.

## Results

| Product | Operator eligibility | Automated XAUUSD and interface | Payout compatibility | Other P2 criteria | Screen result |
| --- | --- | --- | --- | --- | --- |
| FTMO Challenge: 2-Step | **Incompatible.** FTMO's official eligibility page excludes persons who are nationals or residents of the recorded jurisdiction, subject to a narrow EEA-residency and EEA traditional-bank exception for which no reviewed qualifying evidence is recorded. Review stopped here. | Not assessed after decisive incompatibility. | Not assessed after decisive incompatibility. | Not assessed after decisive incompatibility. | **Fail; stop.** |
| The5ers High Stakes 2-Step | **Incompatible.** The product page and terms list the recorded jurisdiction as a forbidden territory and prohibit access or attempted use from it. Review stopped here. | Not assessed after decisive incompatibility. | Not assessed after decisive incompatibility. | Not assessed after decisive incompatibility. | **Fail; stop.** |
| FundedNext CFD Stellar 2-Step, USD 6,000, MT5, no add-ons | **Supported for this public-screen scope, not finally verified.** The current restricted-country page does not list the recorded jurisdiction, and FundedNext's payout documentation explicitly describes a jurisdiction-specific payout route. Final eligibility still depends on KYC and provider review. | **Supported at product level.** The current Stellar 2-Step rules allow EAs/custom indicators for account sizes below USD 50,000. MT5 is offered, and FundedNext's current commission page explicitly documents XAU/USD. Mynyra has no MT5 execution adapter, so implementation compatibility remains unresolved and would require a separately tested integration. | **Unresolved.** General methods include crypto, but the official payout page says traders in the recorded jurisdiction may use only TC Pay. Existing owner constraints establish access to a crypto wallet, not a verified TC Pay-to-usable-cash route. No login or contact was used to resolve this. | The public rules state 5% daily loss, 10% maximum loss, two targets (8% then 5%), five minimum trading days per phase, and consistency/IP/VPN/prohibited-strategy restrictions. Current global base price is USD 59.99; a time-limited public offer advertises USD 29.99. Total exposure, operating viability, strategy-rule fit, final attempts, and STOP compatibility remain unresolved pending private limits and a viable strategy. | **Unresolved; no purchase recommendation.** |

## Official evidence

All pages were retrieved on 2026-09-15. Page wording and offers are time-sensitive;
they must be rechecked before any later decision involving exposure.

### FTMO Challenge: 2-Step

- Product identity and two-stage structure:
  https://ftmo.com/en/challenge/
- Eligibility and restricted persons/jurisdictions:
  https://ftmo.com/en/faq/who-can-join-ftmo/

### The5ers High Stakes 2-Step

- Product terms, account rules, assets, MT5 platform, pricing, and forbidden
  territories:
  https://www.the5ers.com/high-stakes/
- General terms and forbidden-territory definition:
  https://the5ers.com/terms-and-conditions/

### FundedNext CFD Stellar 2-Step, USD 6,000, MT5

- Current resident/citizen restrictions and anti-circumvention rule:
  https://help.fundednext.com/en/articles/8020080-are-any-countries-restricted-on-fundednext-cfds
- Stellar 2-Step rules, loss limits, minimum days, EA scope, IP/VPN, and prohibited
  practices:
  https://help.fundednext.com/en/articles/8021076-what-rules-do-i-need-to-follow-in-the-stellar-2-step-challenge
- Profit targets and product sizes:
  https://help.fundednext.com/en/articles/8021071-what-is-the-profit-target-of-the-stellar-2-step-challenge
- Supported platforms and limitations:
  https://help.fundednext.com/en/articles/8019808-which-platforms-can-i-use-for-trading-at-fundednext
- XAU/USD/metal commission evidence:
  https://help.fundednext.com/en/articles/10701368-what-are-the-commission-charges-for-stellar-challenges-and-fundednext-accounts
- Payout methods, jurisdiction-specific TC Pay restriction, processing statement,
  and gateway charges:
  https://help.fundednext.com/en/articles/8020084-how-can-i-withdraw-my-profits
- Standard first and later reward cycles:
  https://help.fundednext.com/en/articles/9430969-what-is-the-trading-cycle-count-in-my-stellar-2-step-fundednext-account
- Current USD 6,000 base price and time-limited offer:
  https://help.fundednext.com/en/articles/16769387-what-is-the-fundednext-start6k-offer

## Interpretation and limits

“Supported” means only that the cited public page supports the stated criterion as
of retrieval. It does not prove successful KYC, continuing availability, lawful
receipt, compatibility with an unbuilt adapter, or compliance by a future strategy.
An omission from a restricted list is combined here with the provider's explicit
jurisdiction-specific payout instruction; it is not inferred from website access.

The FundedNext evidence contains a meaningful product/platform distinction:
Match-Trader documentation says trading is manual, while the selected sub-USD
50,000 MT5 product's current rules permit EAs. The result therefore applies only
to the exact MT5 configuration above. It must not be generalized to Match-Trader,
larger account sizes, another model, or a future rule version.

No product can be assessed for strategy-rule fit because Py-Mynyra has no surviving
strategy candidate. No exposure-dependent conclusion is possible until the owner
settles final loss, funding, attempt, debt, and STOP limits. The temporary discount
is not a reason to accelerate a purchase.

## Recommended next action

Do not screen more providers yet. Perform one bounded, official-public-evidence
check of the TC Pay receipt path applicable to FundedNext and determine whether it
can deliver usable cash through a channel the owner can legitimately access,
without creating an account or contacting the provider. If that cannot be supported,
reject FundedNext and return to P1. If it can, retain FundedNext only as a candidate
for later assessment; settle the private exposure/attempt/STOP contract and obtain
a viable strategy before any purchase or implementation decision.
