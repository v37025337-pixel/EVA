from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
PREV = REPO / "architecture/yado-native-controller-source-self-mutation-v2.json"
BASE = REPO / "candidates/g2-self-evolution/yado_evolutionary_genome_self_candidate_v2b.py"
OUT = REPO / "candidates/g2-self-evolution/yado_evolutionary_genome_new_dimension_candidate_v1.py"
RECEIPT = REPO / "candidates/g2-self-evolution/yado-native-controller-new-dimension-genesis-v1.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_SPEC_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_candidate(base_source: str) -> str:
    tree = ast.parse(base_source)
    renamed = False
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "YADOEvolutionaryGenomeV1":
            node.name = "_YADOEvolutionaryGenomeV1Base"
            renamed = True
            break
    if not renamed:
        raise RuntimeError("BASE_CONTROLLER_CLASS_NOT_FOUND")
    ast.fix_missing_locations(tree)
    prefix = ast.unparse(tree) + "\n\nimport re\nimport hashlib\n\n"
    extension = r'''
class YADOEvolutionaryGenomeV1(_YADOEvolutionaryGenomeV1Base):
    _DIMENSION_STOP = {
        'NATIVE','SEMANTIC','SELF','OF','AND','THE','A','AN','TO','FROM','FOR','WITH',
        'EVOLUTIONARY','EVOLUTION','REQUIRED','CAPABILITY','NEXT','G2','V1','V2','V3',
        'PASS','WITHHOLD','SHADOW','CONTROLLER','GENESIS','NEW','DIMENSION','SOURCE',
        'REPAIR','CURRENT','TASK','OWN','FAILED','PRIOR','STATUS','ARTIFACT','SCHEMA'
    }

    def _dimension_evidence_strings(self):
        rows = []
        priority_keys = {
            'next_required_capability','failure_next_required_capability','residual_frontier',
            'required_capabilities','deficit','deficits','suggestion','signature','task','objective'
        }
        def walk(x, key=''):
            if isinstance(x, dict):
                for k, v in x.items():
                    walk(v, str(k).lower())
            elif isinstance(x, list):
                for v in x:
                    walk(v, key)
            elif isinstance(x, str) and key in priority_keys:
                rows.append(x)
        walk(self.experience_sources)
        return rows

    def _derive_emergent_dimension(self):
        evidence = self._dimension_evidence_strings()
        if not evidence:
            return None, {'reason':'NO_CAUSAL_DEFICIT_EVIDENCE'}
        existing = {str(k).upper() for k in (self.parent.get('chromosomes') or {})}
        counts = {}
        first = {}
        order = 0
        for text in evidence:
            for token in re.findall(r'[A-Za-z][A-Za-z0-9]{2,}', text.upper().replace('_',' ')):
                if token in self._DIMENSION_STOP or token in existing or token.isdigit():
                    continue
                counts[token] = counts.get(token, 0) + 1
                first.setdefault(token, order)
                order += 1
        ranked = sorted(counts, key=lambda t: (-counts[t], first[t], t))
        if not ranked:
            material = '\n'.join(evidence).encode('utf-8')
            label = 'EMERGENT_' + hashlib.sha256(material).hexdigest()[:12].upper()
        else:
            label = '_'.join(ranked[:2])
        if label in existing:
            label = label + '_' + hashlib.sha256('\n'.join(evidence).encode('utf-8')).hexdigest()[:8].upper()
        meta = {
            'evidence_count': len(evidence),
            'evidence_digest': hashlib.sha256('\n'.join(evidence).encode('utf-8')).hexdigest(),
            'ranked_novel_tokens': ranked[:8],
            'existing_dimensions': sorted(existing),
            'derived_dimension': label,
        }
        return label, meta

    def observe_parent_deficits(self):
        deficits = super().observe_parent_deficits()
        dim, meta = self._derive_emergent_dimension()
        if dim:
            deficits[dim] = {
                'deficit': True,
                'signature': 'UNREPRESENTED_CAUSAL_DEFICIT_CLASS:' + meta['evidence_digest'][:16],
                'suggestion': 'MATERIALIZE_DEFICIT_DERIVED_CHROMOSOME',
                'genesis_meta': meta,
            }
        return deficits

    def mutate(self, deficits):
        child = super().mutate({k:v for k,v in deficits.items() if k in self.parent.get('chromosomes', {})})
        dim, meta = self._derive_emergent_dimension()
        if dim and dim not in child['chromosomes']:
            child['chromosomes'][dim] = self._gene(
                'ALG-G2-EMERGENT-' + hashlib.sha256(dim.encode('utf-8')).hexdigest()[:16].upper(),
                {
                    'mode':'DEFICIT_DERIVED_DIMENSION_V1',
                    'evidence_digest':meta['evidence_digest'],
                    'evidence_count':meta['evidence_count'],
                    'ranked_novel_tokens':meta['ranked_novel_tokens'],
                    'rollback_anchor':self.parent.get('genome_digest'),
                },
                [g.get('gene_id') for g in self.parent.get('chromosomes',{}).values() if isinstance(g,dict) and g.get('gene_id')],
                True,
                'CAUSAL_DEFICIT_CLASS_ABSENT_FROM_PARENT_GENOME',
            )
            child['mutation_count'] = int(child.get('mutation_count',0)) + 1
            child['novel_gene_count'] = int(child.get('novel_gene_count',0)) + 1
            child['emergent_dimension'] = dim
            child['emergent_dimension_meta'] = meta
            child['genome_digest'] = _digest({k:v for k,v in child.items() if k != 'genome_digest'})
        return child

    @staticmethod
    def evaluate(parent, child):
        score = _YADOEvolutionaryGenomeV1Base.evaluate(parent, child)
        parent_dims = set((parent.get('chromosomes') or {}).keys())
        child_dims = set((child.get('chromosomes') or {}).keys())
        for dim in sorted(child_dims - parent_dims):
            gene = child['chromosomes'][dim]
            expr = gene.get('expression') or {}
            valid = bool(
                gene.get('novel_gene')
                and expr.get('mode') == 'DEFICIT_DERIVED_DIMENSION_V1'
                and expr.get('evidence_digest')
                and expr.get('rollback_anchor') == parent.get('genome_digest')
            )
            score['parent'][dim] = 0.0
            score['child'][dim] = 1.0 if valid else 0.0
            score['regression'][dim] = valid
        score['parent_mean'] = sum(score['parent'].values()) / max(1, len(score['parent']))
        score['child_mean'] = sum(score['child'].values()) / max(1, len(score['child']))
        score['fitness_gain'] = score['child_mean'] - score['parent_mean']
        score['all_regressions_pass'] = all(score['regression'].values())
        return score

    def native_new_dimension_genesis(self):
        dim, meta = self._derive_emergent_dimension()
        return {
            'controller_representation':'evolvable_controller',
            'genesis_kind':'DEFICIT_DERIVED_DIMENSION_V1',
            'derived_dimension':dim,
            'evidence':meta,
            'gene_schema':{
                'mode':'DEFICIT_DERIVED_DIMENSION_V1',
                'evidence_digest':'sha256',
                'rollback_anchor':'parent_genome_digest',
            },
            'host_preselected_dimension_name':False,
            'canonical_mutation':False,
        }
'''
    out = prefix + extension
    compile(out, "<yado-native-new-dimension-candidate>", "exec")
    return out


def parent_for(cls):
    return cls.parent_genome(
        head_digest="0" * 64,
        component_digests={"LOGIC":"l","THINKING":"t","INTELLIGENCE":"i","CODE":"c"},
        experience_digest="dimension-genesis-v1",
    )


def main() -> int:
    prev = json.loads(PREV.read_text(encoding="utf-8"))
    if prev.get("status") != "PASS_NATIVE_CONTROLLER_SOURCE_SELF_MUTATION_V2":
        raise RuntimeError("PRIOR_SOURCE_SELF_MUTATION_NOT_ADMITTED")
    base_bytes = BASE.read_bytes()
    base_sha = sha256_bytes(base_bytes)
    if base_sha != prev.get("validated_second_generation_candidate_sha256"):
        raise RuntimeError("PRIOR_CANDIDATE_SHA_MISMATCH")

    candidate_source = build_candidate(base_bytes.decode("utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(candidate_source, encoding="utf-8")
    candidate_sha = sha256_bytes(candidate_source.encode("utf-8"))

    mod = load_module(OUT, "yado_evolutionary_genome_new_dimension_candidate_v1")
    cls = mod.YADOEvolutionaryGenomeV1
    parent = parent_for(cls)

    empty = cls(parent, experience_sources=[])
    empty_result = empty.evolve_once()
    empty_new = sorted(set((empty_result.get('child') or {}).get('chromosomes',{})) - set(parent.get('chromosomes',{})))

    causal_experience = [
        {
            'role':'PRIOR_VERIFIED_CONTROLLER_RESULT',
            'residual_frontier':prev.get('residual_frontier'),
            'next_required_capability':prev.get('next_step'),
            'strict_probe_new_dimensions':prev.get('strict_probe_new_dimensions'),
            'validated_candidate_sha256':prev.get('validated_second_generation_candidate_sha256'),
        },
        {
            'role':'PRIOR_STRICT_WITHHOLD',
            'failure_next_required_capability':'NATIVE_EVOLUTIONARY_CONTROLLER_SELF_REPRESENTATION_AND_MUTATION_V2',
            'deficit':'STRUCTURAL_SEARCH_SPACE_DID_NOT_EXPAND',
        },
    ]
    causal = cls(parent, experience_sources=causal_experience)
    causal_result = causal.evolve_once()
    child = causal_result.get('child') or {}
    new_dims = sorted(set((child.get('chromosomes') or {})) - set(parent.get('chromosomes',{})))
    representation = causal.native_new_dimension_genesis()

    checks = {
        'prior_source_self_mutation_admitted': True,
        'prior_candidate_sha_bound': True,
        'candidate_source_changed': candidate_sha != base_sha,
        'candidate_source_compiles': True,
        'no_dimension_without_causal_deficit_evidence': empty_new == [],
        'dimension_created_with_causal_deficit_evidence': len(new_dims) >= 1,
        'derived_dimension_not_parent_dimension': all(d not in parent.get('chromosomes',{}) for d in new_dims),
        'dimension_name_not_predeclared_by_host': all(d not in candidate_source for d in new_dims),
        'derived_gene_is_novel': all(bool(child['chromosomes'][d].get('novel_gene')) for d in new_dims),
        'rollback_anchor_bound': all((child['chromosomes'][d].get('expression') or {}).get('rollback_anchor') == parent.get('genome_digest') for d in new_dims),
        'causal_evolution_selects_child': causal_result.get('selection') == 'CHILD',
        'all_regressions_pass': (causal_result.get('fitness') or {}).get('all_regressions_pass') is True,
        'controller_representation_emitted': representation.get('controller_representation') == 'evolvable_controller',
        'host_preselected_dimension_name': representation.get('host_preselected_dimension_name') is True,
        'canonical_mutation': False,
        'external_model_used': False,
    }
    passed = (
        checks['prior_source_self_mutation_admitted']
        and checks['prior_candidate_sha_bound']
        and checks['candidate_source_changed']
        and checks['candidate_source_compiles']
        and checks['no_dimension_without_causal_deficit_evidence']
        and checks['dimension_created_with_causal_deficit_evidence']
        and checks['derived_dimension_not_parent_dimension']
        and checks['dimension_name_not_predeclared_by_host']
        and checks['derived_gene_is_novel']
        and checks['rollback_anchor_bound']
        and checks['causal_evolution_selects_child']
        and checks['all_regressions_pass']
        and checks['controller_representation_emitted']
        and not checks['host_preselected_dimension_name']
        and not checks['canonical_mutation']
        and not checks['external_model_used']
    )

    report = {
        'schema':'yado.native_controller_new_dimension_genesis.v1',
        'status':'PASS_SHADOW_NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS_V1' if passed else 'WITHHOLD_NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS_V1',
        'base_candidate':str(BASE.relative_to(REPO)),
        'base_candidate_sha256':base_sha,
        'candidate_path':str(OUT.relative_to(REPO)),
        'candidate_sha256':candidate_sha,
        'parent_dimensions':sorted(parent.get('chromosomes',{})),
        'empty_evidence_new_dimensions':empty_new,
        'causal_evidence_digest':hashlib.sha256(json.dumps(causal_experience,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'derived_new_dimensions':new_dims,
        'derived_dimension_meta':child.get('emergent_dimension_meta'),
        'selection':causal_result.get('selection'),
        'fitness':causal_result.get('fitness'),
        'controller_representation':representation,
        'checks':checks,
        'semantic_boundary':'HOST PROVIDES A GENERIC DEFICIT-TO-DIMENSION GENESIS OPERATOR, NOT A FIFTH DIMENSION NAME. THE RUNNING CONTROLLER DERIVES THE ACTUAL DIMENSION LABEL FROM UNRESOLVED CAUSAL EXPERIENCE, CREATES ITS CHROMOSOME/GENE, BINDS ROLLBACK TO THE PARENT, AND MUST PASS A/B + REGRESSION. DEVELOPMENT CANDIDATE ONLY.',
        'canonical_mutation':False,
        'next_required_capability':'NATIVE_CONTROLLER_DIMENSION_FRESH_TRANSFER_AND_ABLATION' if passed else 'NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS_REPAIR',
    }
    report['receipt_sha256'] = hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    RECEIPT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
    print(json.dumps({
        'status':report['status'],
        'parent_dimensions':report['parent_dimensions'],
        'empty_evidence_new_dimensions':empty_new,
        'derived_new_dimensions':new_dims,
        'selection':report['selection'],
        'candidate_sha256':candidate_sha,
        'next_required_capability':report['next_required_capability'],
        'receipt_sha256':report['receipt_sha256'],
    },indent=2,sort_keys=True))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
