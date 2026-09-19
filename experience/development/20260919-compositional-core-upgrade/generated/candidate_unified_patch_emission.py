def solve(component_id, program_id, inputs):
    return _primitive('join', _primitive('unified_diff', _primitive('splitlines', _input(inputs, 'before')), _primitive('splitlines', _input(inputs, 'after')), 'a/target.py', 'b/target.py'))
