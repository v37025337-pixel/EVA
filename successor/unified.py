"""python -m successor.unified: build, submit, run, status, stop, rehearse, export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .assembly import build, rehearse
from .graph import CausalGraph
from .kernel import SuccessorKernel, encode


def export(graph, output):
    state = graph.snapshot()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'state.json').write_text(encode(state) + '\n')
    paths = []
    for digest, program in state['learned_capabilities'].items():
        path = output / ('learned_capability_' + digest + '.py')
        path.write_text(program['source'])
        paths.append(str(path))
    return {'status': 'EXPORTED', 'directory': str(output), 'source_files': paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    builder = sub.add_parser('build')
    builder.add_argument('--output', required=True); builder.add_argument('--external-root'); builder.add_argument('--catalog')
    for command in ('submit', 'run', 'status', 'stop', 'rehearse', 'export'):
        item = sub.add_parser(command)
        item.add_argument('--manifest', required=True); item.add_argument('--state', required=True)
        if command == 'submit':
            item.add_argument('--input', required=True)
        elif command == 'run':
            item.add_argument('--max-steps', type=int, default=20)
        elif command == 'stop':
            item.add_argument('--goal-id', type=int, required=True)
        elif command == 'rehearse':
            item.add_argument('--limit', type=int, default=12)
        elif command == 'export':
            item.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'build':
        result = build(args.output, args.external_root, args.catalog)
    else:
        kernel = SuccessorKernel(args.manifest, args.state)
        graph = CausalGraph(kernel)
        try:
            if args.command == 'submit':
                result = {'goal_id': graph.submit(json.loads(Path(args.input).read_text()))}
            elif args.command == 'run':
                result = {'steps': len(graph.run(args.max_steps)), 'state': graph.snapshot()}
            elif args.command == 'status':
                result = graph.snapshot()
            elif args.command == 'stop':
                result = graph.stop(args.goal_id)
            elif args.command == 'rehearse':
                result = {'goal_ids': rehearse(graph, args.limit)}
            else:
                result = export(graph, args.output)
        finally:
            kernel.close()
    print(encode(result))


if __name__ == '__main__':
    main()
