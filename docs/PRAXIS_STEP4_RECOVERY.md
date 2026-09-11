# Step 4 complete recovery closure

The frozen `verify` command restored all 2,060 cataloged references. A separate
post-run packaging check, using the same frozen Catalog API, additionally bound
all nine registry inputs. It adds the normalized manifest, quote-cost evidence,
and London TZif/tzdata files that were not references in the inherited Step 3
catalog. No numerical source, result, protocol or gate changed during packaging.

A fresh catalog copied from the verified Step 4 catalog, its backup, and its
isolated restore each verified **2066 references**. Every
registry input resolves to matching bytes in both restored trees. The original
catalogs and the first recovery proof remain unchanged.

- Complete proof SHA-256: `915a4f44de97c67ef487f5d6be2117ee08e38bd3e59476426d7257a8c802d02d`.
- Exact recipe SHA-256: `ce1ede198108c2e86db5fe1949cfb4bc74e443f664e20f88c5206345b1841be6`.
- Private proof: `.local/praxis_step4_complete_recovery_v2/report.json`.
- Input mapping: `.local/praxis_step4_complete_recovery_v2/input_mapping.json`.

This is artifact recovery, not an installation of the archived timezone/runtime
on another host. Restore into fresh private paths and verify the mapped hashes;
do not overwrite existing evidence or replace system timezone files implicitly.
The manifest describes the wider corpus; this bounded archive does not contain
all 81 market series. It contains all nine inputs enumerated by the Step 4 registry. CLI reproduction
also requires the preserved original Step 3 baseline directory (including its
index and registration), frozen Git history, and Python 3.11.14 environment.
This check does not claim to restore an entire ready-to-run workstation.

The exact operational recipe is retained privately and reproduced below. It does
not calculate or select strategy results. Save it as an owner-only file beneath
ignored `.local/`, then use fresh output names. For example, with the retained
recipe and a newly verified screen:

```sh
PYTHONPATH=src .venv/bin/python .local/praxis_step4_complete_recovery_v2/reproduce.py \
  --catalog .local/praxis_step4_verified_repeat/catalog/research.sqlite \
  --output .local/praxis_step4_complete_recovery_repeat
```

```python
"""Archive registry support inputs using the frozen catalog API; no simulation."""
from pathlib import Path
import json,os,hashlib,argparse
from mynyra.catalog import Catalog,copy_private,restore_backup
from mynyra.datasets import archive_sha256
from mynyra.experiment import ROOT,step4_settings,save,private_path

os.umask(0o077)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'.local/praxis_step4_complete_recovery_v2')
parser.add_argument('--catalog',type=Path,default=ROOT/'.local/praxis_step4_verified_v2/catalog/research.sqlite')
args=parser.parse_args()
private=ROOT/'.local'; output=private_path(args.output)
output.mkdir(mode=0o700)
source=private_path(args.catalog)
restore_backup(source,output/'catalog.sqlite')
catalog=Catalog(output/'catalog.sqlite',private);catalog.migrate()
existing={digest:relative for digest,relative,_,_ in catalog.artifact_rows()}
evidence=step4_settings()['evidence'];mapping={}
for key,value in evidence.items():
    if not key.endswith('_path'):continue
    path=ROOT/value; digest=evidence[key[:-5]+'_sha256']
    assert archive_sha256(path)==digest
    if digest in existing:
        relative=existing[digest]
    else:
        if not path.is_relative_to(private):
            dest=output/'support'/key
            dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(path.read_bytes())
            path=dest
        with catalog.transaction() as db:catalog.register_artifact(db,path,'application/octet-stream')
        relative=path.relative_to(private).as_posix();existing[digest]=relative
    mapping[key]={'original_path':value,'canonical_private_path':relative,'sha256':digest}
save(output/'input_mapping.json',mapping)
with catalog.transaction() as db:catalog.register_artifact(db,output/'input_mapping.json','application/json')
# Preserve this exact operational recipe; it only uses already-frozen Catalog APIs.
recipe=output/'reproduce.py'
with recipe.open('xb') as f:f.write(Path(__file__).read_bytes())
with catalog.transaction() as db:catalog.register_artifact(db,recipe,'text/x-python')
counts={'original':catalog.verify_references()}
for label in ('backup','restore'):
    dest=output/label
    if label=='backup':catalog.backup(dest/'catalog.sqlite')
    else:restore_backup(output/'backup/catalog.sqlite',dest/'catalog.sqlite')
    source_root=private if label=='backup' else output/'backup/artifacts'
    for _,relative,_,_ in catalog.artifact_rows():copy_private(source_root/relative,dest/'artifacts'/relative)
    copied=Catalog(dest/'catalog.sqlite',dest/'artifacts')
    counts[label]=copied.verify_references()
    with copied.connect() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()==('ok',)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    for record in mapping.values():assert archive_sha256(dest/'artifacts'/record['canonical_private_path'])==record['sha256']
assert len(set(counts.values()))==1
record={'status':'passed','references':counts,'registry_inputs_restored':len(mapping),'recipe_sha256':archive_sha256(recipe)}
save(output/'report.json',record)
print(json.dumps(record))
```
