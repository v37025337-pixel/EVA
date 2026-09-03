from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import sqrt
from typing import Any, Mapping, Sequence

from yado_organ_runtime_native_v1 import eval_bool, learn_edges, plan_with_edges

NATIVE_PROVENANCE = {
    'status': 'NATIVE_BOUNDED_COGNITIVE_GROWTH_RUNTIME',
    'source': 'ACTIVE_YADO_CONTRACTS_PLUS_FRESH_BENCHMARK_DEFICITS',
    'scope': ['LOGIC', 'THINKING', 'INTELLIGENCE'],
    'external_code_copied_verbatim': False,
    'task_specific_solution_templates': False,
}


def _bool_keys(cases):
    return sorted({str(k) for x, _ in cases for k in x})


def _truth_signature(model, points):
    return tuple(bool(eval_bool(model, x)) for x in points)


def _complexity(model):
    if not isinstance(model, (list, tuple)) or not model:
        return 1
    return 1 + sum(_complexity(x) for x in model[1:] if isinstance(x, (list, tuple)))


def _balanced_fold(op, items):
    items=list(items)
    if not items:
        return ['FALSE'] if op=='OR' else ['TRUE']
    while len(items)>1:
        nxt=[]
        for i in range(0,len(items),2):
            if i+1<len(items): nxt.append([op,items[i],items[i+1]])
            else: nxt.append(items[i])
        items=nxt
    return items[0]


def synthesize_logic_exact_table(cases, max_vars: int = 10):
    """Exact bounded synthesis for a *complete* Boolean truth table.

    Produces a balanced canonical DNF for the smaller of positive or negative
    rows (the latter wrapped in NOT). It refuses incomplete tables, so it is
    not a hidden interpolation policy for partial evidence.
    """
    if not cases:
        return None, {'status':'REJECT_EMPTY','backend':'EXACT_TABLE_DNF'}
    keys=_bool_keys(cases)
    if len(keys)>int(max_vars):
        return None, {'status':'REJECT_TOO_MANY_VARIABLES','variables':len(keys),'backend':'EXACT_TABLE_DNF'}
    seen={}
    for x,y in cases:
        bits=tuple(bool(x.get(k,False)) for k in keys)
        if bits in seen and seen[bits]!=bool(y):
            return None, {'status':'REJECT_CONTRADICTORY_TABLE','backend':'EXACT_TABLE_DNF'}
        seen[bits]=bool(y)
    if len(seen)!=(1<<len(keys)):
        return None, {'status':'REJECT_INCOMPLETE_TABLE','rows':len(seen),'expected':1<<len(keys),'backend':'EXACT_TABLE_DNF'}
    positives=[bits for bits,y in sorted(seen.items()) if y]
    negatives=[bits for bits,y in sorted(seen.items()) if not y]
    use_negative=len(negatives)<len(positives)
    selected=negatives if use_negative else positives
    if not selected:
        model=['TRUE'] if positives else ['FALSE']
        return model,{'status':'EXACT','backend':'EXACT_TABLE_DNF','variables':len(keys),'terms':0,'complemented':use_negative,'exact':1.0}
    terms=[]
    for bits in selected:
        lits=[]
        for key,bit in zip(keys,bits):
            lit=['VAR',key] if bit else ['NOT',['VAR',key]]
            lits.append(lit)
        terms.append(_balanced_fold('AND',lits))
    dnf=_balanced_fold('OR',terms)
    model=['NOT',dnf] if use_negative else dnf
    return model,{'status':'EXACT','backend':'EXACT_TABLE_DNF','variables':len(keys),'terms':len(selected),'complemented':use_negative,'exact':1.0}


def synthesize_logic_bitset(cases, max_nodes: int = 13, max_signatures: int = 262144):
    """Bounded semantic-DP synthesis using integer truth bitsets.

    This is the scalable successor to recursive tuple-signature evaluation.
    It is exact over the supplied cases and keeps only the smallest expression
    for each observed semantic signature.
    """
    if not cases:
        return None, {'signatures': 0, 'max_nodes': int(max_nodes), 'backend': 'BITSET'}
    points=[dict(x) for x,_ in cases]
    target=0
    for i,(_,y) in enumerate(cases):
        if bool(y): target |= (1<<i)
    mask=(1<<len(cases))-1
    keys=_bool_keys(cases)
    by_sig={}
    by_size=defaultdict(list)

    def add(sig, model, size):
        sig &= mask
        if sig in by_sig: return False
        by_sig[sig]=(model,size);by_size[size].append(sig);return True

    add(0,['FALSE'],1); add(mask,['TRUE'],1)
    for key in keys:
        sig=0
        for i,x in enumerate(points):
            if bool(x.get(key,False)): sig|=(1<<i)
        add(sig,['VAR',key],1)
    if target in by_sig:
        m,n=by_sig[target];return m,{'signatures':len(by_sig),'nodes':n,'exact':1.0,'backend':'BITSET'}

    for size in range(2,int(max_nodes)+1):
        # NOT
        for sa in list(by_size.get(size-1,())):
            ma,_=by_sig[sa]; sig=(~sa)&mask
            if add(sig,['NOT',ma],size) and sig==target:
                return by_sig[sig][0],{'signatures':len(by_sig),'nodes':size,'exact':1.0,'backend':'BITSET'}
            if len(by_sig)>=max_signatures: break
        if len(by_sig)>=max_signatures: break

        # Binary commutative operators.
        for ls in range(1,size-1):
            rs=size-1-ls
            if ls>rs or rs<1: continue
            left=list(by_size.get(ls,())); right=list(by_size.get(rs,()))
            for ia,sa in enumerate(left):
                for ib,sb in enumerate(right):
                    if ls==rs and sa>sb: continue
                    ma,_=by_sig[sa];mb,_=by_sig[sb]
                    for op,sig in (('AND',sa&sb),('OR',sa|sb),('XOR',sa^sb)):
                        if add(sig,[op,ma,mb],size) and (sig&mask)==target:
                            return by_sig[sig&mask][0],{'signatures':len(by_sig),'nodes':size,'exact':1.0,'backend':'BITSET'}
                        if len(by_sig)>=max_signatures: break
                    if len(by_sig)>=max_signatures: break
                if len(by_sig)>=max_signatures: break
            if len(by_sig)>=max_signatures: break
        if len(by_sig)>=max_signatures: break

    if not by_sig:
        return None,{'signatures':0,'max_nodes':max_nodes,'exact':0.0,'backend':'BITSET'}
    # Pick the best semantic signature directly, avoiding recursive reevaluation.
    def acc(sig): return 1.0-((sig^target).bit_count()/len(cases))
    best_sig=max(by_sig,key=lambda sig:(acc(sig),-by_sig[sig][1],-sig))
    m,n=by_sig[best_sig]
    return m,{'signatures':len(by_sig),'nodes':n,'exact':acc(best_sig),'bounded':True,'backend':'BITSET'}


def synthesize_logic_minimal(cases, max_nodes: int = 11, max_signatures: int = 65536):
    """Semantic-DP boolean synthesis with a minimum-node bias.

    Unlike the older depth-bounded enumerator, this searches by expression size
    over semantic signatures. It remains bounded and deterministic.
    """
    if not cases:
        return None, {'signatures': 0, 'max_nodes': int(max_nodes)}
    points = [dict(x) for x, _ in cases]
    target = tuple(bool(y) for _, y in cases)
    keys = _bool_keys(cases)
    by_sig: dict[tuple[bool, ...], tuple[Any, int]] = {}
    by_size: dict[int, list[Any]] = defaultdict(list)

    seeds = [['FALSE'], ['TRUE']] + [['VAR', k] for k in keys]
    for m in seeds:
        sig = _truth_signature(m, points)
        if sig not in by_sig:
            by_sig[sig] = (m, 1)
            by_size[1].append(m)
        if sig == target:
            return m, {'signatures': len(by_sig), 'nodes': 1, 'exact': 1.0}

    for size in range(2, int(max_nodes) + 1):
        # Unary NOT: one operator + child.
        child_size = size - 1
        for a in list(by_size.get(child_size, [])):
            m = ['NOT', a]
            sig = _truth_signature(m, points)
            if sig not in by_sig:
                by_sig[sig] = (m, size)
                by_size[size].append(m)
                if sig == target:
                    return m, {'signatures': len(by_sig), 'nodes': size, 'exact': 1.0}
                if len(by_sig) >= max_signatures:
                    break
        if len(by_sig) >= max_signatures:
            break

        # Binary ops: one operator + two children; canonicalize commutative pairs.
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            if right_size < 1 or left_size > right_size:
                continue
            lefts = list(by_size.get(left_size, []))
            rights = list(by_size.get(right_size, []))
            for a in lefts:
                for b in rights:
                    if left_size == right_size and repr(a) > repr(b):
                        continue
                    for op in ('AND', 'OR', 'XOR'):
                        m = [op, a, b]
                        sig = _truth_signature(m, points)
                        if sig in by_sig:
                            continue
                        by_sig[sig] = (m, size)
                        by_size[size].append(m)
                        if sig == target:
                            return m, {'signatures': len(by_sig), 'nodes': size, 'exact': 1.0}
                        if len(by_sig) >= max_signatures:
                            break
                    if len(by_sig) >= max_signatures:
                        break
                if len(by_sig) >= max_signatures:
                    break
            if len(by_sig) >= max_signatures:
                break
        if len(by_sig) >= max_signatures:
            break

    if not by_sig:
        return None, {'signatures': 0, 'max_nodes': max_nodes, 'exact': 0.0}
    # best accuracy, then minimum complexity / deterministic repr
    def rank(item):
        sig, (m, nodes) = item
        acc = sum(a == b for a, b in zip(sig, target)) / len(target)
        return (acc, -nodes, repr(m))
    sig, (best, nodes) = max(by_sig.items(), key=rank)
    acc = sum(a == b for a, b in zip(sig, target)) / len(target)
    return best, {'signatures': len(by_sig), 'nodes': nodes, 'exact': acc, 'bounded': True}


def logic_accuracy(model, cases):
    if model is None or not cases:
        return 0.0
    return sum(bool(eval_bool(model, x)) == bool(y) for x, y in cases) / len(cases)


def learn_multicontext_precedence(episodes, threshold: float = 0.75, min_support: int = 2, max_context_keys: int = 3):
    """Learn separate precedence graphs for bounded context signatures.

    Episode format: (context_mapping_or_iterable, successful_role_trace).
    Context keys are selected only by coverage, not by target ordering.
    """
    if not episodes:
        return {'kind': 'MULTICONTEXT_PRECEDENCE', 'context_keys': [], 'graphs': {}, 'fallback_edges': []}
    contexts = []
    traces = []
    for ctx, trace in episodes:
        if isinstance(ctx, Mapping):
            c = {str(k): bool(v) for k, v in ctx.items()}
        else:
            c = {str(k): True for k in ctx}
        contexts.append(c)
        traces.append([str(r) for r in trace])
    key_counts = Counter(k for c in contexts for k, v in c.items() if v)
    keys = [k for k, _ in sorted(key_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:max_context_keys]]
    grouped: dict[str, list[list[str]]] = defaultdict(list)
    for c, trace in zip(contexts, traces):
        sig = ''.join('1' if c.get(k, False) else '0' for k in keys)
        grouped[sig].append(trace)
    graphs = {}
    for sig, group in sorted(grouped.items()):
        if len(group) >= min_support:
            graphs[sig] = learn_edges(group, threshold=threshold, min_support=min_support)
    return {
        'kind': 'MULTICONTEXT_PRECEDENCE',
        'context_keys': keys,
        'graphs': graphs,
        'fallback_edges': learn_edges(traces, threshold=threshold, min_support=min_support),
        'threshold': float(threshold),
        'min_support': int(min_support),
    }


def plan_multicontext(model, context, actions):
    if not isinstance(model, Mapping) or model.get('kind') != 'MULTICONTEXT_PRECEDENCE':
        return plan_with_edges(actions, model)
    if isinstance(context, Mapping):
        c = {str(k): bool(v) for k, v in context.items()}
    else:
        c = {str(k): True for k in context}
    keys = list(model.get('context_keys') or [])
    sig = ''.join('1' if c.get(k, False) else '0' for k in keys)
    edges = (model.get('graphs') or {}).get(sig, model.get('fallback_edges') or [])
    return plan_with_edges(actions, edges)


def planning_accuracy(model, episodes):
    if not episodes:
        return 0.0
    ok = 0
    for ctx, actions, expected_roles in episodes:
        ids = plan_multicontext(model, ctx, actions)
        by_id = {str(a['id']): str(a['role']) for a in actions}
        got = [by_id[str(i)] for i in ids]
        ok += got == list(expected_roles)
    return ok / len(episodes)


def _numeric_keys(cases):
    return sorted({str(k) for x, _ in cases for k in x})


def fit_knn_strategy(cases, k: int = 3):
    if not cases:
        return None
    keys = _numeric_keys(cases)
    rows = []
    for x, y in cases:
        rows.append(([float(x.get(key, 0.0)) for key in keys], y))
    return {'kind': 'KNN_STRATEGY', 'features': keys, 'rows': rows, 'k': max(1, int(k))}


def knn_predict(model, x: Mapping[str, Any]):
    if not model:
        return None
    keys = list(model['features'])
    q = [float(x.get(key, 0.0)) for key in keys]
    scored = []
    for i, (row, label) in enumerate(model['rows']):
        d = sqrt(sum((a - b) ** 2 for a, b in zip(q, row)))
        scored.append((d, str(label), i, label))
    nearest = sorted(scored)[: max(1, int(model.get('k', 3)))]
    votes = Counter(str(z[3]) for z in nearest)
    best_label_s = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    # Recover original typed label deterministically from nearest occurrence.
    for _, _, _, label in nearest:
        if str(label) == best_label_s:
            return label
    return nearest[0][3]


def strategy_accuracy(model, cases):
    if not model or not cases:
        return 0.0
    return sum(knn_predict(model, x) == y for x, y in cases) / len(cases)


def select_knn_k(fit_cases, validation_cases, candidates=(1, 3, 5, 7, 9)):
    trials = []
    for k in candidates:
        model = fit_knn_strategy(fit_cases, k)
        acc = strategy_accuracy(model, validation_cases)
        trials.append((acc, -int(k), int(k), model))
    _, _, k, model = max(trials, key=lambda z: z[:2])
    return model, {'selected_k': k, 'validation': max(t[0] for t in trials), 'trials': [{'k': t[2], 'accuracy': t[0]} for t in trials]}


def fit_centroid_strategy(cases, max_features: int | None = None):
    if not cases:
        return None
    keys = _numeric_keys(cases)
    labels = sorted({y for _, y in cases}, key=str)
    # Generic Fisher-style feature relevance: between-class spread / within-class spread.
    feature_scores=[]
    for key in keys:
        all_vals=[float(x.get(key,0.0)) for x,_ in cases]
        global_mean=sum(all_vals)/len(all_vals)
        between=0.0; within=0.0
        for label in labels:
            vals=[float(x.get(key,0.0)) for x,y in cases if y==label]
            if not vals: continue
            mean=sum(vals)/len(vals)
            between += len(vals)*(mean-global_mean)**2
            within += sum((v-mean)**2 for v in vals)
        score=between/(within+1e-12)
        feature_scores.append((score,key))
    ranked=[k for _,k in sorted(feature_scores,key=lambda z:(-z[0],z[1]))]
    if max_features is not None:
        ranked=ranked[:max(1,int(max_features))]
    centroids={}
    scales={}
    for key in ranked:
        vals=[float(x.get(key,0.0)) for x,_ in cases]
        mean=sum(vals)/len(vals); var=sum((v-mean)**2 for v in vals)/max(1,len(vals)-1)
        scales[key]=max(var**0.5,1e-6)
    for label in labels:
        rows=[x for x,y in cases if y==label]
        centroids[str(label)]={key:sum(float(x.get(key,0.0)) for x in rows)/len(rows) for key in ranked}
    return {'kind':'CENTROID_STRATEGY','features':ranked,'centroids':centroids,'scales':scales,'label_values':{str(x):x for x in labels}}

def centroid_predict(model, x: Mapping[str,Any]):
    if not model: return None
    scored=[]
    for label_s,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=float(model['scales'].get(key,1.0))
            d += ((float(x.get(key,0.0))-float(center[key]))/scale)**2
        scored.append((d,label_s))
    label_s=min(scored)[1]
    return model['label_values'][label_s]

def centroid_accuracy(model,cases):
    if not model or not cases: return 0.0
    return sum(centroid_predict(model,x)==y for x,y in cases)/len(cases)

def select_centroid_features(fit_cases, validation_cases):
    keys=_numeric_keys(fit_cases)
    trials=[]
    for n in range(1,len(keys)+1):
        m=fit_centroid_strategy(fit_cases,n)
        a=centroid_accuracy(m,validation_cases)
        trials.append((a,-n,n,m))
    _,_,n,m=max(trials,key=lambda z:z[:2])
    return m,{'selected_features':n,'validation':max(t[0] for t in trials),'trials':[{'features':t[2],'accuracy':t[0]} for t in trials]}


__all__ = [
    'NATIVE_PROVENANCE',
    'synthesize_logic_exact_table', 'synthesize_logic_bitset', 'synthesize_logic_minimal', 'logic_accuracy',
    'learn_multicontext_precedence', 'plan_multicontext', 'planning_accuracy',
    'fit_knn_strategy', 'knn_predict', 'strategy_accuracy', 'select_knn_k',
    'fit_centroid_strategy', 'centroid_predict', 'centroid_accuracy', 'select_centroid_features',
]
