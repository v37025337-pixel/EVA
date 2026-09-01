from __future__ import annotations
import copy

class _ForcedCapabilityRouter:
    def __init__(self,capability):
        self.capability=str(capability)
        self.fallback_output=self.capability
    def execute(self,descriptor):
        return self.capability

class BoundedCapabilitySetCoordinatorV1:
    COMPONENT_ID="ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1"
    MAX_CAPABILITIES=4
    MAX_DEPENDENCY_EDGES=8

    @classmethod
    def order(cls,selected_capabilities,capability_tasks):
        selected=tuple(sorted(set(str(x) for x in selected_capabilities)))
        if not selected or len(selected)>cls.MAX_CAPABILITIES:
            return {"status":"WITHHOLD","reason":"CAPABILITY_SET_BOUND","order":[]}
        if any(c not in capability_tasks for c in selected):
            return {"status":"WITHHOLD","reason":"MISSING_CAPABILITY_TASK","order":[]}
        deps={c:set(str(x) for x in capability_tasks[c].get("requires_capabilities",())) for c in selected}
        if sum(len(v) for v in deps.values())>cls.MAX_DEPENDENCY_EDGES:
            return {"status":"WITHHOLD","reason":"DEPENDENCY_EDGE_BOUND","order":[]}
        if any(d not in selected for xs in deps.values() for d in xs):
            return {"status":"WITHHOLD","reason":"MISSING_REQUIRED_CAPABILITY","order":[]}
        out=[];remaining=set(selected)
        while remaining:
            ready=sorted(c for c in remaining if deps[c].issubset(set(out)))
            if not ready:
                return {"status":"WITHHOLD","reason":"DEPENDENCY_CYCLE","order":[]}
            c=ready[0];out.append(c);remaining.remove(c)
        return {"status":"PASS","reason":"ORDERED","order":out}

    @classmethod
    def run(cls,runtime,selected_capabilities,capability_tasks):
        ordered=cls.order(selected_capabilities,capability_tasks)
        if ordered["status"]!="PASS":return ordered|{"results":{}}
        old_router=runtime.router
        results={}
        try:
            for cap in ordered["order"]:
                task=copy.deepcopy(capability_tasks[cap])
                task.pop("requires_capabilities",None)
                task.setdefault("descriptor",{})
                task.setdefault("stream_id","CAPSET_"+str(len(results)))
                runtime.router=_ForcedCapabilityRouter(cap)
                try:
                    result=runtime.run(task)
                except Exception as exc:
                    return {"status":"WITHHOLD","reason":"SUBTASK_EXECUTION_FAILED","failed_capability":cap,"error_type":type(exc).__name__,"order":ordered["order"],"results":results}
                results[cap]=result
        finally:
            runtime.router=old_router
        return {"status":"PASS","reason":"CAPABILITY_SET_EXECUTED","order":ordered["order"],"results":results}
