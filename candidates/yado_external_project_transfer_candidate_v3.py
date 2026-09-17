from runtime.yado_external_project_transfer_v3 import run


RECEIPT = run()


def candidate_snapshot():
    return RECEIPT


__all__ = ["RECEIPT", "candidate_snapshot"]
