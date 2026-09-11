# Step 4 artifact identity correction

The initial preregistration was committed/published as `aae610b` before any new
candidate result. During the first bounded run, source review identified that its
result envelope did not include the experiment ID. Unchanged SMA/no-trade results
can be byte-identical to v1, while the append-only catalog correctly binds each
artifact hash to one canonical path. The planned new result paths would therefore
fail catalog registration.

The first attempt was interrupted and retained create-only under
`.local/praxis_step4_screen_v1/`, with explicit invalidation and termination records. Its supervising process
interrupted first; the surviving worker was then directly terminated. A total of
523 partial case files remain, with no complete index. Only progress
counts were inspected; no candidate economics, charts, trades or bootstrap results
were inspected. No completed index, selection, replay or evaluation was produced.

Correction: add the registered experiment ID to each Step 4 result envelope and
verify it against registration on load. Numerical rules, parameters, costs, sizing,
splits, gates and evaluation prohibition are unchanged. V1 result serialization
and numerical baseline remain unchanged. A synthetic cross-experiment artifact
regression covers the catalog collision and its prevention.

Regenerate and commit the source manifest as a correction, keeping the original
manifest and implementation in Git history. Repeat the unchanged 672-result proof
and the full 1,344-case batch/replay using fresh `_v2` evidence directories. Do not
resume, overwrite, compare candidate performance with, or select from the partial
first attempt. The correction is not parameter tuning or a new economic hypothesis.
