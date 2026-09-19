"""Carry the completed repair checkpoint across its canonical metadata binding."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from run import ROOT, canonical_source_updates, save, events
from successor.archive import file_sha
from successor.continuity import prepare_upgrade
from successor.kernel import SuccessorKernel
from successor.generation import GenerationKernel


def seal(output):
    output = output.resolve()
    evidence = output / 'admission-repair'
    before = json.loads((output / 'summary.json').read_text())
    assert before['status'] == 'PASS_REPAIRED_REPLAY_JSON_AND_READMISSION'
    assert json.loads((evidence / 'fresh-process-verification.json').read_text())['status'] == 'PASS_FRESH_PROCESS_OFFLINE_REPLAY'
    prior_events = events(output / 'kernel.sqlite')
    updates = canonical_source_updates(output / 'birth/manifest.json')
    assert updates and len(updates) == 3
    prior = output / 'prebinding-birth'
    (output / 'birth').rename(prior)
    transition = prepare_upgrade(prior / 'manifest.json', output / 'kernel.sqlite', output / 'birth', source_updates=updates)
    shutil.copyfile(output / 'birth/kernel.sqlite', output / 'kernel.sqlite')
    kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
    try:
        kernel.db.execute('PRAGMA journal_mode=DELETE')
        state = kernel.verify_state()
        assert state['tick'] == before['state_after']['tick'] + 1
        assert kernel.identity == before['identity_digest']
        component = GenerationKernel(kernel, output / 'component-evolution/experience.sqlite', output / 'component-evolution/state.sqlite')
        try:
            assert component.snapshot() == before['component_state']
        finally:
            component.close()
    finally:
        kernel.close()
    assert events(output / 'kernel.sqlite')[:-1] == prior_events
    save(evidence, 'summary-before-canonical-binding', before)
    after = {**before, 'state_after': state, 'implementation_digest': transition['implementation_digest'],
             'canonical_maintenance_binding_applied': True, 'state_before_binding': before['state_after']}
    save(output, 'summary', after); save(evidence, 'summary', after)
    save(evidence, 'canonical-binding', {'status': 'PASS_CANONICAL_METADATA_CONTINUITY',
        'transition': transition, 'source_updates': updates, 'component_readmission_preserved': True})
    for relative in updates:
        target = output / 'source-overlay' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    receipt = json.loads((output / 'continuation-receipt.json').read_text())
    receipt['state_after'] = state
    receipt['checkpoint_files_sha256'] = {str(p.relative_to(output)): file_sha(p) for p in sorted(output.rglob('*'))
        if p.is_file() and p.name != 'continuation-receipt.json' and not p.name.endswith(('-wal', '-shm'))}
    save(output, 'continuation-receipt', receipt)
    print(json.dumps({'status': 'PASS_CANONICAL_METADATA_CONTINUITY', 'state': state,
                       'implementation_digest': transition['implementation_digest']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    seal(parser.parse_args().output)
