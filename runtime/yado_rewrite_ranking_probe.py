"""Subprocess probe for a structurally checked evidence-binding candidate.

Audit hooks restrict side effects; this is not an OS sandbox for arbitrary code.
The caller must verify provenance and the literal-only AST delta before execution.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys


def main():
    request = json.load(sys.stdin)
    source = Path(request['source']).resolve(strict=True)
    if hashlib.sha256(source.read_bytes()).hexdigest() != request['sha256']:
        raise ValueError('PROBE_SOURCE_HASH_MISMATCH')
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
    sys.dont_write_bytecode = True
    sys.path.insert(0, request['runtime_directory'])

    def restrict(event, args):
        if event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event in {
            'os.system', 'os.remove', 'os.rename', 'os.rmdir', 'os.mkdir', 'os.link', 'os.symlink'}:
            raise RuntimeError('PROBE_SIDE_EFFECT_REJECTED:' + event)
        if event == 'open':
            mode, flags = args[1], args[2]
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
                raise RuntimeError('PROBE_FILE_WRITE_REJECTED')

    sys.addaudithook(restrict)
    spec = importlib.util.spec_from_file_location('yado_ranking_candidate', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rankings = [[{'id': row['id'], 'score': row['score']}
                 for row in module.rank_sources(priority)] for priority in request['priorities']]
    print(json.dumps({'rankings': rankings, 'selection_limit': module.MAX_SOURCES_PER_RUN,
                      'pid': os.getpid()}, sort_keys=True))


if __name__ == '__main__':
    main()
