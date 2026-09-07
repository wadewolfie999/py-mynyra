# Praxis

Praxis is Mynyra's name for carrying an operation from a clear purpose through
reasoned action, verification, and a useful handoff. Excellence means sufficient
reliable evidence and a maintainable result within the available time and resources.
It is an aspiration and a working discipline, not a claim of perfection.

The owner's opinions specify desired outcomes and preferences. Challenge proposed
methods, compare consequential alternatives, and change the approach when evidence
supports it. Explicit authority and safety limits still bind the work. The
[research expansion sequence](RESEARCH_EXPANSION_SEQUENCE.md) owns current gates;
propose and record justified revisions rather than silently skipping dependencies.

For each operation:

1. Establish the intended outcome, current evidence, uncertainty and authority.
2. Choose the smallest useful experiment or implementation; consider a materially
   different alternative when the decision has lasting consequences.
3. Execute understood mechanical work through a bounded, reproducible script.
   Retain its process handle and private evidence; avoid repeated manual tool loops.
4. Verify behavior and failures against the intended outcome. Report what passed,
   what remains uncertain, and what would change the decision.
5. Preserve knowledge in the repository and offer changes through a reviewable PR.
   Completion requires evidence; a plan, commit or approval alone is insufficient.

The human is an active orchestrator. Surface exact commands promptly when human
access, interactive sudo, authentication or unavailable host access would unblock
work. Explain purpose, effects, expected success and how the agent will verify it.
Run ordinary authorized commands directly. Never ask for passwords or bypass
interactive authentication; do not confuse a command suggestion with its execution.

Keep this definition in GitHub alongside the operation's scripts and evidence
summaries so future sessions inherit the practice, not only the nickname.
