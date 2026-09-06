# Publication and original commit evidence

Publication is pending. HTTPS Git had no credential available for pushing; existing
SSH trust did not recognize GitHub. The GitHub integration rejected a write with
HTTP 403, `Resource not accessible by integration`. Those attempts did not publish
the branch or create a PR.

Run the prepared script from an authenticated terminal:

```sh
bash scripts/publish-comparison.sh --publish
```

The script checks the branch, clean worktree, expected push destination and
original report ancestry. It pushes without rewriting commits and verifies the
remote head. With an authenticated `gh` installation, it reuses an existing PR
or creates one using [the prepared body](XAUUSD_PR_BODY.md). Otherwise it prints
the comparison URL for creating the PR in GitHub. It never merges the PR.
`--check` performs only local preflight checks. Errors appear in the terminal
and stop execution; fix the reported condition before rerunning.

The report's short commit references identify original local checkpoints.
[XAUUSD_LOCAL_COMMITS.json](XAUUSD_LOCAL_COMMITS.json) also preserves canonical
commit objects for the preregistration, simulator, audit, freeze and report.
Local Git dates are not an independent timestamp attestation. Normal Git push
preserves these identities and their parent history.

Numerical provenance and result hashes remain unchanged. Raw data and private
experiment artifacts remain excluded from publication.
