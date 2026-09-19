"""Tasks authored by the source_tasks model agent, not by the YADO controller."""
import json

def card(repo):
    return {'full_name': repo, 'html_url': 'https://github.com/' + repo}

def row(repo):
    return {'input': {'record': card(repo)}, 'expected': {'source_id': repo.lower(), 'source_url': card(repo)['html_url']}}

normalization = {
    'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
    'training': [row(x) for x in ['exa-labs/exa-mcp-server','mattpocock/skills','affaan-m/ECC']],
    'validation': [row(x) for x in ['dip497/hivemind','dyad-sh/dyad']],
    'queries': [{'input': {'record': card('hoppscotch/hoppscotch')}}],
}

def document(repo, *, pretty=False, reverse=False):
    value = {'repository': repo, 'url': 'https://github.com/' + repo}
    if reverse:
        value = dict(reversed(list(value.items())))
    return json.dumps(value, indent=2 if pretty else None, separators=None if pretty else (',', ':'))

def pair(a, b, expected, *, pretty=False, reverse=False):
    return {'input': {'before': document(a), 'after': document(b, pretty=pretty, reverse=reverse)}, 'expected': expected}

json_equality = {
    'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
    'training': [pair('exa-labs/exa-mcp-server','exa-labs/exa-mcp-server',True,pretty=True),
                 pair('mattpocock/skills','affaan-m/ECC',False),
                 pair('dip497/hivemind','dip497/hivemind',True,pretty=True)],
    'validation': [pair('affaan-m/ECC','affaan-m/ECC',True,reverse=True),
                   pair('dyad-sh/dyad','hoppscotch/hoppscotch',False)],
    'queries': [{'input': {'before': document('hoppscotch/hoppscotch'),
                          'after': document('hoppscotch/hoppscotch',pretty=True,reverse=True)}}],
}

TASKS = [('source-normalization', normalization), ('json-semantic-equivalence', json_equality)]
PROVENANCE = {'task_author': '/root/source_tasks', 'author_type': 'EXTERNAL_MODEL_AGENT',
              'repository_names_grounded_in_public_sources': True,
              'json_wrappers_and_formatting': 'AGENT_AUTHORED',
              'raw_api_responses': False, 'kernel_endogenous_goals': False,
              'definition_source': 'https://www.rfc-editor.org/info/rfc8259/'}
