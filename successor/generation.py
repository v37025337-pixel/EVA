"""Memory-derived, executable component generations above the pinned G2 core.

The assistant supplies adapters and admission contracts. The kernel retrieves
historical gene expressions, measures them, recombines winners and activates a
durable successor profile. This is bounded component evolution, not a G3 claim.
Archived PASS labels never participate in admission.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
import json
import math
from pathlib import Path
import secrets
import sqlite3
from contextlib import closing

from .archive import ExperienceArchive, canonical, file_sha, sha
from .kernel import ROOT, SuccessorKernel, decode, encode, equivalent, fingerprint
from .generation_tasks import ORGANS, challenge

GENOME_SOURCE = 'runtime/yado_evolutionary_genome_v1.py'
LINEAGE_SOURCE = 'runtime/yado_evolutionary_multigeneration_lineage_v1.py'
GENOME_RECEIPT = 'candidates/kernel-self-generated/g2-evolutionary-genome-v1.json'
LINEAGE_RECEIPT = 'candidates/kernel-self-generated/g2-evolutionary-multigeneration-lineage-v1.json'

# Reviewed predecessor from main 05488e8d. Compatibility is restricted to
# this implementation, never to source hashes supplied by an arbitrary journal.
LEGACY_SOURCES = {
    'successor/generation.py': '895170e691d8c637358b91dc0c7d6669998682ac206d89b5c81338062f2096f4',
    'successor/generation_tasks.py': '4ab843e44b10a7da28ff0609e7781cf0231edd42414f8433358ebfd4b3b409b5',
    GENOME_SOURCE: '186479a62f08662a767c47dffcf499f3294eaaecefd21327dbdccc012ed08531',
    LINEAGE_SOURCE: 'a471c4a4c53044db94f482ad7d6f2c4758bad3f9d60c68f2252b88759b7a1cc3',
}

# Exact last implementation before the reviewed genome-fitness maintenance.
# These are immutable history pins, not aliases for whichever files are live.
PRE_MAINTENANCE_SOURCES = {
    **LEGACY_SOURCES,
    'successor/generation.py': 'f5bf60db4e90cd4a7fdc1ff256616365b1767d853f0d53337c242321f12b2c1f',
}
SOURCE_TRANSITION = 'GENOME_FITNESS_BINDING_MAINTENANCE_V1'
REVIEWED_GENOME_SHA256 = '65400f0aadce57e21d8c2c97e7f89e76c6d085ef934fcaab2765ff9c1f8c5f8c'


def sources():
    paths = (GENOME_SOURCE, LINEAGE_SOURCE, 'successor/generation.py', 'successor/generation_tasks.py')
    return {p: file_sha(ROOT / p) for p in paths}


def reviewed_upgrade_sources(previous):
    """Authorize only the named, inspected runtime change; never arbitrary pins."""
    if previous not in (LEGACY_SOURCES, PRE_MAINTENANCE_SOURCES):
        raise ValueError('GENERATION_UNREVIEWED_PREDECESSOR')
    current = sources()
    expected = {**PRE_MAINTENANCE_SOURCES, GENOME_SOURCE: REVIEWED_GENOME_SHA256,
                'successor/generation.py': current.get('successor/generation.py')}
    if current != expected:
        raise ValueError('GENERATION_UNREVIEWED_CURRENT_SOURCES')
    return current


def _source_transition(previous, current, transition):
    if transition is None:
        # Preserve the original offline-retention repair event byte-for-byte.
        return previous == LEGACY_SOURCES and current == PRE_MAINTENANCE_SOURCES
    return (transition == SOURCE_TRANSITION
            and previous in (LEGACY_SOURCES, PRE_MAINTENANCE_SOURCES)
            and current == reviewed_upgrade_sources(previous))


def inventory(archive):
    refs = {k: v for k, v in archive.summary['refs'].items() if k.startswith('refs/remotes/origin/')}
    rows = []
    for ref, tip in sorted(refs.items()):
        count = archive.db.execute('SELECT count(*) FROM branch_files WHERE ref=?', (ref,)).fetchone()[0]
        rows.append({'ref': ref, 'commit': tip, 'files': count})
    return rows


def discover(archive, *, source_pins=None):
    """Only known typed adapters over byte-matched inherited code may execute."""
    current = sources()
    expected = current if source_pins is None else source_pins
    if expected not in (LEGACY_SOURCES, PRE_MAINTENANCE_SOURCES, current):
        raise ValueError('GENERATION_UNREVIEWED_DISCOVERY_SOURCES')
    reviewed_current = (current == {**PRE_MAINTENANCE_SOURCES,
        'successor/generation.py': current.get('successor/generation.py'),
        GENOME_SOURCE: REVIEWED_GENOME_SHA256})
    found = {}
    for ref in (x['ref'] for x in inventory(archive)):
        for receipt, source, family in ((GENOME_RECEIPT, GENOME_SOURCE, 'genome'),
                                        (LINEAGE_RECEIPT, LINEAGE_SOURCE, 'lineage')):
            rows = archive.db.execute('''SELECT b.path,o.digest FROM branch_files b JOIN git_objects o
                ON b.oid=o.oid WHERE b.ref=? AND b.path IN (?,?)''', (ref, receipt, source)).fetchall()
            blobs = {r['path']: r['digest'] for r in rows}
            accepted = {expected[source]}
            if reviewed_current and expected == current and source == GENOME_SOURCE:
                # Reuse descriptors from the exact reviewed predecessor. The
                # repaired typed adapter remeasures them; archived code/PASS
                # never executes or authorizes admission.
                accepted.add(PRE_MAINTENANCE_SOURCES[source])
            if receipt not in blobs or source not in blobs or blobs[source] not in accepted:
                continue
            # Reading rechecks decompression and SHA. Historical code is never imported.
            archive.read(blobs[source])
            obj = json.loads(archive.read(blobs[receipt]))
            genomes = ([obj['evolution_run']['child']] if family == 'genome'
                       else [item['genome'] for item in obj['lineage']])
            for index, genome in enumerate(genomes):
                for organ, gene in genome['chromosomes'].items():
                    if organ not in ORGANS:
                        continue
                    option = {'family': family, 'expression': gene['expression'], 'organ': organ}
                    validate_option(option)
                    key = fingerprint(option)
                    item = found.setdefault(key, {**option, 'option_digest': key, 'evidence': []})
                    proof = {'ref': ref, 'receipt_digest': blobs[receipt],
                        'source_digest': blobs[source], 'source': source, 'genome_index': index}
                    if blobs[source] != expected[source]:
                        proof.update(source_transition=SOURCE_TRANSITION,
                                     current_source_digest=expected[source])
                    item['evidence'].append(proof)
    if len(found) > 32:
        raise ValueError('GENERATION_OPTION_BUDGET')
    return sorted(found.values(), key=lambda x: x['option_digest'])


def validate_option(option):
    if option.get('organ') not in ORGANS or option.get('family') not in ('parent', 'genome', 'lineage'):
        raise ValueError('GENERATION_UNKNOWN_COMPONENT')
    e, organ, family = option['expression'], option['organ'], option['family']
    if family == 'parent':
        if e != {}:
            raise ValueError('GENERATION_PARENT_EXPRESSION')
        return
    if organ == 'THINKING':
        if family == 'genome':
            valid = e == {'latency_tiebreak': True}
        else:
            valid = (set(e) == {'objectives'} and isinstance(e['objectives'], list)
                     and 1 <= len(e['objectives']) <= 3
                     and len(set(e['objectives'])) == len(e['objectives'])
                     and set(e['objectives']) <= {'latency', 'risk', 'uncertainty'})
    else:
        key = {'LOGIC': 'max_width', 'INTELLIGENCE': 'max_trigger_width', 'CODE': 'max_degree'}[organ]
        valid = (type(e.get(key)) is int and 1 <= e[key] <= 5
                 and set(e) <= {key, 'candidate_generator'})
    if not valid:
        raise ValueError('GENERATION_EXPRESSION_OUTSIDE_ADAPTER_GRAMMAR')


def parent_profile():
    return {organ: {'organ': organ, 'family': 'parent', 'expression': {}} for organ in ORGANS}


def execute_component(option, task):
    """Fit on training only, freeze the model/source, then evaluate query inputs."""
    validate_option(option)
    if task.get('organ') != option['organ']:
        raise ValueError('GENERATION_TASK_ORGAN')
    from yado_evolutionary_genome_v1 import (LogicDNFGeneV1, LatencyAwarePlannerGeneV1,
        TripleTriggerRouterGeneV1, PolynomialReturnRepairGeneV1,
        BudgetAdaptiveCompositionalLogicV2, WorkBudgetAdaptiveContingentPlannerV2,
        CoveragePrunedCompositionalSchemaRouterV3, ContingentStage, AmbiguityAwareProgramRepairV11)
    from yado_evolutionary_multigeneration_lineage_v1 import (BooleanDNFLineageGene,
        TriggerRouterLineageGene, PlannerLineageGene, PolynomialCodeLineageGene)
    family, organ, e = option['family'], option['organ'], option['expression']
    if organ == 'THINKING':
        stages = task['stages']
        if not isinstance(stages, list) or len(stages) > 8:
            raise ValueError('GENERATION_STAGE_BUDGET')
        numbers = [task[k] for k in ('current', 'target', 'budget')]
        numbers += [s.get(k, 0) for s in stages for k in ('cost', 'expected_gain', 'latency', 'risk', 'uncertainty')]
        if any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 10000 for x in numbers):
            raise ValueError('GENERATION_PLAN_NUMBER_BUDGET')
        ids = [s['stage_id'] for s in stages]
        if any(type(x) is not str or len(x) > 80 for x in ids) or len(set(ids)) != len(ids):
            raise ValueError('GENERATION_STAGE_ID_CONTRACT')
        args = (task['current'], task['target'], task['budget'])
        if family == 'lineage':
            result = PlannerLineageGene.plan(*args, stages, e['objectives'])
        else:
            cls = WorkBudgetAdaptiveContingentPlannerV2 if family == 'parent' else LatencyAwarePlannerGeneV1
            result = asdict(cls.plan(*args, [ContingentStage(**s) for s in stages], task.get('completed', ())))
        return {'answer': result['action'], 'artifact': result, 'artifact_digest': fingerprint(result)}
    train, queries = task['training'], task['queries']
    if not isinstance(train, list) or not 1 <= len(train) <= 256 or not isinstance(queries, list) or len(queries) > 128:
        raise ValueError('GENERATION_EXAMPLE_BUDGET')
    if organ == 'CODE':
        if len(task['source']) > 16_000 or any(len(row[0]) != 1 for row in train):
            raise ValueError('GENERATION_SOURCE_CONTRACT')
        numbers = [x for args, expected in train for x in [*args, expected]] + [x for args in queries for x in args]
        if any(type(x) is not int or abs(x) > 10**12 for x in numbers) or any(len(x) != 1 for x in queries):
            raise ValueError('GENERATION_INTEGER_SOURCE_BUDGET')
        examples = [(tuple(args), expected) for args, expected in train]
        if family == 'parent':
            result = AmbiguityAwareProgramRepairV11.repair(task['source'], task['function'], examples, max_candidates=1000)
        elif family == 'genome':
            result = PolynomialReturnRepairGeneV1.synthesize(task['source'], task['function'], examples)
        else:
            result = PolynomialCodeLineageGene.synthesize(task['source'], task['function'], examples, e['max_degree'])
        if not result.get('source'):
            raise ValueError('GENERATION_NO_SOURCE_CANDIDATE')
        frozen = fingerprint(result)
        answers = [AmbiguityAwareProgramRepairV11.execute(result['source'], task['function'], tuple(x)) for x in queries]
        return {'answer': answers, 'artifact': result, 'artifact_digest': frozen}
    if any(not isinstance(r.get('input'), dict) or len(r['input']) > 8 for r in train):
        raise ValueError('GENERATION_FIELD_BUDGET')
    if any(type(v) is not bool for row in train for v in row['input'].values()):
        raise ValueError('GENERATION_BOOLEAN_INPUT_REQUIRED')
    if any(not isinstance(q, dict) or len(q) > 8 or any(type(v) is not bool for v in q.values()) for q in queries):
        raise ValueError('GENERATION_BOOLEAN_QUERY_REQUIRED')
    if organ == 'LOGIC':
        if family == 'parent':
            model = BudgetAdaptiveCompositionalLogicV2.learn_symmetric_boolean(train)
            predict = BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean
        else:
            cls = LogicDNFGeneV1 if family == 'genome' else BooleanDNFLineageGene
            model, predict = cls.fit(train, max_width=e['max_width']), cls.predict
    else:
        if family == 'parent':
            cls = CoveragePrunedCompositionalSchemaRouterV3
            model = cls.fit(train, task['fallback'])
        elif family == 'genome':
            cls = TripleTriggerRouterGeneV1
            model = cls.fit(train, task['fallback'], e['max_trigger_width'])
        else:
            cls = TriggerRouterLineageGene
            model = cls.fit(train, task['fallback'], e['max_trigger_width'])
        predict = cls.route
    frozen = fingerprint(model)
    return {'answer': [predict(model, x) for x in queries], 'artifact': model, 'artifact_digest': frozen}


def evaluate(profile, cases):
    outcomes = []
    for task, expected in cases:
        try:
            result = execute_component(profile[task['organ']], task)
            passed = equivalent(result['answer'], expected)
            outcomes.append({'organ': task['organ'], 'task_digest': fingerprint(task),
                'expected': expected, 'result': result, 'passed': bool(passed)})
        except Exception as error:
            outcomes.append({'organ': task['organ'], 'task_digest': fingerprint(task),
                'expected': expected, 'error': type(error).__name__ + ':' + str(error), 'passed': False})
    scores = {organ: sum(x['passed'] for x in outcomes if x['organ'] == organ) /
              sum(1 for x in outcomes if x['organ'] == organ) for organ in ORGANS
              if any(x['organ'] == organ for x in outcomes)}
    return {'scores': scores, 'outcomes': outcomes, 'cases_digest': fingerprint(cases)}


def select(options, cases, retention):
    """Recombine the smallest non-regressing winners; no historical verdicts."""
    profile, evidence = parent_profile(), []
    for organ in ORGANS:
        dev = [c for c in cases if c[0]['organ'] == organ]
        protected = [c for c in retention if c[0]['organ'] == organ]
        baseline = evaluate(profile, dev)['scores'][organ]
        parent_checks = evaluate(profile, protected)['outcomes']
        choices = []
        for option in [o for o in options if o['organ'] == organ]:
            probe = {**profile, organ: option}
            measured, retained = evaluate(probe, dev), evaluate(probe, protected)
            regressions = [i for i, (p, c) in enumerate(zip(parent_checks, retained['outcomes'])) if p['passed'] and not c['passed']]
            score = measured['scores'][organ]
            evidence.append({'option_digest': option['option_digest'], 'organ': organ,
                'development': measured, 'retention': retained, 'regressions': regressions})
            if score > baseline and not regressions:
                complexity = sum(v if type(v) is int else len(v) if isinstance(v, list) else 1
                                 for v in option['expression'].values())
                choices.append((-score, complexity, option['option_digest'], option))
        if choices:
            profile[organ] = min(choices, key=lambda x: x[:3])[3]
    return profile, evidence


def retained_memory(kernel, through_tick=None):
    """Re-execute learned results; rejected goals stay rejected, never relabelled."""
    from .cognitive import CognitiveLoop, replay
    loop = CognitiveLoop(kernel)
    goals = replay([r for r in loop._records() if through_tick is None or r['tick'] <= through_tick])
    checks = []
    for goal in goals.values():
        if goal['status'] == 'ACTIVE':
            raise ValueError('GENERATION_REQUIRES_IDLE_COGNITION')
        if goal['status'] in ('WITHHOLD', 'STOPPED'):
            checks.append({'goal_id': goal['id'], 'status': goal['status'], 'retained': True, 'scope': 'REJECTION_PRESERVED'})
            continue
        replayed = copy.deepcopy(goal)
        if goal['spec']['domain'] == 'library_discovery':
            # This is historical retention, not fresh package discovery. Replay
            # already verified the saved candidate/proof binding. Verify that
            # exact frozen observation again without consulting today's PyPI.
            check = loop._verify(replayed, recorded_verification=goal['verification'])
            checks.append({'goal_id': goal['id'], 'status': goal['status'], 'retained': check['passed'],
                           'scope': check['scope'], 'checks': check['checks']})
            continue
        if goal['spec']['domain'] == 'native_source' and goal['decision']['choice']['strategy'] == 'reuse_verified_source':
            # The original admitted program is re-executed. This is retention
            # of a learned result, not a rerun of its historical selection.
            result = copy.deepcopy(goal['result'])
            for part in ('training', 'validation', 'queries'):
                key = 'predictions' if part == 'queries' else part + '_predictions'
                result[key] = kernel.parent.execute_native_source(result, [r['input'] for r in goal['spec'][part]])
            replayed['execution'] = {**goal['execution'], 'result': result}
        else:
            replayed['execution'] = {**loop._execute(goal), 'tick': goal['execution']['tick']}
        check = loop._verify(replayed)
        checks.append({'goal_id': goal['id'], 'status': goal['status'], 'retained': check['passed'],
            'scope': check['scope'], 'checks': check['checks']})
    return {'goals': len(checks), 'passed': all(x['retained'] for x in checks), 'checks': checks}


class GenerationKernel:
    """A separate, source-pinned journal preserves the inherited kernel identity."""
    def __init__(self, kernel, archive_path, state):
        self.kernel = kernel
        parent_path = kernel.db.execute('PRAGMA database_list').fetchone()[2]
        if Path(state).resolve() in (Path(parent_path).resolve(), Path(archive_path).resolve()):
            raise ValueError('GENERATION_REQUIRES_SEPARATE_STATE')
        self.archive = ExperienceArchive(archive_path)
        self.db = sqlite3.connect(state, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events(tick INTEGER PRIMARY KEY,body TEXT NOT NULL,hash TEXT NOT NULL)')
        self._verified_replays = set()
        try:
            if not self.db.execute('SELECT 1 FROM events LIMIT 1').fetchone():
                self._append({'kind': 'BIRTH', 'sources': sources(), 'parent_identity': kernel.identity,
                    'parent_state': kernel.verify_state(), 'archive_sha256': file_sha(archive_path),
                    'branches': inventory(self.archive), 'scope': 'EXECUTABLE_COMPONENT_GENERATIONS',
                    'canonical_generation': kernel.parent_audit['generation']})
            self.birth = self.records()[0]
            self.pinned_sources = self._source_lineage(self.records())
            if (self.birth['kind'] != 'BIRTH' or self.pinned_sources != sources() or self.birth['parent_identity'] != kernel.identity
                    or self.birth['archive_sha256'] != file_sha(archive_path)
                    or self.birth['branches'] != inventory(self.archive)):
                raise ValueError('GENERATION_SOURCE_OR_LINEAGE_DRIFT')
            parent = self.birth['parent_state']
            row = kernel.db.execute('SELECT event_hash FROM events WHERE tick=?', (parent['tick'],)).fetchone()
            if parent['tick'] and (row is None or row[0] != parent['event_hash']):
                raise ValueError('GENERATION_PARENT_MEMORY_DRIFT')
            self.snapshot()
        except BaseException:
            self.close()
            raise

    def close(self):
        self.db.close()
        self.archive.close()

    def _append(self, body):
        row = self.db.execute('SELECT tick,hash FROM events ORDER BY tick DESC LIMIT 1').fetchone()
        tick, previous = (row[0] + 1, row[1]) if row else (1, '0' * 64)
        raw = encode(body)
        digest = sha((previous + '\n' + str(tick) + '\n' + raw).encode())
        self.db.execute('INSERT INTO events VALUES(?,?,?)', (tick, raw, digest))
        return {**body, 'tick': tick, 'event_hash': digest}

    def records(self):
        previous, records = '0' * 64, []
        for tick, raw, digest in self.db.execute('SELECT tick,body,hash FROM events ORDER BY tick'):
            if tick != len(records) + 1 or sha((previous + '\n' + str(tick) + '\n' + raw).encode()) != digest:
                raise ValueError('GENERATION_HISTORY_INTEGRITY')
            records.append({**decode(raw), 'tick': tick, 'event_hash': digest})
            previous = digest
        return records

    def _check_parent_state(self, state):
        tick = state.get('tick')
        if type(tick) is not int or tick < 0 or state.get('status') != 'PASS':
            raise ValueError('GENERATION_PARENT_MEMORY_DRIFT')
        row = self.kernel.db.execute('SELECT event_hash FROM events WHERE tick=?', (tick,)).fetchone()
        if state.get('event_hash') != (row[0] if row else '0' * 64) or (tick and row is None):
            raise ValueError('GENERATION_PARENT_MEMORY_DRIFT')

    def _source_lineage(self, records):
        pinned = records[0]['sources']
        parent_tick = records[0]['parent_state']['tick']
        for index, row in enumerate(records[1:], 1):
            if row['kind'] != 'SOURCE_UPGRADE':
                continue
            if (row['previous_sources'] != pinned
                    or not _source_transition(pinned, row['sources'], row.get('transition_id'))
                    or row['predecessor_tick'] != records[index - 1]['tick']
                    or row['predecessor_event_hash'] != records[index - 1]['event_hash']):
                raise ValueError('GENERATION_SOURCE_UPGRADE_PROVENANCE')
            self._check_parent_state(row['parent_state'])
            if row['parent_state']['tick'] < parent_tick:
                raise ValueError('GENERATION_SOURCE_UPGRADE_MEMORY_BOUNDARY')
            pinned, parent_tick = row['sources'], row['parent_state']['tick']
        return pinned

    def snapshot(self):
        records = self.records()
        if self._source_lineage(records) != sources():
            raise ValueError('GENERATION_SOURCE_DRIFT')
        profile, generation, proposal, admission, activated = parent_profile(), 0, None, None, False
        upgrade, readmission, execution_admitted = None, None, True
        event_sources = self.birth['sources']
        for row in records[1:]:
            if row['kind'] == 'PROPOSE':
                if proposal is not None or row['profile_digest'] != fingerprint(row['profile']):
                    raise ValueError('GENERATION_PROPOSAL_PROVENANCE')
                if row['event_hash'] not in self._verified_replays:
                    options = discover(self.archive, source_pins=event_sources)
                    seed = self.birth['parent_state']['event_hash']
                    chosen, evidence = select(options, challenge(seed), challenge(seed, retention=True))
                    if (row['options'] != options or row['development_seed'] != seed
                            or row['profile'] != chosen or row['selection_evidence'] != evidence):
                        raise ValueError('GENERATION_SELECTION_NOT_REPRODUCIBLE')
                    self._verified_replays.add(row['event_hash'])
                proposal = row
            elif row['kind'] == 'ADMISSION':
                if (proposal is None or admission is not None or row['proposal_tick'] != proposal['tick']
                        or row['profile_digest'] != proposal['profile_digest']
                        or row['passed'] != admission_passed(row)):
                    raise ValueError('GENERATION_ADMISSION_PROVENANCE')
                if row['event_hash'] not in self._verified_replays:
                    cases, protected = challenge(row['fresh_seed']), challenge(row['fresh_seed'], retention=True)
                    expected = {'parent': evaluate(parent_profile(), cases),
                        'child': evaluate(proposal['profile'], cases),
                        'parent_retention': evaluate(parent_profile(), protected),
                        'child_retention': evaluate(proposal['profile'], protected),
                        'inherited_memory': retained_memory(self.kernel, self.birth['parent_state']['tick'])}
                    if any(row[k] != v for k, v in expected.items()):
                        raise ValueError('GENERATION_ADMISSION_NOT_REPRODUCIBLE')
                    self._verified_replays.add(row['event_hash'])
                admission = row
            elif row['kind'] == 'ACTIVATE':
                if (admission is None or not admission['passed'] or activated
                        or row['admission_tick'] != admission['tick']
                        or row['profile_digest'] != proposal['profile_digest']):
                    raise ValueError('GENERATION_ACTIVATION_WITHOUT_ADMISSION')
                profile, generation = proposal['profile'], 1
                activated = True
            elif row['kind'] == 'ROLLBACK':
                if generation != 1:
                    raise ValueError('GENERATION_ROLLBACK_WITHOUT_CHILD')
                profile, generation = parent_profile(), 0
            elif row['kind'] == 'EXECUTE':
                if not execution_admitted:
                    raise ValueError('GENERATION_REQUIRES_READMISSION')
                if row['profile_digest'] != fingerprint(profile) or row['generation'] != generation:
                    raise ValueError('GENERATION_EXECUTION_WRONG_PROFILE')
            elif row['kind'] == 'SOURCE_UPGRADE':
                upgrade, readmission, execution_admitted = row, None, False
                event_sources = row['sources']
            elif row['kind'] == 'READMISSION':
                if (upgrade is None or readmission is not None or proposal is None
                        or row['upgrade_tick'] != upgrade['tick']
                        or row['proposal_tick'] != proposal['tick']
                        or row['profile_digest'] != fingerprint(profile)
                        or row['passed'] != admission_passed(row)
                        or row['parent_state']['tick'] < upgrade['parent_state']['tick']):
                    raise ValueError('GENERATION_READMISSION_PROVENANCE')
                self._check_parent_state(row['parent_state'])
                if row['event_hash'] not in self._verified_replays:
                    cases, protected = challenge(row['fresh_seed']), challenge(row['fresh_seed'], retention=True)
                    expected = self._measure(profile, cases, protected, row['parent_state']['tick'], proposal)
                    if any(row[k] != v for k, v in expected.items()):
                        raise ValueError('GENERATION_READMISSION_NOT_REPRODUCIBLE')
                    self._verified_replays.add(row['event_hash'])
                readmission, execution_admitted = row, row['passed']
            else:
                raise ValueError('GENERATION_UNKNOWN_EVENT')
        return {'component_generation': generation, 'profile': profile, 'profile_digest': fingerprint(profile),
            'execution_admitted': execution_admitted,
            'readmission_passed': None if readmission is None else readmission['passed'],
            'events': len(records), 'event_hash': records[-1]['event_hash'],
            'remote_branches': len(self.birth['branches']), 'canonical_generation': self.birth['canonical_generation'],
            'formal_g3_transition': False, 'consciousness_established': False, 'background_process_running': False}

    def _transaction(self, operation):
        self.kernel._check_sources()
        if self.pinned_sources != sources():
            raise ValueError('GENERATION_SOURCE_DRIFT')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.snapshot()
            result = operation()
            self.db.execute('COMMIT')
            return result
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def propose(self):
        return self._transaction(self._propose)

    def _propose(self):
        if any(r['kind'] == 'PROPOSE' for r in self.records()):
            raise ValueError('GENERATION_PROPOSAL_ALREADY_FROZEN')
        options = discover(self.archive)
        seed = self.birth['parent_state']['event_hash']
        profile, evidence = select(options, challenge(seed), challenge(seed, retention=True))
        return self._append({'kind': 'PROPOSE', 'profile': profile, 'profile_digest': fingerprint(profile),
            'options': options, 'selection_evidence': evidence, 'development_seed': seed,
            'controller_authorship': 'ASSISTANT', 'selection': 'KERNEL_MEASURED_COMPONENT_RECOMBINATION'})

    def admit(self):
        return self._transaction(self._admit)

    def _admit(self):
        records = self.records()
        if any(r['kind'] == 'ADMISSION' for r in records):
            raise ValueError('GENERATION_ADMISSION_ALREADY_COMPLETED')
        proposal = next((r for r in records if r['kind'] == 'PROPOSE'), None)
        if proposal is None:
            raise ValueError('GENERATION_REQUIRES_FROZEN_PROPOSAL')
        # Generated only after durable source/profile freeze; no reselection.
        seed = secrets.token_hex(16)
        cases, protected = challenge(seed), challenge(seed, retention=True)
        parent, child = parent_profile(), proposal['profile']
        row = {'kind': 'ADMISSION', 'proposal_tick': proposal['tick'], 'profile_digest': proposal['profile_digest'],
            'fresh_seed': seed, 'parent': evaluate(parent, cases), 'child': evaluate(child, cases),
            'parent_retention': evaluate(parent, protected), 'child_retention': evaluate(child, protected),
            'inherited_memory': retained_memory(self.kernel, self.birth['parent_state']['tick']),
            'memory_ablation': fingerprint(select([], challenge(proposal['development_seed']),
                challenge(proposal['development_seed'], retention=True))[0]) == fingerprint(parent),
            'canonical_audit': self.kernel.parent.audit()['pass']}
        row['passed'] = admission_passed(row)
        admission = self._append(row)
        if row['passed']:
            self._append({'kind': 'ACTIVATE', 'admission_tick': admission['tick'],
                          'profile_digest': proposal['profile_digest']})
        return admission

    def execute(self, task):
        return self._transaction(lambda: self._execute(task))

    def _execute(self, task):
        snapshot = self.snapshot()
        if not snapshot['execution_admitted']:
            raise ValueError('GENERATION_REQUIRES_READMISSION')
        result = execute_component(snapshot['profile'][task['organ']], copy.deepcopy(task))
        return self._append({'kind': 'EXECUTE', 'generation': snapshot['component_generation'],
            'profile_digest': snapshot['profile_digest'], 'task': task, 'result': result,
            'status': 'EXECUTED_REQUIRES_INDEPENDENT_CHECK'})

    def _measure(self, profile, cases, protected, through_tick, proposal):
        return {'parent': evaluate(parent_profile(), cases), 'child': evaluate(profile, cases),
            'parent_retention': evaluate(parent_profile(), protected),
            'child_retention': evaluate(profile, protected),
            'inherited_memory': retained_memory(self.kernel, through_tick),
            'memory_ablation': fingerprint(select([], challenge(proposal['development_seed']),
                challenge(proposal['development_seed'], retention=True))[0]) == fingerprint(parent_profile()),
            'canonical_audit': self.kernel.parent.audit()['pass']}

    def readmit(self):
        return self._transaction(self._readmit)

    def _readmit(self):
        records, state = self.records(), self.snapshot()
        upgrades = [r for r in records if r['kind'] == 'SOURCE_UPGRADE']
        proposal = next((r for r in records if r['kind'] == 'PROPOSE'), None)
        if (not upgrades or proposal is None
                or any(r['kind'] == 'READMISSION' and r['upgrade_tick'] == upgrades[-1]['tick'] for r in records)):
            raise ValueError('GENERATION_READMISSION_NOT_AVAILABLE')
        seed, parent_state = secrets.token_hex(16), self.kernel.verify_state()
        row = {'kind': 'READMISSION', 'upgrade_tick': upgrades[-1]['tick'],
            'proposal_tick': proposal['tick'], 'profile_digest': state['profile_digest'],
            'parent_state': parent_state, 'fresh_seed': seed,
            **self._measure(state['profile'], challenge(seed), challenge(seed, retention=True),
                            parent_state['tick'], proposal)}
        row['passed'] = admission_passed(row)
        return self._append(row)

    def rollback(self):
        return self._transaction(self._rollback)

    def _rollback(self):
        if self.snapshot()['component_generation'] != 1:
            raise ValueError('GENERATION_NO_ACTIVE_CHILD')
        return self._append({'kind': 'ROLLBACK', 'reason': 'EXPLICIT_ROLLBACK'})


def upgrade_component_state(kernel, archive_path, predecessor_state, output):
    """Copy a reviewed journal, append provenance, and require fresh admission.

    Both the predecessor's events and source pins remain unchanged. Opening the
    result recomputes the historical proposal/admission under offline retention.
    """
    predecessor, output = Path(predecessor_state).resolve(), Path(output).resolve()
    if output.exists() or not predecessor.is_file():
        raise ValueError('GENERATION_UPGRADE_REQUIRES_NEW_OUTPUT')
    output.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(predecessor.as_uri() + '?mode=ro', uri=True)) as old:
        with closing(sqlite3.connect(output)) as new:
            old.backup(new)
    holder = GenerationKernel.__new__(GenerationKernel)
    holder.kernel = kernel
    holder.db = sqlite3.connect(output, isolation_level=None)
    try:
        holder.db.execute('PRAGMA journal_mode=DELETE')
        holder.db.execute('PRAGMA synchronous=FULL')
        records = holder.records()
        if not records:
            raise ValueError('GENERATION_UNREVIEWED_PREDECESSOR')
        previous = holder._source_lineage(records)
        current = reviewed_upgrade_sources(previous)
        last = records[-1]
        holder._append({'kind': 'SOURCE_UPGRADE', 'transition_id': SOURCE_TRANSITION,
            'previous_sources': previous, 'sources': current, 'predecessor_tick': last['tick'],
            'predecessor_event_hash': last['event_hash'], 'parent_state': kernel.verify_state()})
    finally:
        holder.db.close()
    migrated = GenerationKernel(kernel, archive_path, output)
    try:
        return migrated.snapshot()
    finally:
        migrated.close()


def admission_passed(row):
    parent, child = row['parent']['scores'], row['child']['scores']
    if set(parent) != set(ORGANS) or set(child) != set(ORGANS):
        return False
    protected = list(zip(row['parent_retention']['outcomes'], row['child_retention']['outcomes']))
    return bool(row['canonical_audit'] and row['memory_ablation'] and row['inherited_memory']['passed']
        and all(child[k] >= parent[k] for k in ORGANS) and all(child[k] == 1 for k in ORGANS)
        and sum(child[k] > parent[k] for k in ORGANS) >= 2
        and len(protected) == len(row['parent_retention']['outcomes'])
        and all(not p['passed'] or c['passed'] for p, c in protected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('propose', 'admit', 'readmit', 'status', 'execute', 'rollback'))
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--kernel-state', required=True)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--generation-state', required=True)
    parser.add_argument('--input')
    args = parser.parse_args()
    kernel = SuccessorKernel(args.manifest, args.kernel_state)
    kernel.db.execute('PRAGMA journal_mode=DELETE')
    try:
        generation = GenerationKernel(kernel, args.archive, args.generation_state)
        try:
            if args.command == 'status':
                result = generation.snapshot()
            elif args.command == 'execute':
                result = generation.execute(json.loads(Path(args.input).read_text()))
            else:
                result = getattr(generation, args.command)()
            print(encode(result))
        finally:
            generation.close()
    finally:
        kernel.close()


if __name__ == '__main__':
    main()
