"""Host network transport feeding real public bytes to existing YADO adapters.

The host authors transport and source inventory; YADO performs its existing
bounded evidence checks and router emission. Marker checks are not understanding.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36')]
OUT = Path(sys.argv[1]).resolve()
SOURCES = ['exa-labs/exa-mcp-server', 'dip497/hivemind',
           'NationalSecurityAgency/ghidra', 'ripienaar/free-for-dev',
           'nexustools-dev/nexus-tools', 'dyad-sh/dyad', 'hoppscotch/hoppscotch',
           'mattpocock/skills', 'affaan-m/ECC']
CORPUS = OUT / 'public-source-bytes'
CORPUS.mkdir(exist_ok=True)

def save(name, data):
    (OUT / (name + '.json')).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def fetch(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'api.github.com', 'raw.githubusercontent.com'}:
        raise ValueError('UNEXPECTED_PUBLIC_SOURCE')
    req = urllib.request.Request(url, headers={'User-Agent': 'YADO-source-learning/1.0', 'Accept': 'application/vnd.github+json,text/plain'})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('SOURCE_TOO_LARGE')
        final = response.url
    content = raw.decode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    (CORPUS / (digest + '.txt')).write_bytes(raw)
    receipt = {'url': url, 'final_url': final, 'sha256': digest,
               'read_only': True, 'credentials_used': False, 'external_write': False,
               'private_network_access': False, 'downloaded_code_executed': False,
               'transport': 'HOST_HTTPS_PUBLIC_FETCH', 'bytes': len(raw)}
    return {'content': content, 'receipt': receipt}

def capture(repo):
    try:
        meta = fetch('https://api.github.com/repos/' + repo)
        metadata = json.loads(meta['content'])
        readme = fetch('https://raw.githubusercontent.com/' + metadata['full_name'] + '/' + metadata['default_branch'] + '/README.md')
        return {'requested_repo': repo, 'repo': metadata['full_name'], 'status': 'FETCHED_REAL_CONTENT',
                'metadata': meta['receipt'], 'readme': readme['receipt'],
                'license': (metadata.get('license') or {}).get('spdx_id')}
    except Exception as exc:
        return {'requested_repo': repo, 'status': 'WITHHOLD', 'error': type(exc).__name__ + ':' + str(exc)}

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    inventory = list(pool.map(capture, SOURCES))
save('screenshot-source-inventory', inventory)
print(json.dumps({'stage': 'inventory', 'fetched': sum(x['status'] == 'FETCHED_REAL_CONTENT' for x in inventory), 'total': len(inventory)}), flush=True)

from yado_unified_core_external_tool_ecosystem_learning_v1 import UnifiedYADOCoreExternalToolEcosystemLearningV1
from yado_unified_core_external_dev_self_development_v1 import UnifiedYADOCoreExternalDevSelfDevelopmentV1
from yado_external_dev_self_development_v1 import ExternalDevSelfDevelopmentV1
for name in ('ecosystem', 'repository-development'):
    try:
        if name == 'ecosystem':
            core = UnifiedYADOCoreExternalToolEcosystemLearningV1(ROOT)
            result = core.study_external_tool_ecosystem(fetch_override=fetch, repo_root=ROOT)
        else:
            core = UnifiedYADOCoreExternalDevSelfDevelopmentV1(ROOT)
            result = core.external_dev_self_develop('Study the user-specified developer repositories and evaluate a native capability router',
                fetch_override=fetch, candidate_path=OUT/'repository-router.py', receipt_path=OUT/'repository-router-receipt.json')
            if (OUT/'repository-router.py').exists():
                before = ExternalDevSelfDevelopmentV1.evaluate_router_source((ROOT/'candidates/autonomous/yado_external_dev_capability_router_candidate_v1.py').read_text())
                after = ExternalDevSelfDevelopmentV1.evaluate_router_source((OUT/'repository-router.py').read_text())
                save('router-comparison', {'before_accuracy': before['accuracy'], 'after_accuracy': after['accuracy'],
                     'gain': after['accuracy']-before['accuracy'], 'benchmark': 'EXISTING_FIVE_CASE_SUITE', 'new_blind_benchmark': False})
        result['network_transport_authorship'] = 'ASSISTANT'
        result['external_docs_are_untrusted_data'] = True
    except Exception as exc:
        result = {'status': 'WITHHOLD', 'error': type(exc).__name__ + ':' + str(exc)}
    save(name+'-host-transport', result)
    print(json.dumps({'stage':name, 'status':result['status']}), flush=True)
