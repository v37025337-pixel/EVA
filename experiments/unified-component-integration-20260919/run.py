"""Execute the existing four-organ genetic profile through one durable kernel.

Cases are generated from the repository's declared bounded task grammar. This
is an actual offline runtime integration experiment, not an internet benchmark.
"""
import argparse
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from successor.archive import file_sha
from successor.generation_tasks import challenge
from successor.kernel import SuccessorKernel


def run(manifest, output):
    output.mkdir(parents=True, exist_ok=False)
    state = output / 'kernel.sqlite'
    kernel = SuccessorKernel(manifest, state)
    try:
        spec = {'domain': 'native_source',
                'training': [{'input': {'text': a}, 'expected': b}
                             for a, b in [('abc', 'cba'), ('def', 'fed'), ('gh', 'hg')]],
                'validation': [{'input': {'text': a}, 'expected': b}
                               for a, b in [('ijk', 'kji'), ('lm', 'ml')]],
                'queries': [{'input': {'text': 'nop'}}]}
        learned = kernel.open_goal(spec)
        kernel.think(30)
        assert kernel.cognitive_snapshot()['goals'][str(learned)]['status'] == 'VALIDATED_ON_HOLDOUT'

        def requests(seed):
            return [{'kind': 'component', 'payload': task,
                     'expect': {'path': ['answer'], 'equals': expected}}
                    for task, expected in challenge(seed)]

        seed = secrets.token_hex(16)
        tasks = requests(seed)
        baseline = [kernel.execute(t) for t in tasks]
        proposal = kernel.propose_component_generation()
        admission = kernel.admit_component_generation()
        assert admission['passed'], admission
        identity = kernel.identity
        kernel.close()
        kernel = SuccessorKernel(manifest, state)
        assert kernel.identity == identity
        after = [kernel.execute(t) for t in tasks]
        fresh_seed = secrets.token_hex(16)
        kernel.submit('Fresh tasks through the common queue', requests(fresh_seed))
        fresh = kernel.resume(10)
        recalled = kernel.open_goal(spec, budget=1)
        kernel.think(20)
        recall = kernel.cognitive_snapshot()['goals'][str(recalled)]
        assert recall['attempted'] == ['reuse_verified_source']
        assert recall['result']['predictions'] == ['pon']
        assert all(r['status'] == 'VERIFIED' for r in after + fresh)
        assert all(r['result']['component_generation'] == 1 for r in after + fresh)
        verified = kernel.verify_state()
        report = {'schema': 'yado.unified_component_integration.v1', 'status': 'PASS',
                  'scope': 'OFFLINE_DECLARED_COMPONENT_GRAMMAR_REAL_EXECUTION',
                  'integration_authorship': 'ASSISTANT', 'profile_selection': 'EXISTING_KERNEL_CONTROLLER',
                  'identity_digest': identity, 'manifest_sha256': file_sha(manifest),
                  'source_sha256': {p: file_sha(ROOT / p) for p in (
                      'successor/kernel.py', 'successor/component_binding.py', 'successor/generation.py')},
                  'baseline_verified': sum(r['status'] == 'VERIFIED' for r in baseline),
                  'after_activation_verified': len(after), 'fresh_queue_verified': len(fresh),
                  'learned_source_reused': True, 'restart_verified': True,
                  'state_integrity': verified, 'component_state': kernel.component_generation_snapshot(),
                  'baseline_seed': seed, 'fresh_seed': fresh_seed,
                  'baseline': baseline, 'proposal': proposal, 'admission': admission,
                  'after_activation': after, 'fresh_queue': fresh,
                  'formal_generation_changed': False, 'unrestricted_self_rewrite_proven': False}
        (output / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + '\n')
        return {k: report[k] for k in ('status', 'baseline_verified', 'after_activation_verified',
                                      'fresh_queue_verified', 'learned_source_reused', 'restart_verified',
                                      'state_integrity')}
    finally:
        kernel.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest.resolve(), args.output.resolve()), indent=2))
