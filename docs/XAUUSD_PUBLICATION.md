# Publication and original commit evidence

Command-line HTTPS Git had no configured credential for pushing, and the existing
SSH trust configuration did not recognize GitHub. Neither credentials nor SSH
configuration were changed. The authorized branch and PR are published through
the connected GitHub integration instead.

The integration creates new commit identities. It preserves the exact Git trees
of the original local commit sequence in order, with each publication commit
message identifying its original local SHA. The report's short commit references
(`d3c664a`, `8445601`, `1cee2cb`, `10095a4`, `e578559`) refer to those **local**
experiment checkpoints, not the later publication commit identities.

[`XAUUSD_LOCAL_COMMITS.json`](XAUUSD_LOCAL_COMMITS.json) preserves their full
canonical commit objects, parent references and tree IDs. Their original SHA-1
identities can be checked by hashing Git's `commit <byte-count>\0` header followed
by the recorded UTF-8 object bytes. Publication verifies each remote tree against
its local tree before creating the next commit. This retains the original
preregistration/freeze evidence without claiming that publication happened before
the experiment. Local Git dates are not an independent timestamp attestation.

The numerical input/configuration/implementation/result hashes in the protocol,
freeze and report remain unchanged. No raw data or private experiment files are
published. A local evidence branch retains the original commits if the working
branch is subsequently aligned to the published history.
