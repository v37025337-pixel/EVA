from __future__ import annotations
import hashlib,json
from yado_openapi_adapter_runtime import OpenAPIContractRuntime

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class G2OpenAPIContractCapabilityV1:
    COMPONENT_ID="ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1"

    def __init__(self,state_section:dict|None=None):
        self.runtime=OpenAPIContractRuntime(state_section or {})

    def classify(self,contract_id:str):
        out=self.runtime.classify(contract_id)
        return dict(out)|{"network_execute":False,"capability_id":self.COMPONENT_ID}

    def compile_plan(self,contract_id:str):
        out=self.runtime.compile_plan(contract_id)
        if out.get("network_execute") is not False:
            raise RuntimeError("OPENAPI_NETWORK_EXECUTION_MUST_REMAIN_DISABLED")
        out=dict(out)
        out["capability_id"]=self.COMPONENT_ID
        out["execution_boundary"]="CONTRACT_CLASSIFICATION_AND_PLAN_ONLY"
        return out

    @classmethod
    def component(cls):
        x={
          "schema":"yado.g2.openapi_contract_capability.v1",
          "component_id":cls.COMPONENT_ID,
          "substrate":"runtime/yado_rc8_v36/yado_openapi_adapter_runtime.py",
          "network_execute":False,
          "read_only_contract_planning":True,
          "credential_gate_preserved":True,
          "evidence_gate_preserved":True,
          "primary_verification_gate_preserved":True,
          "architecture_mutation":False,
          "canonical_active":False,
        }
        x["component_digest"]=_digest(x)
        return x

__all__=["G2OpenAPIContractCapabilityV1"]
