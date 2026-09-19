"""Bounded, training-only induction over a reviewed compositional language.

The language, library adapters and search are maintainer-authored. The kernel
selects expressions and infers data structures from examples. This does not
invent new primitives, execute supplied Python, or claim general intelligence.
Emitted ``solve(component_id, program_id, inputs)`` functions use the reviewed
``_primitive`` and ``_input`` globals supplied by :func:`execute`.
"""
from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import itertools
import json
import re
import warnings

SCHEMA = 'yado.compositional_source.v1'
GRAMMAR = 'YADO_TYPED_COMPOSITION_V1'
GRAMMAR_V2 = 'YADO_TYPED_COMPOSITION_V2'
GRAMMARS = (GRAMMAR, GRAMMAR_V2)
MAX_TEXT = 8192
MAX_VALUE_TEXT = 65536
MAX_ITEMS = 128
MAX_NODES = 128
MAX_DEPTH = 16
MAX_STATES = 4096
MAX_ATTEMPTS = 20000
MAX_MEMORIES = 16
MAX_PER_TYPE = 96
MAX_MEMORY_BINDINGS = 64
MAX_SEARCH_VALUE_UNITS = 2_000_000


def _sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _kind(value):
    if type(value) is bool:
        return 'bool'
    if type(value) is int:
        return 'int'
    if type(value) is str:
        return 'str'
    if value is None:
        return 'null'
    if type(value) is list:
        return 'list'
    if type(value) is dict:
        return 'dict'
    if isinstance(value, ast.AST):
        return 'ast'
    raise ValueError('COMPOSITION_VALUE_TYPE')


def _bounded(value, depth=0, *, internal=False, _budget=None):
    if _budget is None:
        _budget = [8192, MAX_VALUE_TEXT]
    _budget[0] -= 1
    if _budget[0] < 0:
        raise ValueError('COMPOSITION_VALUE_NODE_BUDGET')
    if depth > MAX_DEPTH:
        raise ValueError('COMPOSITION_VALUE_DEPTH')
    kind = _kind(value)
    if kind == 'str':
        if len(value) > MAX_VALUE_TEXT:
            raise ValueError('COMPOSITION_VALUE_LENGTH')
        # Reject lone surrogates before source hashing or UTF-8 persistence.
        value.encode('utf-8')
        _budget[1] -= len(value)
        if _budget[1] < 0:
            raise ValueError('COMPOSITION_VALUE_LENGTH')
    elif kind == 'int':
        if abs(value) > 10**9:
            raise ValueError('COMPOSITION_INTEGER_BOUND')
    elif kind in {'list', 'dict'}:
        if len(value) > MAX_ITEMS:
            raise ValueError('COMPOSITION_CONTAINER_BOUND')
        if kind == 'dict':
            if any(type(key) is not str or len(key) > MAX_TEXT for key in value):
                raise ValueError('COMPOSITION_OBJECT_KEY')
            for key in value:
                key.encode('utf-8')
                _budget[1] -= len(key)
                if _budget[1] < 0:
                    raise ValueError('COMPOSITION_VALUE_LENGTH')
        for child in (value.values() if kind == 'dict' else value):
            _bounded(child, depth + 1, internal=internal, _budget=_budget)
    elif kind == 'ast':
        nodes = sum(1 for _ in ast.walk(value)) if internal else 0
        _budget[0] -= nodes
        if not internal or nodes > 1024 or _budget[0] < 0:
            raise ValueError('COMPOSITION_AST_BOUND')
    return value


def _freeze(value):
    """Typed observational key; bool and int must never collapse together."""
    kind = _kind(value)
    if kind == 'ast':
        return (kind, ast.dump(value, include_attributes=False))
    if kind == 'list':
        return (kind, tuple(_freeze(x) for x in value))
    if kind == 'dict':
        return (kind, tuple((k, _freeze(v)) for k, v in value.items()))
    return (kind, value)


def _json_key_v2(value):
    """Semantic JSON key, separate from order-observing search signatures.

    The existing bounded domain still excludes floats, non-string object keys,
    and ASTs. Arrays retain order; object keys do not. Scalar types stay exact.
    """
    kind = _kind(value)
    if kind == 'ast':
        raise ValueError('COMPOSITION_JSON_VALUE_TYPE')
    if kind == 'list':
        return (kind, tuple(_json_key_v2(child) for child in value))
    if kind == 'dict':
        return (kind, tuple((key, _json_key_v2(value[key])) for key in sorted(value)))
    return (kind, value)


def _json_equal_v2(left, right):
    return _json_key_v2(_bounded(left)) == _json_key_v2(_bounded(right))


def _ast_dump(value):
    if isinstance(value, ast.AST):
        return ast.dump(value, include_attributes=False)
    if type(value) is list and all(isinstance(x, ast.AST) for x in value):
        return _canonical([ast.dump(x, include_attributes=False) for x in value])
    raise ValueError('COMPOSITION_AST_DUMP_INPUT')


def _strict_json(text):
    def invalid(_):
        raise ValueError('COMPOSITION_NON_JSON_NUMBER')
    return json.loads(text, parse_constant=invalid)


def _parse_python(text):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', SyntaxWarning)
        return ast.parse(text)


def _unified_diff(before, after, old, new):
    if (len(before) > MAX_ITEMS or len(after) > MAX_ITEMS
            or any(type(line) is not str for line in [*before, *after])
            or sum(map(len, [*before, *after])) > 2 * MAX_TEXT
            or len(old) > 256 or len(new) > 256
            or '\n' in old or '\n' in new or '\r' in old or '\r' in new):
        raise ValueError('COMPOSITION_DIFF_BUDGET')
    return list(difflib.unified_diff(before, after, fromfile=old, tofile=new))


# Signatures and adapters are a finite, versioned library, not task handlers.
# Intermediate ASTs are data. They are never compiled or executed.
_OPERATIONS = {
    'strip': (('str',), lambda x: x.strip()),
    'lower': (('str',), lambda x: x.lower()),
    'upper': (('str',), lambda x: x.upper()),
    'reverse': (('str',), lambda x: x[::-1]),
    'length': (('str|list|dict',), len),
    'splitlines': (('str',), lambda x: x.splitlines(keepends=True)),
    'join': (('list',), lambda x: ''.join(x)),
    'json_parse': (('str',), _strict_json),
    'json_compact': (('json',), lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'), allow_nan=False)),
    'json_ascii': (('json',), lambda x: json.dumps(x, ensure_ascii=True, separators=(',', ':'), allow_nan=False)),
    'json_default': (('json',), lambda x: json.dumps(x, ensure_ascii=False, allow_nan=False)),
    'parse_python': (('str',), _parse_python),
    'top_level_functions': (('ast',), lambda x: [n for n in x.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
    'ast_dump': (('ast|list',), _ast_dump),
    'field': (('dict', 'str'), lambda x, key: x[key]),
    'index': (('list', 'int'), lambda x, index: x[index]),
    'equal': (('any', 'any'), lambda x, y: _freeze(x) == _freeze(y)),
    'not_equal': (('any', 'any'), lambda x, y: _freeze(x) != _freeze(y)),
    'concat': (('str', 'str'), lambda x, y: x + y),
    'add': (('int', 'int'), lambda x, y: x + y),
    'subtract': (('int', 'int'), lambda x, y: x - y),
    'multiply': (('int', 'int'), lambda x, y: x * y),
    'unified_diff': (('list', 'list', 'str', 'str'), _unified_diff),
}
_RESULT_TYPES = {
    'strip': {'str'}, 'lower': {'str'}, 'upper': {'str'}, 'reverse': {'str'},
    'length': {'int'}, 'splitlines': {'list'}, 'join': {'str'},
    'json_parse': {'str', 'int', 'bool', 'null', 'list', 'dict'},
    'json_compact': {'str'}, 'json_ascii': {'str'}, 'json_default': {'str'},
    'parse_python': {'ast'}, 'top_level_functions': {'list'}, 'ast_dump': {'str'},
    'field': {'str', 'int', 'bool', 'null', 'list', 'dict'},
    'index': {'str', 'int', 'bool', 'null', 'list', 'dict', 'ast'},
    'equal': {'bool'}, 'not_equal': {'bool'}, 'concat': {'str'},
    'add': {'int'}, 'subtract': {'int'}, 'multiply': {'int'}, 'unified_diff': {'list'},
    'json_equal_v2': {'bool'}, 'json_not_equal_v2': {'bool'},
}
_OPERATIONS_V2 = {
    **_OPERATIONS,
    'json_equal_v2': (('json', 'json'), _json_equal_v2),
    'json_not_equal_v2': (('json', 'json'), lambda x, y: not _json_equal_v2(x, y)),
}


def _operations(grammar):
    if grammar == GRAMMAR:
        return _OPERATIONS
    if grammar == GRAMMAR_V2:
        return _OPERATIONS_V2
    raise ValueError('COMPOSITION_GRAMMAR_VERSION')


def catalog(*, grammar=GRAMMAR):
    """Return a detached description, never a mutable operator registry."""
    return {'schema': SCHEMA, 'grammar': grammar,
            'operators': [{'name': name, 'arguments': list(signature)}
                          for name, (signature, _) in _operations(grammar).items()],
            'budgets': {'program_nodes': MAX_NODES, 'program_depth': MAX_DEPTH,
                        'input_text_characters': MAX_TEXT, 'value_text_characters': MAX_VALUE_TEXT,
                        'value_nodes': 8192, 'container_items': MAX_ITEMS, 'named_inputs': 8,
                        'search_states': MAX_STATES, 'search_attempts': MAX_ATTEMPTS,
                        'per_type_beam': MAX_PER_TYPE, 'unary_search_depth': 3,
                        'memories': MAX_MEMORIES, 'bindings_per_memory': MAX_MEMORY_BINDINGS,
                        'search_value_units': MAX_SEARCH_VALUE_UNITS},
            'primitive_authorship': 'MAINTAINER', 'selection_inputs': 'TRAINING_ONLY',
            'new_primitive_invention': False}


def _accepts(signature, value):
    kind = _kind(value)
    return signature == 'any' or kind in signature.split('|') or signature == 'json' and kind != 'ast'


def _primitive(name, *arguments):
    signatures, implementation = _OPERATIONS_V2[name]
    if len(arguments) != len(signatures) or not all(_accepts(s, v) for s, v in zip(signatures, arguments)):
        raise ValueError('COMPOSITION_PRIMITIVE_SIGNATURE')
    return _bounded(implementation(*arguments), internal=True)


def _input(inputs, key):
    return inputs[key]


def _node(op, **fields):
    return {'op': op, **fields}


def _call(name, *args):
    return _node('call', name=name, args=list(args))


def _literal(value):
    return _node('literal', value=value)


def _validate_program(program, signature, *, grammar=GRAMMAR):
    count = 0
    operations = _operations(grammar)
    keys = {key for key, _ in signature}
    kinds = dict(signature)

    def visit(node, depth=0):
        nonlocal count
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH:
            raise ValueError('COMPOSITION_PROGRAM_BUDGET')
        if type(node) is not dict or type(node.get('op')) is not str:
            raise ValueError('COMPOSITION_IR_SCHEMA')
        op = node['op']
        if op == 'input':
            if set(node) != {'op', 'key'} or type(node['key']) is not str or node['key'] not in keys:
                raise ValueError('COMPOSITION_INPUT_REFERENCE')
            return {kinds[node['key']]}
        elif op == 'literal':
            if set(node) != {'op', 'value'} or type(node['value']) not in {str, int, bool, type(None)}:
                raise ValueError('COMPOSITION_LITERAL_SCHEMA')
            _bounded(node['value'])
            if type(node['value']) is str and len(node['value']) > MAX_TEXT:
                raise ValueError('COMPOSITION_LITERAL_BOUND')
            return {_kind(node['value'])}
        elif op == 'call':
            if (set(node) != {'op', 'name', 'args'} or type(node['name']) is not str
                    or node['name'] not in operations or type(node['args']) is not list
                    or len(node['args']) != len(operations[node['name']][0])):
                raise ValueError('COMPOSITION_CALL_SCHEMA')
            for expected, child in zip(operations[node['name']][0], node['args']):
                possible = visit(child, depth + 1)
                accepted = ({'str', 'int', 'bool', 'null', 'list', 'dict'} if expected == 'json'
                            else {'str', 'int', 'bool', 'null', 'list', 'dict', 'ast'} if expected == 'any'
                            else set(expected.split('|')))
                if not possible & accepted:
                    raise ValueError('COMPOSITION_IR_TYPE_MISMATCH')
            return _RESULT_TYPES[node['name']]
        elif op == 'list':
            if set(node) != {'op', 'items'} or type(node['items']) is not list or len(node['items']) > MAX_ITEMS:
                raise ValueError('COMPOSITION_LIST_SCHEMA')
            for child in node['items']:
                visit(child, depth + 1)
            return {'list'}
        elif op == 'object':
            if set(node) != {'op', 'items'} or type(node['items']) is not list or len(node['items']) > MAX_ITEMS:
                raise ValueError('COMPOSITION_OBJECT_SCHEMA')
            seen = set()
            for pair in node['items']:
                if (type(pair) is not list or len(pair) != 2 or type(pair[0]) is not str
                        or len(pair[0]) > MAX_TEXT or pair[0] in seen):
                    raise ValueError('COMPOSITION_OBJECT_SCHEMA')
                pair[0].encode('utf-8')
                seen.add(pair[0])
                visit(pair[1], depth + 1)
            return {'dict'}
        else:
            raise ValueError('COMPOSITION_UNKNOWN_OPERATION')

    visit(program)
    return count


def _expression(node):
    op = node['op']
    if op == 'input':
        return '_input(inputs, ' + repr(node['key']) + ')'
    if op == 'literal':
        return repr(node['value'])
    if op == 'call':
        return '_primitive(' + ', '.join([repr(node['name'])] + [_expression(x) for x in node['args']]) + ')'
    if op == 'list':
        return '[' + ', '.join(_expression(x) for x in node['items']) + ']'
    return '{' + ', '.join(repr(k) + ': ' + _expression(v) for k, v in node['items']) + '}'


def _emit(program):
    return ('def solve(component_id, program_id, inputs):\n'
            '    return ' + _expression(program) + '\n')


def _signature(signature):
    if (type(signature) is not list or not 1 <= len(signature) <= 8
            or any(type(x) is not list or len(x) != 2 or type(x[0]) is not str
                   or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', x[0])
                   or type(x[1]) is not str
                   or x[1] not in {'str', 'int', 'bool', 'null', 'list', 'dict'} for x in signature)
            or len({x[0] for x in signature}) != len(signature)
            or signature != sorted(signature)):
        raise ValueError('COMPOSITION_INPUT_SIGNATURE')
    return signature


def validate(candidate):
    """Validate reviewed IR and exact re-emission, never a caller's hash alone."""
    if type(candidate) is not dict:
        raise ValueError('COMPOSITION_CANDIDATE_SCHEMA')
    required = {'schema', 'grammar', 'program', 'source', 'source_sha256', 'input_signature',
                'training_digest', 'parent_source_sha256', 'synthesis_inputs'}
    if (not required <= set(candidate) or candidate['schema'] != SCHEMA or candidate['grammar'] not in GRAMMARS
            or candidate['synthesis_inputs'] != 'TRAINING_ONLY'):
        raise ValueError('COMPOSITION_CANDIDATE_SCHEMA')
    signature = _signature(candidate['input_signature'])
    _validate_program(candidate['program'], signature, grammar=candidate['grammar'])
    expected = _emit(candidate['program'])
    if type(candidate['source']) is not str or candidate['source'] != expected:
        raise ValueError('COMPOSITION_SOURCE_REEMISSION_MISMATCH')
    if type(candidate['source_sha256']) is not str or candidate['source_sha256'] != _sha(expected):
        raise ValueError('COMPOSITION_SOURCE_DIGEST_MISMATCH')
    if type(candidate['training_digest']) is not str or not re.fullmatch('[0-9a-f]{64}', candidate['training_digest']):
        raise ValueError('COMPOSITION_TRAINING_DIGEST')
    parents = candidate['parent_source_sha256']
    if (type(parents) is not list or len(parents) > MAX_MEMORIES
            or any(type(p) is not str or not re.fullmatch('[0-9a-f]{64}', p) for p in parents)
            or parents != sorted(set(parents))):
        raise ValueError('COMPOSITION_MEMORY_PROVENANCE')


def _checked_inputs(inputs, signature):
    if type(inputs) is not dict or sorted(inputs) != [x[0] for x in signature]:
        raise ValueError('COMPOSITION_INPUT_SIGNATURE')
    for key, kind in signature:
        if _kind(inputs[key]) != kind:
            raise ValueError('COMPOSITION_INPUT_SIGNATURE')
        _bounded(inputs[key])
        if type(inputs[key]) is str and len(inputs[key]) > MAX_TEXT:
            raise ValueError('COMPOSITION_INPUT_LENGTH')
    return copy.deepcopy(inputs)


def execute(candidate, inputs):
    """Execute only reviewed re-emitted programs; this is not a Python sandbox."""
    # Snapshot before checking so another owner cannot replace checked source
    # between re-emission verification and compilation.
    candidate = copy.deepcopy(candidate)
    validate(candidate)
    if type(inputs) is not list or len(inputs) > 128:
        raise ValueError('COMPOSITION_EXECUTION_BATCH')
    namespace = {'__builtins__': {}, '_primitive': _primitive, '_input': _input}
    exec(compile(candidate['source'], '<reviewed-compositional-source>', 'exec'), namespace)
    return [_bounded(namespace['solve']('learned', 'learned', _checked_inputs(row, candidate['input_signature'])))
            for row in inputs]


def _evaluate(program, row):
    op = program['op']
    if op == 'input':
        return row[program['key']]
    if op == 'literal':
        return program['value']
    if op == 'call':
        return _primitive(program['name'], *[_evaluate(x, row) for x in program['args']])
    if op == 'list':
        return [_evaluate(x, row) for x in program['items']]
    return {k: _evaluate(v, row) for k, v in program['items']}


def _training(training):
    if type(training) is not list or not 3 <= len(training) <= 64:
        raise ValueError('COMPOSITION_TRAINING_BUDGET')
    clean, signature, seen, output_kind = [], None, set(), None
    for row in training:
        if type(row) is not dict or set(row) != {'input', 'expected'} or type(row['input']) is not dict:
            raise ValueError('COMPOSITION_TRAINING_SCHEMA')
        current = [[k, _kind(v)] for k, v in sorted(row['input'].items())]
        _signature(current)
        signature = current if signature is None else signature
        inputs = _checked_inputs(row['input'], signature)
        marker = _canonical(inputs)
        if marker in seen:
            raise ValueError('COMPOSITION_DUPLICATE_INPUT')
        seen.add(marker)
        _bounded(row['expected'])
        kind = _kind(row['expected'])
        output_kind = kind if output_kind is None else output_kind
        if output_kind != kind:
            raise ValueError('COMPOSITION_OUTPUT_SIGNATURE')
        clean.append({'input': inputs, 'expected': copy.deepcopy(row['expected'])})
    return clean, signature, output_kind


def _rename(program, mapping):
    result = copy.deepcopy(program)
    def visit(node):
        if node['op'] == 'input':
            node['key'] = mapping[node['key']]
        for child in node.get('args', []):
            visit(child)
        if node['op'] == 'list':
            for child in node['items']:
                visit(child)
        if node['op'] == 'object':
            for _, child in node['items']:
                visit(child)
    visit(result)
    return result


def _withhold(reason, **stats):
    return {'schema': SCHEMA, 'status': 'WITHHOLD', 'reason': reason, 'source': None,
            'synthesis_inputs': 'TRAINING_ONLY', 'automatic_canonical_promotion': False, **stats}


def synthesize(training, *, memories=(), grammar=GRAMMAR):
    """Infer a program from training alone and previously verified memory seeds.

    The caller supplies memories exclusively from its verified durable journal;
    a valid candidate proves grammar origin, not prior holdout success. Inlining
    records the exact parent programs used. Memory contains no new callables.
    """
    operations = _operations(grammar)
    try:
        rows, signature, output_kind = _training(training)
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        return _withhold(str(error))
    if not isinstance(memories, (tuple, list)) or len(memories) > MAX_MEMORIES:
        raise ValueError('COMPOSITION_MEMORY_BUDGET')
    for memory in memories:
        validate(memory)
        if grammar == GRAMMAR and memory['grammar'] != GRAMMAR:
            raise ValueError('COMPOSITION_MEMORY_GRAMMAR')
    target = tuple(_freeze(row['expected']) for row in rows)
    pool, by_behavior, attempts, value_units = [], {}, 0, 0
    match = None

    def add(program, parents=(), depth=0):
        nonlocal attempts, match, value_units
        attempts += 1
        if attempts > MAX_ATTEMPTS or len(pool) >= MAX_STATES:
            raise OverflowError('COMPOSITION_SEARCH_BUDGET')
        try:
            _validate_program(program, signature, grammar=grammar)
            values = [_bounded(_evaluate(program, row['input']), internal=True) for row in rows]
            behavior = tuple(_freeze(value) for value in values)
        except (ValueError, TypeError, KeyError, IndexError, SyntaxError, UnicodeError, RecursionError, OverflowError):
            return None
        previous = by_behavior.get(behavior)
        if previous is not None:
            return previous
        def weight(value):
            if type(value) is str:
                return len(value) + 1
            if type(value) is tuple:
                return 1 + sum(weight(x) for x in value)
            return 1
        value_units += weight(behavior)
        if value_units > MAX_SEARCH_VALUE_UNITS:
            raise OverflowError('COMPOSITION_SEARCH_VALUE_BUDGET')
        entry = {'program': program, 'values': values, 'behavior': behavior, 'depth': depth,
                 'kind': _kind(values[0]), 'parents': frozenset(parents)}
        pool.append(entry)
        by_behavior[behavior] = entry
        if behavior == target and match is None:
            match = entry
        return entry

    def entries(kind=None):
        return [x for x in pool if kind is None or x['kind'] == kind][:MAX_PER_TYPE]

    def unary(name, entry):
        return add(_call(name, entry['program']), entry['parents'], entry['depth'] + 1)

    def structure(values, depth=0):
        if depth > MAX_DEPTH:
            return None
        behavior = tuple(_freeze(v) for v in values)
        if behavior in by_behavior:
            entry = by_behavior[behavior]
            return entry['program'], entry['parents']
        if all(_freeze(v) == _freeze(values[0]) for v in values) and type(values[0]) in {str, int, bool, type(None)}:
            return _literal(values[0]), frozenset()
        if all(type(v) is dict and list(v) == list(values[0]) for v in values):
            items, parents = [], set()
            for key in values[0]:
                child = structure([v[key] for v in values], depth + 1)
                if child is None:
                    return None
                items.append([key, child[0]])
                parents.update(child[1])
            return _node('object', items=items), frozenset(parents)
        if all(type(v) is list and len(v) == len(values[0]) for v in values):
            items, parents = [], set()
            for index in range(len(values[0])):
                child = structure([v[index] for v in values], depth + 1)
                if child is None:
                    return None
                items.append(child[0])
                parents.update(child[1])
            return _node('list', items=items), frozenset(parents)
        return None

    def infer_structures():
        values = [row['expected'] for row in rows]
        if output_kind in {'dict', 'list'}:
            inferred = structure(values)
            if inferred:
                add(inferred[0], inferred[1])
        elif output_kind == 'str':
            try:
                parsed = [_bounded(_strict_json(v)) for v in values]
            except (ValueError, TypeError, UnicodeError, RecursionError):
                return
            inferred = structure(parsed)
            if inferred:
                for encoder in ('json_compact', 'json_ascii', 'json_default'):
                    add(_call(encoder, inferred[0]), inferred[1])

    try:
        # Verified programs are first-class seeds, renamed by typed argument
        # bijections. Their expression trees are inlined, not dynamically called.
        seen_memory = set()
        for memory in memories:
            if memory['source_sha256'] in seen_memory:
                continue
            seen_memory.add(memory['source_sha256'])
            old = memory['input_signature']
            if len(old) > len(signature):
                continue
            for selected in itertools.islice(itertools.permutations(signature, len(old)), MAX_MEMORY_BINDINGS):
                if any(a[1] != b[1] for a, b in zip(old, selected)):
                    continue
                renamed = _rename(memory['program'], {a[0]: b[0] for a, b in zip(old, selected)})
                add(renamed, [memory['source_sha256']])
        for key, _ in signature:
            add(_node('input', key=key))
        for value in (None, False, True, 0, 1, -1, ''):
            add(_literal(value))
        # Generic lexical constants: only shared tokens from every training
        # output. No query labels, row-specific outputs or task names enter here.
        constants = []
        if output_kind == 'str':
            tokens = [set(re.findall(r'[A-Za-z0-9_./-]{1,128}', row['expected'])) for row in rows]
            constants = sorted(set.intersection(*tokens))[:24]
            for value in constants:
                add(_literal(value))
        infer_structures()
        for depth in range(3):
            if match is not None:
                break
            frontier = [x for x in pool if x['depth'] == depth]
            # Per-type beams make selection order deterministic and bounded.
            selected = []
            for kind in ('str', 'int', 'bool', 'null', 'list', 'dict', 'ast'):
                selected.extend([x for x in frontier if x['kind'] == kind][:MAX_PER_TYPE])
            for entry in selected:
                for name, (arg_types, _) in operations.items():
                    if len(arg_types) == 1 and all(_accepts(arg_types[0], v) for v in entry['values']):
                        unary(name, entry)
                if entry['kind'] == 'dict':
                    common = set.intersection(*(set(v) for v in entry['values']))
                    for key in sorted(common)[:16]:
                        add(_call('field', entry['program'], _literal(key)), entry['parents'], depth + 1)
                if entry['kind'] == 'list':
                    for index in range(min(8, *(len(v) for v in entry['values']))):
                        add(_call('index', entry['program'], _literal(index)), entry['parents'], depth + 1)
            infer_structures()
        if match is None and output_kind == 'bool':
            # Comparison accepts canonical ASTs as well as ordinary values;
            # matching type prevents accidental bool/int equivalence.
            pairs = []
            for kind in ('ast', 'list', 'str', 'int', 'bool', 'dict', 'null'):
                for left, right in itertools.combinations(entries(kind), 2):
                    cost = (_validate_program(left['program'], signature, grammar=grammar)
                            + _validate_program(right['program'], signature, grammar=grammar))
                    pairs.append((cost, left, right))
            # V1 retains its exact comparator order and attempt counts. V2 first
            # tries explicit JSON semantics, then the unchanged AST/general ops.
            phases = [('equal', 'not_equal')]
            if grammar == GRAMMAR_V2:
                phases.insert(0, ('json_equal_v2', 'json_not_equal_v2'))
            for names in phases:
                for _, left, right in sorted(pairs, key=lambda item: item[0]):
                    if names[0] == 'json_equal_v2' and left['kind'] == 'ast':
                        continue
                    for name in names:
                        add(_call(name, left['program'], right['program']), left['parents'] | right['parents'])
                        if match is not None:
                            break
                    if match is not None:
                        break
                if match is not None:
                    break
        if match is None and output_kind == 'str':
            # Library calls remain compositional: splitlines -> diff -> join.
            # File labels come from shared lexical constants, not a fixed path.
            lines = [x for x in entries('list') if all(all(type(v) is str for v in seq) for seq in x['values'])]
            labels = ['', *constants]
            for left, right in itertools.permutations(lines[:12], 2):
                for old, new in itertools.product(labels, repeat=2):
                    program = _call('join', _call('unified_diff', left['program'], right['program'], _literal(old), _literal(new)))
                    add(program, left['parents'] | right['parents'])
                    if match is not None:
                        break
                if match is not None:
                    break
        if match is None and output_kind in {'str', 'int'}:
            names = ('concat',) if output_kind == 'str' else ('add', 'subtract', 'multiply')
            for left, right in itertools.product(entries(output_kind)[:48], repeat=2):
                for name in names:
                    add(_call(name, left['program'], right['program']), left['parents'] | right['parents'])
                    if match is not None:
                        break
                if match is not None:
                    break
    except OverflowError as error:
        if match is None:
            return _withhold(str(error), search_states=len(pool), search_attempts=attempts)
    if match is None:
        return _withhold('COMPOSITION_NO_PROGRAM_WITHIN_GRAMMAR', search_states=len(pool), search_attempts=attempts)
    source = _emit(match['program'])
    candidate = {'schema': SCHEMA, 'grammar': grammar, 'program': match['program'],
                 'source': source, 'source_sha256': _sha(source), 'input_signature': signature,
                 'training_digest': _sha(_canonical(rows)), 'synthesis_inputs': 'TRAINING_ONLY',
                 'parent_source_sha256': sorted(match['parents']), 'compiled': True,
                 'origin': 'KERNEL_SELECTED_COMPOSITION_OF_REVIEWED_PRIMITIVES',
                 'automatic_canonical_promotion': False,
                 'search_states': len(pool), 'search_attempts': attempts}
    validate(candidate)
    predictions = execute(candidate, [row['input'] for row in rows])
    if tuple(_freeze(v) for v in predictions) != target:
        return _withhold('COMPOSITION_EMITTED_EXECUTION_MISMATCH')
    return candidate
