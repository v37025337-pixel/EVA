from runtime.yado_external_project_evolution_v2 import run


RECEIPT = run()


def candidate_snapshot():
    return RECEIPT


__all__ = ["RECEIPT", "candidate_snapshot"]
