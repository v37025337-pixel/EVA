from runtime.yado_external_project_bridge_v1 import PROJECTS, route_task, snapshot


def candidate_snapshot():
    result = snapshot()
    result["candidate_branch_only"] = True
    result["project_ids"] = [project.project_id for project in PROJECTS]
    return result


__all__ = ["candidate_snapshot", "route_task"]
