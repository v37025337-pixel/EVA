"""Reproduce on the predecessor checkout, then continue its exact journal.

Run with the selected checkout on PYTHONPATH. The fixtures and controller repair
are maintainer-authored; source selection and retry decisions execute in YADO.
"""
import argparse
import json
from pathlib import Path

from successor.archive import file_sha
from successor.kernel import ROOT, SuccessorKernel


def goal(structured=False):
    def expected(x, y):
        return {'total': x + y} if structured else x + y
    return {'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
            'training': [{'input': {'x': x, 'y': y}, 'expected': expected(x, y)}
                         for x, y in [(2, 7), (5, -3), (-4, 13)]],
            'validation': [{'input': {'x': x, 'y': y}, 'expected': expected(x, y)}
                           for x, y in [(11, -6), (-8, -9)]],
            'queries': [{'input': {'x': 31, 'y': 17}}]}


def journal(kernel):
    return [dict(row) for row in kernel.db.execute(
        'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick')]


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def run(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    if args.phase == 'parent':
        kernel = SuccessorKernel(args.manifest, args.state)
        try:
            kernel.set_compositional_synthesis(True)
            failed_id = kernel.open_goal(goal(True), budget=5)
            kernel.think(40)
            failed = kernel.cognitive_snapshot()['goals'][str(failed_id)]
            assert failed['status'] == 'WITHHOLD', failed
            learned_id = kernel.open_goal(goal(), budget=5)
            kernel.think(40)
            learned = kernel.cognitive_snapshot()['goals'][str(learned_id)]
            assert learned['status'] == 'VALIDATED_ON_HOLDOUT', learned
            sid = kernel.start_development(budget=10, max_goals=2)
            kernel.develop(60)
            session = kernel.development_snapshot()['sessions'][sid]
            assert not session['selections'], session
            save(out / 'journal.json', journal(kernel))
            save(out / 'summary.json', {'status': 'REPRODUCED_MEMORY_RETRY_DISCONNECT',
                 'identity': kernel.identity, 'failed_goal': failed, 'learned_goal': learned,
                 'development': session, 'state_verification': kernel.verify_state()})
        finally:
            kernel.close()
        return
    from successor.continuity import prepare_upgrade
    parent = json.loads(Path(args.manifest).read_text())
    updates = {name: {'previous_sha256': digest, 'current_sha256': file_sha(ROOT / name)}
               for name, digest in parent['inherited_files'].items() if file_sha(ROOT / name) != digest}
    upgraded = prepare_upgrade(args.manifest, args.state, out / 'birth', source_updates=updates)
    kernel = SuccessorKernel(upgraded['manifest'], upgraded['state'])
    try:
        prefix = journal(kernel)[:-1]
        old_goals = kernel.cognitive_snapshot()['goals']
        sid = kernel.start_development(budget=10, max_goals=2)
        kernel.develop(60)
        session = kernel.development_snapshot()['sessions'][sid]
        assert len(session['selections']) == 1 and len(session['outcomes']) == 1, session
        assert session['outcomes'][0]['status'] == 'VALIDATED_ON_HOLDOUT', session
        child = kernel.cognitive_snapshot()['goals'][str(session['outcomes'][0]['goal_id'])]
        assert child['result']['predictions'] == [{'total': 48}], child
        assert child['result']['parent_source_sha256'], child
        assert journal(kernel)[:len(prefix)] == prefix
        assert all(kernel.cognitive_snapshot()['goals'][key] == value for key, value in old_goals.items())
        identity = kernel.identity
        save(out / 'source-updates.json', updates)
        save(out / 'candidate.json', child['result'])
        verification = kernel.verify_state()
    finally:
        kernel.close()
    kernel = SuccessorKernel(upgraded['manifest'], upgraded['state'])
    try:
        assert kernel.verify_state() == verification
        idle = kernel.start_development(budget=10, max_goals=2)
        kernel.develop(60)
        assert not kernel.development_snapshot()['sessions'][idle]['selections']
        save(out / 'journal.json', journal(kernel))
        save(out / 'summary.json', {'status': 'PASS_VERIFIED_MEMORY_DEVELOPMENT_CONTINUATION',
             'operational_identity': identity, 'inherited_events': len(prefix),
             'predecessor_events_unchanged': True, 'predecessor_results_unchanged': True,
             'restart_verified': True, 'redundant_retry_count': 0,
             'development': session, 'query_predictions': child['result']['predictions'],
             'parent_sources': child['result']['parent_source_sha256'],
             'state_verification': kernel.verify_state(),
             'controller_and_fixtures_authorship': 'MAINTAINER',
             'program_and_retry_selection': 'YADO', 'consciousness_established': False})
    finally:
        kernel.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('parent', 'resume'), required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--output', required=True)
    run(parser.parse_args())
