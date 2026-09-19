def solve(component_id, program_id, inputs):
    return _primitive('json_compact', {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'hive_add_comment', 'arguments': {'id': 'YADO-1', 'message': _input(inputs, 'message')}}})
