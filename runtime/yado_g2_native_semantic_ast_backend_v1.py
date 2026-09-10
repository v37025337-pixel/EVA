"""Reusable, non-executing transport for the existing V12/V17/V18 AST lineage.

The placement algorithm below is extracted from V18. It supplies no new edit
semantics. A different goal needs its own native semantic operator and evidence.
"""
from pathlib import Path
import ast, builtins, copy, hashlib, json


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value):
    return hashlib.sha256(canon(value).encode()).hexdigest()


def sha_text(source):
    return hashlib.sha256(source.encode()).hexdigest()


def checked_path(repo, relative):
    path = (Path(repo) / relative).resolve()
    if not path.is_relative_to(Path(repo).resolve()):
        raise ValueError("LINEAGE_PATH_OUTSIDE_REPOSITORY")
    return path


def load_verified(repo, relative, digest_key="receipt_sha256"):
    path = checked_path(repo, relative)
    data = json.loads(path.read_text(encoding="utf-8"))
    unsigned = {k: v for k, v in data.items() if k != digest_key}
    if data.get(digest_key) != digest(unsigned):
        raise ValueError("LINEAGE_DIGEST_MISMATCH:" + relative)
    return data


def load_bundle(repo):
    """Use the existing lineage contract, never a caller-supplied patch or AST."""
    request_path = "architecture/yado-kernel-native-context-bound-ast-source-realization-v18-request.json"
    request = json.loads(checked_path(repo, request_path).read_text())
    parents = request["parents"]
    sem = load_verified(repo, parents["semantic_edit_gene"])
    context = load_verified(repo, parents["v17_context_gene"], "gene_digest")
    operand = load_verified(repo, parents["v12_ifexp_gene"], "gene_digest")
    binding = load_verified(repo, parents["kernel_provenant_target_binding"])
    v17 = load_verified(repo, parents["v17_receipt"])
    v18_path = "candidates/kernel-self-generated/g2-native-context-bound-ast-source-realization-v18.json"
    v18 = load_verified(repo, v18_path)
    serializer_path = "candidates/kernel-self-generated/g2-target-semantic-source-constructor-genesis-v5.json"
    serializer = load_verified(repo, serializer_path)
    if not all(str(row.get("status", "")).startswith("PASS_SHADOW_") for row in (sem, v18, serializer)):
        raise ValueError("NATIVE_LINEAGE_NOT_VALIDATED")
    if serializer.get("selected_primitive") != "unparse":
        raise ValueError("UNSUPPORTED_NATIVE_SERIALIZER")
    if context.get("v12_operand_materialization_gene_id") != operand.get("gene_id"):
        raise ValueError("NATIVE_OPERAND_CONTEXT_LINEAGE_MISMATCH")
    if context.get("all_context_dependencies_bound") is not True:
        raise ValueError("NATIVE_CONTEXT_INCOMPLETE")
    target = binding["target_path"]
    if target != v18.get("kernel_provenant_target_path"):
        raise ValueError("NATIVE_TARGET_LINEAGE_MISMATCH")
    if not target.startswith("runtime/") or not target.endswith(".py"):
        raise ValueError("NATIVE_TARGET_NOT_RUNTIME_PYTHON")
    checked_path(repo, target)
    files = sorted(set(parents.values()) | {request_path, v18_path, serializer_path})
    return {"anchor": sem["meta_language_gene"]["operator_program"]["anchor_contract"],
            "operand": operand, "context": context, "target_path": target,
            "parent_sha256": v18["parent_source_sha256"],
            "historical_candidate_sha256": v18["candidate_source_sha256"],
            "current_context_status": v17.get("status"),
            "current_context_ready": str(v17.get("status", "")).startswith("PASS_SHADOW_"),
            "gene_id": sem["meta_language_gene"]["gene_id"],
            "lineage_sha256": {rel: hashlib.sha256(checked_path(repo, rel).read_bytes()).hexdigest() for rel in files}}


def materialize_source(bundle, parent_source):
    if sha_text(parent_source) != bundle["parent_sha256"]:
        raise ValueError("NATIVE_PARENT_SOURCE_DRIFT")
    anchor = bundle["anchor"]
    g12, g17 = bundle["operand"], bundle["context"]
    tree=ast.parse(parent_source)

    # Find the target call only from the YADO-created semantic anchor.
    call_name=str(anchor.get('call_name') or '')
    finding_code=str(anchor.get('finding_code') or '')
    required_status=anchor.get('required_before_status_value')
    target_call=None
    target_index=None
    for i,stmt in enumerate(tree.body):
        if not isinstance(stmt,ast.Expr) or not isinstance(stmt.value,ast.Call):
            continue
        call=stmt.value
        if not isinstance(call.func,ast.Name) or call.func.id!=call_name or len(call.args)<4:
            continue
        if isinstance(call.args[0],ast.Constant) and call.args[0].value==finding_code:
            target_call=call;target_index=i;break
    if target_call is None:
        raise RuntimeError('YADO_ANCHOR_NOT_FOUND')
    if not isinstance(target_call.args[3],ast.Constant) or target_call.args[3].value!=required_status:
        raise RuntimeError('YADO_ANCHOR_STATUS_DRIFT')

    # Parse the replacement expression that YADO already materialized in V12.
    ifexp_expr=ast.parse(str(g12['materialized_ifexp_source']),mode='eval').body
    if not isinstance(ifexp_expr,ast.IfExp):
        raise RuntimeError('V12_NOT_IFEXP')

    def stored_names(node):
        return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Param))}

    def loaded_names(node):
        stores=stored_names(node)
        return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}-stores

    ifexp_free=sorted(loaded_names(ifexp_expr)-set(dir(builtins)))
    expected_free=sorted(str(x) for x in g17.get('full_free_context_names',[]))
    if ifexp_free!=expected_free:
        raise RuntimeError(f'V12_V17_FREE_CONTEXT_MISMATCH:{ifexp_free}:{expected_free}')

    # Determine names already bound before the target anchor in the kernel-provenant source.
    def defined_by_stmt(stmt):
        out=set()
        if isinstance(stmt,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            out.add(stmt.name)
        elif isinstance(stmt,(ast.Assign,ast.AnnAssign)):
            for n in ast.walk(stmt):
                if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store): out.add(n.id)
        elif isinstance(stmt,ast.Import):
            for a in stmt.names: out.add(a.asname or a.name.split('.')[0])
        elif isinstance(stmt,ast.ImportFrom):
            for a in stmt.names: out.add(a.asname or a.name)
        return out

    defined=set()
    for stmt in tree.body[:target_index]:
        defined |= defined_by_stmt(stmt)

    closure=g17.get('context_closure') or {}

    def materialize_binding(name,row):
        kind=row.get('kind')
        if kind=='IMPORT':
            parsed=ast.parse(str(row['source'])).body
            if len(parsed)!=1: raise RuntimeError('BAD_IMPORT_BINDING:'+name)
            return parsed[0]
        if kind=='SIMPLE_ASSIGN':
            return ast.Assign(
                targets=[ast.Name(id=name,ctx=ast.Store())],
                value=ast.parse(str(row['rhs_source']),mode='eval').body,
            )
        if kind=='FEATURE_DICT_EXPRESSION':
            return ast.Assign(
                targets=[ast.Name(id=name,ctx=ast.Store())],
                value=ast.parse(str(row['rhs_source']),mode='eval').body,
            )
        if kind=='UNPACK_MAP_ARTIFACT_BINDING':
            src=ast.parse(str(row['source_statement'])).body
            if len(src)!=1 or not isinstance(src[0],ast.Assign):
                raise RuntimeError('BAD_UNPACK_BINDING:'+name)
            assign=src[0]
            if not assign.targets or not isinstance(assign.targets[0],(ast.Tuple,ast.List)):
                raise RuntimeError('BAD_UNPACK_TARGETS:'+name)
            targets=assign.targets[0].elts
            if not isinstance(assign.value,ast.Call) or len(assign.value.args)<2:
                raise RuntimeError('BAD_UNPACK_CALL:'+name)
            seq=assign.value.args[1]
            if not isinstance(seq,(ast.List,ast.Tuple)):
                raise RuntimeError('BAD_UNPACK_SEQUENCE:'+name)
            target_names=[x.id if isinstance(x,ast.Name) else None for x in targets]
            if name not in target_names:
                raise RuntimeError('UNPACK_NAME_NOT_FOUND:'+name)
            idx=target_names.index(name)
            if idx>=len(seq.elts):
                raise RuntimeError('UNPACK_ARITY_MISMATCH:'+name)
            loader=str(row.get('loader_name') or '')
            if not loader: raise RuntimeError('UNPACK_LOADER_MISSING:'+name)
            return ast.Assign(
                targets=[ast.Name(id=name,ctx=ast.Store())],
                value=ast.Call(func=ast.Name(id=loader,ctx=ast.Load()),args=[copy.deepcopy(seq.elts[idx])],keywords=[]),
            )
        if kind in ('FUNCTION','BUILTIN','RUNTIME_INTRINSIC'):
            return None
        raise RuntimeError('UNSUPPORTED_CONTEXT_BINDING:'+name+':'+str(kind))

    stmt_by_name={}
    for name,row in closure.items():
        if name in defined:
            continue
        stmt=materialize_binding(name,row)
        if stmt is not None:
            stmt_by_name[name]=stmt

    # Only materialize the dependency closure needed by the V12 expression.
    needed=set(expected_free)
    changed=True
    while changed:
        changed=False
        for name in list(needed):
            stmt=stmt_by_name.get(name)
            if stmt is None: continue
            deps=loaded_names(stmt)-set(dir(builtins))
            for dep in deps:
                if dep not in defined and dep not in needed:
                    needed.add(dep);changed=True

    # Topological order over YADO-provided bindings.
    ordered=[]
    available=set(defined)|set(dir(builtins))
    pending={k:v for k,v in stmt_by_name.items() if k in needed}
    while pending:
        progress=False
        for name in sorted(list(pending)):
            stmt=pending[name]
            deps=loaded_names(stmt)-available
            deps-=defined_by_stmt(stmt)
            if not deps:
                ordered.append(stmt);available |= defined_by_stmt(stmt);pending.pop(name);progress=True
        if not progress:
            unresolved={k:sorted(loaded_names(v)-available-defined_by_stmt(v)) for k,v in pending.items()}
            raise RuntimeError('V17_CONTEXT_TOPOLOGY_UNRESOLVED:'+canon(unresolved))

    # Build the candidate by inserting only gene-derived context bindings and replacing
    # only the anchored status with the V12 YADO-materialized IfExp.
    candidate_tree=copy.deepcopy(tree)
    candidate_call=None
    candidate_index=None
    for i,stmt in enumerate(candidate_tree.body):
        if not isinstance(stmt,ast.Expr) or not isinstance(stmt.value,ast.Call): continue
        call=stmt.value
        if not isinstance(call.func,ast.Name) or call.func.id!=call_name or len(call.args)<4: continue
        if isinstance(call.args[0],ast.Constant) and call.args[0].value==finding_code:
            candidate_call=call;candidate_index=i;break
    if candidate_call is None: raise RuntimeError('CANDIDATE_ANCHOR_NOT_FOUND')

    context_nodes=[copy.deepcopy(x) for x in ordered]
    candidate_tree.body[candidate_index:candidate_index]=context_nodes
    candidate_call.args[3]=copy.deepcopy(ifexp_expr)
    ast.fix_missing_locations(candidate_tree)
    candidate_source=ast.unparse(candidate_tree)+'\n'
    compile(candidate_source,'<yado-v18-candidate>','exec')
    candidate_sha=sha_text(candidate_source)
    return candidate_source


def propose(repo, priority):
    bundle = load_bundle(repo)
    contract = bundle["anchor"]["finding_code"]
    result = {"backend": "NATIVE_SEMANTIC_AST_V12_V17_V18",
              "available_semantic_contracts": [contract],
              "requested_contract": priority.get("code"),
              "current_context_status": bundle["current_context_status"],
              "lineage_sha256": bundle["lineage_sha256"],
              "candidate_source": None, "target_path": None,
              "external_models_used": False, "candidate_executed": False,
              "host_authored_transport": True, "host_authored_new_edit_semantics": False}
    if priority.get("origin") == "EXTERNAL_REQUEST" or priority.get("code") != contract:
        result.update(status="WITHHOLD_NO_NATIVE_SEMANTIC_OPERATOR_FOR_GOAL",
                      next_required_capability="FRESH_GOAL_CONDITIONED_NATIVE_SEMANTIC_EDIT_GENESIS")
        return result
    if not bundle["current_context_ready"]:
        result.update(status="WITHHOLD_CURRENT_NATIVE_CONTEXT_NOT_VALIDATED",
                      next_required_capability="CURRENT_EVIDENCE_BOUND_NATIVE_CONTEXT_VALIDATION")
        return result
    path = checked_path(repo, bundle["target_path"])
    parent = path.read_text(encoding="utf-8")
    if sha_text(parent) != bundle["parent_sha256"]:
        result.update(status="WITHHOLD_NATIVE_PARENT_SOURCE_DRIFT",
                      next_required_capability="CURRENT_TARGET_BOUND_NATIVE_SEMANTIC_EDIT_GENESIS")
        return result
    source = materialize_source(bundle, parent)
    result.update(status="NATIVE_SOURCE_EMITTED_PENDING_FRESH_GATE", candidate_source=source,
                  candidate_sha256=sha_text(source), parent_sha256=sha_text(parent),
                  target_path=bundle["target_path"], gene_id=bundle["gene_id"],
                  compile_pass=True)
    return result
