def solve(component_id, program_id, inputs):
    return _primitive('not_equal', _primitive('top_level_functions', _primitive('parse_python', _input(inputs, 'after'))), _primitive('top_level_functions', _primitive('parse_python', _input(inputs, 'before'))))
