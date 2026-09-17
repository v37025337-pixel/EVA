from runtime.yado_external_project_training_v1 import route, snapshot, train


TRAINED = train()


def candidate_snapshot():
    result = snapshot()
    result["candidate_branch_only"] = True
    result["training_digest"] = TRAINED["training_digest"]
    result["row_count"] = TRAINED["row_count"]
    return result


__all__ = ["TRAINED", "candidate_snapshot", "route"]
