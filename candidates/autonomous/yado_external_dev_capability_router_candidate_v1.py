PACK_DIGEST = '3668cb47e84c0d008e7171e3aafde1c2407e2b44274e938e874cb827a803882c'
POLICY_SHA256 = '05f488e43ac584903d784607588194e700a0c52e3e0bd0f9a70392cb03a9d26a'
RULES = {'TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN': ['acceptance', 'agent', 'and', 'branch', 'contract', 'coordinate', 'criteria', 'dip497', 'hivemind', 'isolate', 'issue', 'mcp', 'parallel', 'review', 'supervise', 'supervision', 'task', 'worktree'], 'READ_ONLY_API_ASSERTION_WORKBENCH': ['api', 'assert', 'assertion', 'collections', 'endpoint', 'graphql', 'hoppscotch', 'http', 'post', 'protocol', 'request', 'response', 'schema', 'status', 'websocket'], 'LOCAL_APP_BUILD_ADMISSION_LOOP': ['admission', 'app', 'application', 'bring', 'build', 'builder', 'candidate', 'compile', 'dyad', 'keys', 'loop', 'open', 'own', 'preview', 'regression', 'stack', 'test', 'your'], 'PURE_LOCAL_DEV_UTILITY_LIBRARY': ['base64', 'checker', 'client', 'decode', 'decoder', 'dev', 'diff', 'digest', 'encode', 'format', 'formatter', 'hash', 'json', 'jwt', 'minify', 'nexus', 'nexustools', 'offline', 'pure', 'side', 'tools', 'transform', 'url', 'utility'], 'FREE_TIER_RESOURCE_DISCOVERY': ['and', 'cd', 'ci', 'cloud', 'compute', 'database', 'deploy', 'dev', 'discovery', 'for', 'free', 'hosting', 'iaas', 'major', 'paas', 'providers', 'resource', 'ripienaar', 'serverless', 'storage', 'tier', 'web']}
PRIORITY = ['TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN', 'READ_ONLY_API_ASSERTION_WORKBENCH', 'LOCAL_APP_BUILD_ADMISSION_LOOP', 'PURE_LOCAL_DEV_UTILITY_LIBRARY', 'FREE_TIER_RESOURCE_DISCOVERY']

def _tokens(text):
    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in str(text))
    return set(x for x in cleaned.split() if x)

def route(deficit):
    tokens = _tokens(deficit)
    ranked = []
    for index, capability in enumerate(PRIORITY):
        matched = [word for word in RULES[capability] if word in tokens]
        ranked.append((len(matched), -index, capability, matched))
    ranked.sort(reverse=True)
    if not ranked or ranked[0][0] <= 0:
        return {'status': 'WITHHOLD_ROUTER_NO_MATCH', 'capability': None, 'matched': [], 'pack_digest': PACK_DIGEST, 'policy_sha256': POLICY_SHA256}
    top = ranked[0]
    return {'status': 'PASS_ROUTER_SELECTION', 'capability': top[2], 'matched': top[3], 'score': top[0], 'pack_digest': PACK_DIGEST, 'policy_sha256': POLICY_SHA256}

def snapshot():
    return {'schema': 'yado.external_dev_capability_router_candidate.v1', 'pack_digest': PACK_DIGEST, 'policy_sha256': POLICY_SHA256, 'capability_count': len(PRIORITY), 'automatic_main_mutation': False, 'g3_genesis_performed': False}
