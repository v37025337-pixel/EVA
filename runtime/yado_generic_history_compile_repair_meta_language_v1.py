from __future__ import annotations
import copy,difflib,hashlib,itertools,json

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class GenericHistoryCompileRepairMetaLanguageV1:
    COMPONENT_ID='LANG-G2-GENERIC-HISTORY-COMPILE-REPAIR-META-V1'
    ANCESTOR_POLICIES=('NEAREST_COMPILING','ALL_COMPILING')
    MAX_HUNKS=(1,2,3)
    RANKINGS=('MIN_HUNKS_THEN_LINES','MIN_LINES_THEN_HUNKS','MIN_DISTANCE_TO_ERROR_THEN_LINES')

    @staticmethod
    def compile_error(source):
        try:
            compile(source,'<yado-history-repair>','exec')
            return None
        except SyntaxError as e:
            return {'msg':str(e.msg),'lineno':e.lineno,'offset':e.offset}

    @staticmethod
    def _opcodes(current,ancestor):
        a=current.splitlines(keepends=True)
        b=ancestor.splitlines(keepends=True)
        sm=difflib.SequenceMatcher(a=a,b=b,autojunk=False)
        ops=[]
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag!='equal':
                ops.append({'tag':tag,'i1':i1,'i2':i2,'j1':j1,'j2':j2})
        return a,b,ops

    @staticmethod
    def _apply_subset(cur_lines,anc_lines,ops,subset):
        out=list(cur_lines)
        for idx in sorted(subset,key=lambda k:ops[k]['i1'],reverse=True):
            op=ops[idx]
            out[op['i1']:op['i2']]=anc_lines[op['j1']:op['j2']]
        return ''.join(out)

    @classmethod
    def repair(cls,program,current,history):
        if cls.compile_error(current) is None:
            return {'source':current,'status':'ALREADY_COMPILES','ancestor_index':None,'reverted_hunks':[]}
        compiling=[(i,s) for i,s in enumerate(history) if isinstance(s,str) and cls.compile_error(s) is None]
        if not compiling:
            return {'source':None,'status':'NO_COMPILING_ANCESTOR'}
        if program['ancestor_policy']=='NEAREST_COMPILING':
            compiling=compiling[:1]
        candidates=[]
        err=cls.compile_error(current) or {}
        err_line=max(1,int(err.get('lineno') or 1))-1
        for anc_index,ancestor in compiling:
            cur,anc,ops=cls._opcodes(current,ancestor)
            if not ops:
                continue
            limit=min(int(program['max_hunks']),len(ops))
            for width in range(1,limit+1):
                for subset in itertools.combinations(range(len(ops)),width):
                    cand=cls._apply_subset(cur,anc,ops,subset)
                    if cls.compile_error(cand) is not None:
                        continue
                    line_cost=sum(max(1,ops[k]['i2']-ops[k]['i1'],ops[k]['j2']-ops[k]['j1']) for k in subset)
                    distance=min(abs(ops[k]['i1']-err_line) for k in subset)
                    if program['ranking']=='MIN_HUNKS_THEN_LINES':
                        rank=(width,line_cost,distance,anc_index,subset)
                    elif program['ranking']=='MIN_LINES_THEN_HUNKS':
                        rank=(line_cost,width,distance,anc_index,subset)
                    else:
                        rank=(distance,line_cost,width,anc_index,subset)
                    candidates.append((rank,cand,anc_index,list(subset),line_cost,distance))
        if not candidates:
            return {'source':None,'status':'NO_COMPILE_RESTORE_WITHIN_BUDGET'}
        candidates.sort(key=lambda x:x[0])
        rank,cand,anc_index,subset,line_cost,distance=candidates[0]
        return {
          'source':cand,'status':'REPAIRED','ancestor_index':anc_index,
          'reverted_hunks':subset,'line_cost':line_cost,'error_distance':distance,
          'candidate_count':len(candidates)
        }

    @classmethod
    def programs(cls):
        for ap,mh,rk in itertools.product(cls.ANCESTOR_POLICIES,cls.MAX_HUNKS,cls.RANKINGS):
            p={'schema':'yado.g2.generic_history_compile_repair_program.v1',
               'ancestor_policy':ap,'max_hunks':mh,'ranking':rk,
               'primitive_sequence':['SCAN_HISTORY','FILTER_COMPILING','DIFF_HUNKS','SEARCH_HUNK_SUBSETS','COMPILE_ORACLE','RANK_MINIMAL_REPAIR']}
            p['program_digest']=_digest(p)
            yield p

    @classmethod
    def accuracy(cls,program,examples):
        if not examples:return 0.0
        ok=0
        for row in examples:
            got=cls.repair(program,row['current'],row['history']).get('source')
            ok+=(got==row['expected'])
        return ok/len(examples)

    @classmethod
    def whole_ancestor_baseline(cls,examples):
        if not examples:return 0.0
        ok=0
        for row in examples:
            candidate=next((s for s in row['history'] if cls.compile_error(s) is None),None)
            ok+=(candidate==row['expected'])
        return ok/len(examples)

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.generic_history_compile_repair_meta_language.v1',
          'component_id':cls.COMPONENT_ID,
          'primitives':['SCAN_HISTORY','FILTER_COMPILING','DIFF_HUNKS','SEARCH_HUNK_SUBSETS','COMPILE_ORACLE','RANK_MINIMAL_REPAIR'],
          'ancestor_policies':list(cls.ANCESTOR_POLICIES),'max_hunks':list(cls.MAX_HUNKS),'rankings':list(cls.RANKINGS),
          'target_patch_encoded':False,'external_model_required':False,'bounded_search':True,
          'semantic_boundary':'GENERIC HISTORY-GUIDED COMPILE REPAIR. IT SEARCHES MINIMAL REVERSION SUBSETS AGAINST COMPILING ANCESTORS; IT DOES NOT CONTAIN THE TARGET FILE LINE NUMBER, PATCH TEXT, OR EXPECTED REPAIRED SOURCE.'
        }
        x['component_digest']=_digest(x);return x

__all__=['GenericHistoryCompileRepairMetaLanguageV1']
