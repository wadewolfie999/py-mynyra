#!/usr/bin/env python3
"""Frozen Step 4 lifecycle. No broker/network imports or evaluation-price path."""

import argparse
from decimal import localcontext
import json
import os
from pathlib import Path
import runpy
import signal

from mynyra.catalog import Catalog, copy_private, restore_backup
from mynyra.datasets import archive_sha256
from mynyra.experiment import (
    ROOT, DEFAULT_CONFIG, STEP4_CONFIG, STEP4_PROTOCOL, STEP4_SOURCE,
    json_value, load_runs, private_path, run_cases, save, screen_cases, settings,
    step4_cases, step4_inputs, step4_provenance, step4_report, step4_select,
    step4_settings, step4_source_hashes, step4_inventory_hash, run_step4,
)


def copy_definition(source, destination):
    destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:
        out.write(source.read_bytes())
        out.flush()
        os.fsync(out.fileno())


def baseline(output,cfg,prov):
    bars=step4_inputs(cfg)
    base=settings(DEFAULT_CONFIG)
    reference=ROOT/'.local/praxis_step3_proof_v3/baseline'
    index=json.loads((reference/'index.json').read_text())
    run_cases(bars,base,screen_cases(base),output,prov,{'snapshot_sha256':cfg['input_sha256']})
    actual=json.loads((output/'index.json').read_text())
    if actual['runs']!=index['runs']:
        raise ValueError('Unchanged baseline numerical artifacts differ')
    save(output/'reconciliation.json',{'status':'passed','matching_result_hashes':len(actual['runs']),
         'expected_index_sha256':archive_sha256(reference/'index.json'),'provenance':prov})
    print(json.dumps({'baseline_matched':len(actual['runs'])}),flush=True)


def catalog_proof(output,screen,cfg,prov):
    private=ROOT/'.local'
    catalog_path=output/'catalog/research.sqlite'
    restore_backup(private/'praxis_step3_proof_v3/catalog/research.sqlite',catalog_path)
    catalog=Catalog(catalog_path,private)
    catalog.migrate()
    definition=output/'definition'
    for p in (STEP4_CONFIG,STEP4_PROTOCOL,STEP4_SOURCE):
        copy_definition(p,definition/p.name)
    # Archive all registered code, tests and protocol dependencies for recovery.
    for relative in prov['source_hashes']:
        source=ROOT/relative
        copy_definition(source,definition/'source'/relative)
    catalog.register_experiment(cfg['id'],definition/STEP4_PROTOCOL.name,definition/STEP4_CONFIG.name,prov['implementation_sha256'])
    snapshot=private/'praxis_step3_proof_v3/snapshot/xauusd_m1_preapril.csv'
    catalog.freeze_snapshot('praxis-step4-preapril','faraz-xauusd-m1-20260904-r1',cfg['id'],
        'development-and-selection','exploratory','2026-01-20T03:59:00+00:00','2026-04-01T00:00:00+00:00',snapshot,cfg['input_rows'])
    index=json.loads((screen/'index.json').read_text())
    for number,entry in enumerate(index['runs']):
        p=screen/entry['file']
        status=json.loads(p.read_text())['status']
        catalog.record_run(f'praxis-step4-{number:04d}',cfg['id'],'praxis-step4-preapril',
            entry['period'],entry['candidate'],entry['scenario'],entry['view'],p,status)
    with catalog.transaction() as db:
        for p in (screen/'registration.json',screen/'index.json',output/'audit.json',output/'aggregates.json',output/'advancement.json',definition/STEP4_SOURCE.name):
            catalog.register_artifact(db,p,'application/json')
        # Hash identity has one authoritative path: avoid registering a duplicate
        # copy of config/protocol while retaining the whole source tree privately.
        known={r[0] for r in catalog.artifact_rows()}
        for p in sorted((definition/'source').rglob('*')):
            if p.is_file() and archive_sha256(p) not in known:
                digest=catalog.register_artifact(db,p,'application/octet-stream')
                known.add(digest)
    original=catalog.verify_references()
    counts={'original':original}
    for label in ('backup','restore'):
        dest=output/label
        if label=='backup':catalog.backup(dest/'research.sqlite')
        else:restore_backup(output/'backup/research.sqlite',dest/'research.sqlite')
        source_root=private if label=='backup' else output/'backup/artifacts'
        for _,relative,_,_ in catalog.artifact_rows():
            copy_private(source_root/relative,dest/'artifacts'/relative)
        copied=Catalog(dest/'research.sqlite',dest/'artifacts')
        counts[label]=copied.verify_references()
        with copied.connect() as db:
            if db.execute('PRAGMA integrity_check').fetchone()!=('ok',) or db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Catalog restore integrity failed')
    if len(set(counts.values()))!=1:raise ValueError('Restored references differ')
    save(output/'recovery.json',{'status':'passed','references':counts})
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze-source','baseline','run','verify','evaluate'))
    parser.add_argument('--output',type=Path)
    parser.add_argument('--screen',type=Path)
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    os.umask(0o077)
    cfg=step4_settings()
    if args.command=='freeze-source':
        # This creates a versioned definition, not market results; commit it.
        with STEP4_SOURCE.open('x') as f:
            json.dump({'experiment':cfg['id'],'source_hashes':step4_source_hashes(),
                       'case_inventory_sha256':step4_inventory_hash(cfg)},f,sort_keys=True,indent=2)
            f.write('\n')
        print('Source manifest created; commit before any historical run.')
        return
    if args.output is None:parser.error('--output is required')
    output=private_path(args.output)
    if output.exists():raise ValueError('Output already exists; choose a fresh name')
    prov=step4_provenance()
    with localcontext() as context:
        context.prec=cfg['decimal_precision']
        if args.command=='evaluate':
            # No input path is opened, regardless of screen diagnostics.
            save(output,{'status':'not_opened','reason':'independent_data_unavailable','finalists':[],'provenance':prov})
        elif args.command in ('baseline','run'):
            def timeout(signum,frame):
                raise TimeoutError('Registered pass time limit exceeded')
            signal.signal(signal.SIGALRM,timeout)
            signal.alarm(cfg['maximum_pass_seconds'])
            try:
                if args.command=='baseline':baseline(output,cfg,prov)
                else:
                    if args.baseline is None:parser.error('--baseline reconciliation is required')
                    proof=json.loads((args.baseline/'reconciliation.json').read_text())
                    if proof.get('status')!='passed' or proof.get('matching_result_hashes')!=672 or proof.get('provenance')!=prov:
                        raise ValueError('Baseline proof differs from this freeze')
                    # Check actual evidence, not only its success flag.
                    base_index=json.loads((args.baseline/'index.json').read_text())
                    reference=json.loads((ROOT/'.local/praxis_step3_proof_v3/baseline/index.json').read_text())
                    if base_index['runs']!=reference['runs']:raise ValueError('Baseline inventory differs')
                    load_runs(args.baseline,prov,screen_cases(settings(DEFAULT_CONFIG)))
                    run_step4(output,cfg,prov)
            except Exception as error:
                if output.is_dir() and not (output/'failure.json').exists():
                    save(output/'failure.json',{'status':'incomplete','error_type':type(error).__name__})
                raise
            finally:signal.alarm(0)
        else:
            if args.screen is None or args.replay is None:parser.error('verify requires --screen and --replay')
            output.mkdir(mode=0o700,parents=True,exist_ok=False)
            audit=runpy.run_path(str(ROOT/'scripts/audit-comparison.py'))['audit']
            result=audit(args.screen,args.replay,cfg,prov,step4_cases(cfg))
            save(output/'audit.json',result)
            _,runs=load_runs(args.screen,prov,step4_cases(cfg))
            selection=step4_select(runs,cfg)
            save(output/'advancement.json',{**selection,'provenance':prov,'index_sha256':archive_sha256(args.screen/'index.json')})
            save(output/'aggregates.json',step4_report(runs,cfg))
            counts=catalog_proof(output,args.screen,cfg,prov)
            print(json.dumps({'status':'verified','cases':result['runs'],'references':counts,'finalists':[],
                              'evaluation':'independent_data_unavailable'}),flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status':'failed','error_type':type(error).__name__}),flush=True)
        raise SystemExit(1)
