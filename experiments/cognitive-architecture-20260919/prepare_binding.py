"""Prepare an uncommitted canonical maintenance binding from the current HEAD."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'runtime'))
from yado_evolution_ledger_v2 import event_hash, validate_ledger_v2

UPGRADE = 'YADO_UNIFIED_COGNITIVE_DEVELOPMENT_BINDING_V1'
REPORT = 'experiments/cognitive-architecture-20260919/cognitive-verification.json'

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()

def file_sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

def base(relative):
    return json.loads(subprocess.check_output(['git', 'show', '81e61776a3702d0f7566e44ed7dae6c4ebb3fdef:' + relative], cwd=ROOT))

def seal(value, key):
    value[key] = digest({k: v for k, v in value.items() if k != key})

def save(relative, value):
    (ROOT / relative).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')

core = base('canonical/yado-unified-core-v1.json')
head = base('canonical/yado-main-head-g2.json')
ledger = base('architecture/evolution-ledger.json')
contract = base('architecture/yado-unified-architecture-v2.json')
parent_head = head['canonical_head_digest']
metadata = {
    'id': UPGRADE,
    'continuation_entrypoint': 'experiments/repository-learning-resume-20260919/run.py',
    'development_entrypoint': 'successor.kernel.SuccessorKernel.develop_native_programs',
    'selection': 'EXISTING_KERNEL_SELECTORS_FROM_DURABLE_DEFICITS',
    'rounds_per_campaign': 3,
    'endogenous_cycles_per_campaign': 20,
    'predecessor_checkpoint_run': 35453219380,
    'predecessor_tick': 1142,
    'public_web_modules': [
        'runtime/yado_unified_core_self_directed_web_research_v1.py',
        'runtime/yado_unified_core_peer_systems_learning_v1.py',
        'runtime/yado_unified_core_external_dev_self_development_v1.py'],
    'cognitive_validation_modules': [
        'runtime/yado_relational_causal_logic_holdout_v1.py',
        'runtime/yado_thinking_contextual_holdout_v1.py',
        'runtime/yado_intelligence_transfer_holdout_v1.py',
        'runtime/yado_memory_experience_holdout_v1.py',
        'runtime/yado_cognitive_integration_holdout_v1.py'],
    'cognitive_validation_scope': 'SHADOW_BOUNDED_FIXED_SEED_REVALIDATION',
    'cognitive_report': REPORT,
    'integration_authorship': 'ASSISTANT_USER_AUTHORIZED',
    'general_capability_gain_proven': False,
    'automatic_canonical_promotion': False,
    'background_process_running': False,
}
contract['unified_cognitive_development'] = copy.deepcopy(metadata)
save('architecture/yado-unified-architecture-v2.json', contract)
for document in (core, head):
    document['unified_cognitive_development'] = copy.deepcopy(metadata)
    document['maintenance_history'].append(copy.deepcopy(document['maintenance']))
    document['maintenance'] = {**document['maintenance'], 'capability_upgrade': UPGRADE,
        'authorship': 'ASSISTANT_USER_AUTHORIZED_MODULE_BINDING_AND_CONTINUATION',
        'validation_report': REPORT, 'parent_main_commit': '81e61776a3702d0f7566e44ed7dae6c4ebb3fdef',
        'native_capability_gain_claimed': False, 'formal_generation_changed': False}
seeds = set(core['active_runtime_sources']) | set(metadata['public_web_modules']) | set(metadata['cognitive_validation_modules']) | {'runtime/yado_autonomous_deep_development_v1.py'}
roots, done, pending = [ROOT, ROOT/'runtime', ROOT/'runtime/yado_rc8_v36'], set(), list(seeds)
while pending:
    relative = pending.pop()
    if relative in done:
        continue
    path = ROOT / relative
    done.add(relative)
    for node in ast.walk(ast.parse(path.read_text())):
        imports, search = [], roots
        if isinstance(node, ast.Import):
            imports = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                anchor = path.parent
                for _ in range(node.level - 1):
                    anchor = anchor.parent
                search = [anchor]
            imports = [node.module or ''] + ['.'.join(filter(None, [node.module, alias.name]))
                                           for alias in node.names if alias.name != '*']
        for name in imports:
            for root in search:
                location = root.joinpath(*name.split('.')) if name else root
                found = next((p for p in (location.with_suffix('.py'), location/'__init__.py')
                              if p.is_file() and p.is_relative_to(ROOT)), None)
                if found:
                    pending.append(found.relative_to(ROOT).as_posix())
                    break
sources = {name: file_sha(name) for name in sorted(done)}
core['active_runtime_sources'] = sorted(sources)
core['runtime_integrity_manifest'].update(sources=sources, manifest_digest=digest(sources))
seal(core, 'core_digest')
save('canonical/yado-unified-core-v1.json', core)
head['unified_core'].update(core_digest=core['core_digest'],
                          runtime_integrity_manifest_digest=core['runtime_integrity_manifest']['manifest_digest'])
seal(head, 'canonical_head_digest')
save('canonical/yado-main-head-g2.json', head)
index = len(ledger['events'])
event = {'event_id': UPGRADE + '_MAINTENANCE_' + str(index), 'index': index,
         'parent_event_hash': ledger['tail_event_hash'], 'event_type': 'USER_AUTHORIZED_MAINTENANCE_BINDING',
         'generation': head['generation_id'], 'promotion_applied': False, 'canonical_mutation': True,
         'previous_head_digest': parent_head, 'new_head_digest': head['canonical_head_digest'],
         'implementation_id': head['implementation_id'], 'capability_upgrade': UPGRADE,
         'effect': 'BIND_EXISTING_WEB_AND_COGNITIVE_MODULES_AND_BOUNDED_DURABLE_DEVELOPMENT; NEXT=' + ledger['open_deficits'][0],
         'validation_required_before_main_merge': ['FULL_REGRESSION', 'FULL_KERNEL_AUDIT_V2',
             'CANONICAL_INVARIANT_GUARD', 'STATEFUL_CONTINUATION_FROM_1142_AND_BOUNDED_PROGRAM_DEVELOPMENT'],
         'source_path': 'architecture/yado-unified-architecture-v2.json',
         'source_digest': file_sha('architecture/yado-unified-architecture-v2.json')}
event['event_hash'] = event_hash(event)
ledger['events'].append(event)
ledger.update(event_count=len(ledger['events']), tail_event_hash=event['event_hash'],
              current_head_digest=head['canonical_head_digest'])
seal(ledger, 'ledger_digest')
validate_ledger_v2(ledger)
save('architecture/evolution-ledger.json', ledger)
print(json.dumps({'sources': len(sources), 'head': head['canonical_head_digest'], 'ledger_event_index': index}))
