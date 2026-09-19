"""Additive structured-data goals; legacy scalar goal contracts stay intact."""
import copy
import json
import re

SCHEMA = 'yado.native_program_goal.v1'


def validate_goal(spec):
    if (type(spec) is not dict or set(spec) != {'schema', 'domain', 'training', 'validation', 'queries'}
            or spec['schema'] != SCHEMA or spec['domain'] != 'native_source'):
        raise ValueError('PROGRAM_GOAL_SCHEMA')
    seen, signature, output_type = set(), None, None
    def value(node, budget, depth=0):
        budget[0] -= 1
        if budget[0] < 0 or depth > 16:
            raise ValueError('PROGRAM_VALUE_NODE_OR_DEPTH_BUDGET')
        if node is None or type(node) is bool:
            return
        if type(node) is int and abs(node) <= 10**9:
            return
        if type(node) is str and len(node) <= 8192:
            node.encode('utf-8')
            budget[1] -= len(node)
            if budget[1] < 0:
                raise ValueError('PROGRAM_VALUE_TEXT_BUDGET')
            return
        if type(node) not in (list, dict) or len(node) > 128:
            raise ValueError('PROGRAM_JSON_VALUE_CONTRACT')
        if type(node) is dict:
            if any(type(k) is not str or len(k) > 256 for k in node):
                raise ValueError('PROGRAM_JSON_KEY_CONTRACT')
            for key in node:
                value(key, budget, depth + 1)
            children = node.values()
        else:
            children = node
        for child in children:
            value(child, budget, depth + 1)
    for partition, minimum, maximum in (('training', 3, 64), ('validation', 2, 32), ('queries', 1, 32)):
        rows = spec[partition]
        if type(rows) is not list or not minimum <= len(rows) <= maximum:
            raise ValueError('PROGRAM_EXAMPLE_BUDGET:' + partition)
        for row in rows:
            required = {'input'} if partition == 'queries' else {'input', 'expected'}
            if type(row) is not dict or set(row) != required:
                raise ValueError('PROGRAM_EXAMPLE_SCHEMA')
            inputs = row['input']
            if (type(inputs) is not dict or not 1 <= len(inputs) <= 8
                    or any(type(k) is not str or re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,31}', k) is None
                           for k in inputs)):
                raise ValueError('PROGRAM_NAMED_INPUT_CONTRACT')
            value(row, [2048, 65536])
            current = [(k, type(inputs[k]).__name__) for k in sorted(inputs)]
            if signature is not None and current != signature:
                raise ValueError('PROGRAM_INPUT_SIGNATURE_DRIFT')
            signature = current
            marker = json.dumps(inputs, sort_keys=True, ensure_ascii=True, separators=(',', ':'))
            if marker in seen:
                raise ValueError('PROGRAM_PARTITIONS_MUST_HAVE_DISTINCT_INPUTS')
            seen.add(marker)
            if partition != 'queries':
                current_type = type(row['expected'])
                if output_type is not None and current_type is not output_type:
                    raise ValueError('PROGRAM_OUTPUT_SIGNATURE_DRIFT')
                output_type = current_type
    return copy.deepcopy(spec)
