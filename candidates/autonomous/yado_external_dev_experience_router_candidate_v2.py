BASE_ROUTER_SOURCE_SHA256 = '15dfa3369bc64427a33acd4480ad763c51fb869942d1489e438a76a03b1a337d'
BASE_POLICY_SHA256 = '05f488e43ac584903d784607588194e700a0c52e3e0bd0f9a70392cb03a9d26a'
PACK_DIGEST = '3668cb47e84c0d008e7171e3aafde1c2407e2b44274e938e874cb827a803882c'
TRAINING_DIGEST = '9108379d4bb04f82804a090f745fef8ab885554088012e864e66b5fe85c00485'
WEIGHTS = {'TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN': {'coordinate': 3, 'criteria': 6, 'review': 6}, 'READ_ONLY_API_ASSERTION_WORKBENCH': {'endpoint': 6, 'graphql': 3, 'response': 6}, 'LOCAL_APP_BUILD_ADMISSION_LOOP': {'admission': 6, 'build': 3, 'candidate': 8, 'compile': 9, 'preview': 6, 'regression': 9, 'test': 5}, 'PURE_LOCAL_DEV_UTILITY_LIBRARY': {'digest': 12, 'hash': 6, 'json': 3, 'offline': 12}, 'FREE_TIER_RESOURCE_DISCOVERY': {'compute': 4, 'for': 5, 'free': 4, 'resource': 3, 'serverless': 6}}
PRIORITY = ['TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN', 'READ_ONLY_API_ASSERTION_WORKBENCH', 'LOCAL_APP_BUILD_ADMISSION_LOOP', 'PURE_LOCAL_DEV_UTILITY_LIBRARY', 'FREE_TIER_RESOURCE_DISCOVERY']

def _tokens(text):
    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in str(text))
    return set(x for x in cleaned.split() if x)

def route(deficit):
    tokens = _tokens(deficit)
    ranked = []
    for index, capability in enumerate(PRIORITY):
        profile = WEIGHTS[capability]
        matched = [word for word in profile if word in tokens]
        raw = sum(profile[word] for word in matched)
        total = sum(profile.values())
        score = (raw / total) if total else 0.0
        ranked.append((score, -index, capability, matched, raw, total))
    ranked.sort(reverse=True)
    if not ranked or ranked[0][0] <= 0.0:
        return {'status': 'WITHHOLD_ROUTER_NO_MATCH', 'capability': None, 'matched': [], 'score': 0.0, 'pack_digest': PACK_DIGEST, 'training_digest': TRAINING_DIGEST}
    top = ranked[0]
    return {'status': 'PASS_ROUTER_SELECTION', 'capability': top[2], 'matched': top[3], 'score': top[0], 'raw_score': top[4], 'profile_total': top[5], 'pack_digest': PACK_DIGEST, 'training_digest': TRAINING_DIGEST}

def snapshot():
    return {'schema': 'yado.external_dev_experience_router_candidate.v2', 'base_policy_sha256': BASE_POLICY_SHA256, 'training_digest': TRAINING_DIGEST, 'capability_count': len(PRIORITY), 'scoring': 'NORMALIZED_EXPERIENCE_WEIGHTED_COVERAGE', 'automatic_main_mutation': False, 'g3_genesis_performed': False}
