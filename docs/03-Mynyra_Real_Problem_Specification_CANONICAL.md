# Mynyra — Real Problem Specification

**Status:** Canonical problem definition  
**Owner:** Vahid  
**Purpose:** Define the optimization problem before solution search.  
**Scope:** Economic/technical trajectory of Mynyra and its surrounding operating system.  

## 1. Problem

Starting from the current financial, technical, operational, and external state, determine a sequence of actions that reaches the first **financially self-sustaining state** as quickly as practicable while keeping failure survivable.

The problem is **not** to finish Mynyra as quickly as possible.

The system evolves as

\[
S_0 \xrightarrow{a_1} S_1 \xrightarrow{a_2} S_2 \cdots \xrightarrow{a_n} S_*
\]

where each state contains the relevant financial, technical, operational, and external conditions, and each action may include development, testing, validation, trading, account acquisition, manual operation, automation, withdrawal, debt repayment, waiting, or abandonment of an unproductive path.

**Mynyra development is one admissible action class, not the terminal objective.**

---

## 2. Objective

Reach a state \(S_*\) in which trading produces **repeatable and actually realizable cash flow** sufficient to:

- finance continued operation;
- materially reduce or remove dependence on external financing;
- survive ordinary failures without returning to the initial fragile state;
- support continued development from a stronger financial position.

The primary quantities to minimize are:

- elapsed time;
- scarce capital consumed.

They are optimized subject to hard constraints on ruin, safety, authority, evidence quality, and recoverability.

---

## 3. Economic Target

The target variable is not merely trading P&L:

\[
\text{gross P\&L}
\neq
\text{realized P\&L}
\neq
\text{withdrawable profit}
\neq
\text{cash received}
\neq
\text{net increase in usable assets}.
\]

The relevant objective concerns **money actually under operational control**, after relevant costs, failed attempts, challenge fees, resets, payout restrictions, debt obligations, and unavoidable losses.

A useful waypoint such as \$300/week may remain operationally valuable, but the deeper state transition is:

\[
\boxed{\text{externally financed / fragile} \rightarrow \text{self-financing / recoverable}}
\]

---

## 4. State

The problem must operate on the current state \(S(t)\), not on a permanently fixed initial condition.

At minimum:

\[
S(t)=(
\text{cash},
\text{debt},
\text{available financing},
\text{Mynyra readiness},
\text{strategy evidence},
\text{account access},
\text{time},
\text{operator capacity},
\text{infrastructure},
\text{risk capacity},
\text{external rules}
).
\]

Evidence is time-dependent and may become stale. Material state changes require re-evaluation of the preferred trajectory.

---

## 5. Admissible Actions

No implementation path is assumed in advance. Actions may include:

- developing part of Mynyra;
- running experiments;
- backtesting or live-read validation;
- manually performing operations not yet worth automating;
- acquiring or attempting prop accounts;
- using existing infrastructure;
- improving strategy evidence;
- withdrawing funds;
- repaying debt;
- increasing capital reserves;
- waiting for additional evidence;
- abandoning a strategy, account path, feature, or architecture branch;
- automating a previously manual operation.

An action is not justified merely because it improves Mynyra. It must improve the relevant state, remove important uncertainty, reduce risk, increase recoverability, or enable a necessary later transition.

---

## 6. Constraints

### 6.1 Financial survival

Expected value alone is insufficient if failure can eliminate the ability to continue.

Conceptually:

\[
P(\text{ruin before } S_*) < \epsilon.
\]

### 6.2 Authorized exposure

The path must respect explicit limits on:

- personal cash at risk;
- borrowed capital and additional debt;
- challenge/account attempts;
- drawdown and loss per attempt;
- recycling of profits;
- conditions requiring STOP.

A path outside the authorized envelope is invalid even if its expected return is attractive.

### 6.3 Technical and operational safety

Financial urgency must not weaken minimum safety requirements. Prevent the positive feedback loop:

\[
\text{financial pressure}
\rightarrow
\text{weaker validation}
\rightarrow
\text{greater failure}
\rightarrow
\text{less capital}
\rightarrow
\text{greater financial pressure}.
\]

### 6.4 Bounded safety work

The opposite failure must also be prevented:

\[
\text{fear of failure}
\rightarrow
\text{more infrastructure}
\rightarrow
\text{more abstraction}
\rightarrow
\text{delayed economic exposure}
\rightarrow
\text{no revenue}.
\]

Safety work must remain proportional to the risk it controls.

---

## 7. Evidence

Every claim must be interpreted according to exactly what its evidence proves:

\[
\text{backtest PASS} \not\Rightarrow \text{live profitability},
\]

\[
\text{live-read PASS} \not\Rightarrow \text{execution profitability},
\]

\[
\text{profitable strategy} \not\Rightarrow \text{successful cash realization}.
\]

Technical milestones must not become false proxies for economic convergence.

The eventual cash-realization chain is broader:

\[
\text{strategy}
\rightarrow
\text{account}
\rightarrow
\text{rules}
\rightarrow
\text{execution}
\rightarrow
\text{eligible profit}
\rightarrow
\text{withdrawal}
\rightarrow
\text{cash received}.
\]

---

## 8. Recoverability

A good path is not merely one with a high probability of success; it is one whose failures leave useful continuation states.

For every action:

\[
S_i \xrightarrow{a_i} S_{\text{failure}}
\]

must be considered explicitly.

The governing question is:

> **From what state can the system resume if this action fails?**

Actions capable of irreversible or cascading damage require stronger justification than actions whose failures are cheap and recoverable.

---

## 9. Value of Information

Some actions are valuable mainly because they eliminate uncertainty rather than because they immediately create functionality or money.

A useful heuristic is:

\[
\frac{\text{important uncertainty eliminated}}
{\text{time}+\text{capital}+\text{risk}+\text{irreversibility}}.
\]

A small experiment that invalidates an entire path may be more valuable than implementing a large feature.

---

## 10. Non-Objectives

The following are **not independent objectives**:

- finishing Mynyra;
- maximizing automation;
- maximizing architectural elegance;
- implementing every planned feature;
- maximizing technical sophistication;
- generalizing Mynyra into Nyvora;
- eliminating all manual operations;
- achieving a particular prop-account structure;
- reaching a specific software architecture.

They are justified only when they causally improve the trajectory toward the target state or control a necessary risk.

The key structural correction is:

\[
\boxed{\text{Mynyra development trajectory} \neq \text{economic trajectory}}
\]

unless evidence establishes otherwise for a particular action.

---

## 11. Decision Test

Every proposed action should answer four primary questions:

\[
\boxed{\text{Does it materially move the economic state?}}
\]

\[
\boxed{\text{What important uncertainty does it remove?}}
\]

\[
\boxed{\text{What can it irreversibly lose?}}
\]

\[
\boxed{\text{What state remains if it fails?}}
\]

Secondary checks:

- Is the action currently authorized?
- Is its evidence still valid?
- Does it introduce a new dependency or failure mode?
- Can failure cascade into unrelated parts of the system?
- Is there a cheaper experiment that provides the same information?
- Does this action genuinely belong on the critical path?
- Is complexity being introduced earlier than necessary?

---

## 12. Canonical Formulation

> **Starting from the current financial, technical, operational, and external state, identify a sequence of authorized, evidence-driven, and survivable actions that reaches the first financially self-sustaining state as quickly as practicable.**
>
> **Optimize jointly for elapsed time and scarce capital while constraining probability of ruin, irreversible loss, technical and operational failure, unauthorized exposure, and unrecoverable state transitions.**
>
> **No particular development, trading, prop-account, automation, or architectural path is assumed in advance. Mynyra development is one possible control variable within the larger economic system.**
>
> **The target is not a finished product but a durable regime in which repeatable, realizable cash flow can finance continued operation and ordinary failures remain recoverable.**
>
> **Actions should be selected according to their causal effect on the economic state, their value of information, their downside and irreversibility, and the quality of the state that remains after failure.**

---

## Core Principle

\[
\boxed{\text{Do not optimize the path to a finished Mynyra.}}
\]

Optimize:

\[
\boxed{\text{the path from the present state to a financially self-sustaining state.}}
\]

Then evaluate Mynyra, feature by feature and action by action, according to whether it actually belongs on that path.
