"""Explicit adapters over inherited solvers and a bounded arithmetic source IR."""
from __future__ import annotations

import ast
import math
import re

from .archive import sha
from .cognitive import CognitiveLoop, STRATEGIES as COG_STRATEGIES, split_examples, validate_goal
from .kernel import SuccessorKernel, encode, equivalent

STRATEGIES = {**COG_STRATEGIES, 'source_synthesis': (('native_expression_ir', 3),),
              'source_apply': (('registered_source', 1),),
              **{'native:' + k: (('inherited_dispatch', 1),) for k in SuccessorKernel.TASK_KINDS}}


def validate_input(capability, value):
    if capability not in STRATEGIES or not isinstance(value, dict):
        raise ValueError('UNKNOWN_CAPABILITY_OR_INPUT_SCHEMA')
    if capability in COG_STRATEGIES or capability == 'source_synthesis':
        if 'domain' in value:
            raise ValueError('INPUT_CANNOT_OVERRIDE_CAPABILITY')
        spec = validate_goal({'domain': 'numeric' if capability == 'source_synthesis' else capability, **value})
        return {k: v for k, v in spec.items() if k != 'domain'}
    if capability == 'source_apply':
        if (set(value) != {'capability_id', 'queries'} or not isinstance(value['capability_id'], str)
                or not re.fullmatch('[0-9a-f]{64}', value['capability_id'])
                or not isinstance(value['queries'], list) or not 1 <= len(value['queries']) <= 32):
            raise ValueError('REGISTERED_SOURCE_INPUT_SCHEMA')
        for q in value['queries']:
            if (not isinstance(q, dict) or set(q) != {'x', 'y'}
                    or any(type(v) is not int or abs(v) > 1000 for v in q.values())):
                raise ValueError('SOURCE_QUERY_BOUND')
    encode(value)
    return value


def expression_ast(expr, depth=0):
    if depth > 12:
        raise ValueError('SOURCE_IR_DEPTH')
    if expr in ('x', 'y'):
        return ast.Name(id=expr, ctx=ast.Load())
    if type(expr) in (int, float) and math.isfinite(expr) and abs(expr) <= 10**12:
        return ast.Constant(value=expr)
    if isinstance(expr, (tuple, list)) and len(expr) == 3 and expr[0] in ('+', '-', '*'):
        return ast.BinOp(left=expression_ast(expr[1], depth + 1),
                         op={'+': ast.Add, '-': ast.Sub, '*': ast.Mult}[expr[0]](),
                         right=expression_ast(expr[2], depth + 1))
    raise ValueError('SOURCE_IR_OUTSIDE_GRAMMAR')


def source_expression(source):
    if not isinstance(source, str) or len(source.encode()) > 8192:
        raise ValueError('SOURCE_SIZE_BOUND')
    tree = ast.parse(source)
    if len(list(ast.walk(tree))) > 128 or len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError('SOURCE_FUNCTION_SCHEMA')
    fn = tree.body[0]
    args = fn.args
    if (fn.name != 'yado_generated_capability' or fn.decorator_list or fn.returns or fn.type_comment
            or getattr(fn, 'type_params', []) or args.posonlyargs or args.vararg or args.kwarg
            or args.kwonlyargs or args.defaults or args.kw_defaults
            or [a.arg for a in args.args] != ['x', 'y'] or any(a.annotation or a.type_comment for a in args.args)
            or len(fn.body) != 1 or not isinstance(fn.body[0], ast.Return)):
        raise ValueError('SOURCE_FUNCTION_SCHEMA')
    def read(node, depth=0):
        if depth > 12:
            raise ValueError('SOURCE_AST_DEPTH')
        if isinstance(node, ast.Name) and node.id in ('x', 'y'):
            return node.id
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            expression_ast(node.value)
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            value = -read(node.operand, depth + 1)
            expression_ast(value)
            return value
        if isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult):
            return [{ast.Add: '+', ast.Sub: '-', ast.Mult: '*'}[type(node.op)],
                    read(node.left, depth + 1), read(node.right, depth + 1)]
        raise ValueError('SOURCE_AST_OUTSIDE_GRAMMAR')
    return read(fn.body[0].value)


def materialize(expr):
    body = expression_ast(expr)
    source = 'def yado_generated_capability(x, y):\n    return ' + ast.unparse(body) + '\n'
    source_expression(source)
    return source


def interpret(expr, x, y):
    if expr == 'x':
        return x
    if expr == 'y':
        return y
    if type(expr) in (int, float):
        return expr
    a, b = interpret(expr[1], x, y), interpret(expr[2], x, y)
    return {'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b}[expr[0]]()


def execute_source(source, queries):
    source_expression(source)
    namespace = {'__builtins__': {}}
    exec(compile(source, '<yado-bounded-arithmetic>', 'exec'), namespace)
    return [namespace['yado_generated_capability'](q['x'], q['y']) for q in queries]


def execute(kernel, capability, value, strategy, registry):
    value = validate_input(capability, value)
    if capability in COG_STRATEGIES:
        g = {'id': 0, 'spec': {'domain': capability, **value},
             'decision': {'tick': 0, 'workspace_digest': '', 'choice': {'strategy': strategy}}}
        return CognitiveLoop(kernel)._execute(g)['result']
    if capability == 'source_synthesis':
        train, holdout = split_examples(value['rows'])
        model = kernel.parent.synthesize_mathematical_expression(train, max_ops=3, max_states_per_level=10000)
        if model.get('expression') is None:
            return {'status': 'WITHHOLD', 'reason': 'NO_NATIVE_EXPRESSION_IN_BUDGET'}
        source = materialize(model['expression'])
        return {'status': 'CANDIDATE', 'source': source, 'source_sha256': sha(source.encode()),
                'expression': source_expression(source), 'origin': 'YADO_NATIVE_SEMANTIC_SYNTHESIS',
                'predictions': execute_source(source, value['queries']),
                'holdout_predictions': execute_source(source, holdout),
                'train_count': len(train), 'holdout_count': len(holdout)}
    if capability == 'source_apply':
        program = registry[value['capability_id']]
        return {'status': 'CANDIDATE', 'capability_id': value['capability_id'],
                'admission_tick': program['admission_tick'],
                'predictions': execute_source(program['source'], value['queries'])}
    result = kernel._dispatch({'kind': capability.removeprefix('native:'), 'payload': value})
    failed = isinstance(result, dict) and str(result.get('status', '')).startswith(('FAIL', 'ERROR', 'WITHHOLD'))
    return {'status': 'WITHHOLD' if failed else 'CANDIDATE', 'value': result}


def at(value, path):
    for key in path:
        if not isinstance(value, (dict, list, tuple)):
            raise ValueError('BINDING_PATH_NOT_CONTAINER')
        if isinstance(value, (list, tuple)) and type(key) is not int:
            raise ValueError('BINDING_INDEX_REQUIRED')
        value = value[key]
    return value


def verify(capability, value, result, expect, registry):
    if result.get('status') != 'CANDIDATE':
        return {'passed': False, 'checks': 0, 'scope': 'NO_CANDIDATE'}
    try:
        if capability == 'source_apply':
            program = registry[value['capability_id']]
            expr = source_expression(program['source'])
            expected = [interpret(expr, q['x'], q['y']) for q in value['queries']]
            return {'passed': equivalent(result['predictions'], expected)
                    and result['admission_tick'] == program['admission_tick']
                    and result['capability_id'] == value['capability_id'], 'checks': len(expected),
                    'scope': 'REGISTERED_PROGRAM_EQUIVALENCE; GENERALIZATION_NOT_REVERIFIED'}
        if capability == 'source_synthesis':
            expr = source_expression(result['source'])
            _, holdout = split_examples(value['rows'])
            if (sha(result['source'].encode()) != result['source_sha256'] or expr != result['expression']
                    or not equivalent(result['predictions'], [interpret(expr, q['x'], q['y']) for q in value['queries']])
                    or not equivalent(result['holdout_predictions'], [interpret(expr, q['x'], q['y']) for q in holdout])):
                raise ValueError('SOURCE_REALIZATION_MISMATCH')
        if capability in COG_STRATEGIES or capability == 'source_synthesis':
            g = {'id': 0, 'spec': {'domain': 'numeric' if capability == 'source_synthesis' else capability, **value},
                 'decision': {'workspace_digest': ''}, 'execution': {'tick': 0, 'result': result}}
            verified = CognitiveLoop(None)._verify(g)
            return {k: verified[k] for k in ('passed', 'checks', 'scope')}
        if expect is None:
            return {'passed': None, 'checks': 0, 'scope': 'NO_INDEPENDENT_EXPECTATION'}
        return {'passed': equivalent(at(result, expect['path']), expect['equals']),
                'checks': 1, 'scope': 'CALLER_SUPPLIED_EXPECTATION'}
    except (ValueError, KeyError, TypeError, IndexError, SyntaxError, OverflowError):
        return {'passed': False, 'checks': 0, 'scope': 'MALFORMED_CANDIDATE_OR_EXPECTATION'}
