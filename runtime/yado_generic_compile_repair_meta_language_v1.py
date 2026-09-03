from __future__ import annotations
import copy,hashlib,itertools,json

def _canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o): return hashlib.sha256(_canon(o).encode()).hexdigest()

class GenericCompileRepairMetaLanguageV1:
    COMPONENT_ID='LANG-G2-GENERIC-COMPILE-REPAIR-META-V1'
    ANCHORS=('ERROR_OFFSET','ERROR_OFFSET_MINUS1','ERROR_OFFSET_PLUS1','LINE_END_MINUS1','LINE_END')
    ACTIONS=('DELETE','INSERT','REPLACE')
    CHARS=tuple('()[]{}')

    @staticmethod
    def _compile_error(source):
        try:
            compile(source,'<yado-compile-repair>','exec')
            return None
        except SyntaxError as e:
            return {'msg':str(e.msg),'lineno':e.lineno,'offset':e.offset}

    @classmethod
    def _absolute_positions(cls,source,error):
        lines=source.splitlines(keepends=True)
        ln=int(error.get('lineno') or 1)
        if ln<1 or ln>len(lines):
            return {}
        start=sum(len(x) for x in lines[:ln-1])
        raw=lines[ln-1]
        logical=raw.rstrip('\r\n')
        base=start+max(0,int(error.get('offset') or 1)-1)
        end=start+len(logical)
        return {
          'ERROR_OFFSET':base,
          'ERROR_OFFSET_MINUS1':max(start,base-1),
          'ERROR_OFFSET_PLUS1':min(end,base+1),
          'LINE_END_MINUS1':max(start,end-1),
          'LINE_END':end,
        }

    @classmethod
    def execute(cls,program,source):
        err=cls._compile_error(source)
        if err is None:
            return source
        positions=cls._absolute_positions(source,err)
        pos=positions.get(program['anchor'])
        if pos is None:
            return None
        action=program['action']
        ch=program.get('char')
        if action=='DELETE':
            if pos>=len(source): return None
            candidate=source[:pos]+source[pos+1:]
        elif action=='INSERT':
            candidate=source[:pos]+str(ch)+source[pos:]
        elif action=='REPLACE':
            if pos>=len(source): return None
            candidate=source[:pos]+str(ch)+source[pos+1:]
        else:
            return None
        return candidate if cls._compile_error(candidate) is None else None

    @classmethod
    def programs(cls):
        for anchor in cls.ANCHORS:
            p={'schema':'yado.g2.generic_compile_repair_program.v1','anchor':anchor,'action':'DELETE','char':None,'max_edits':1}
            p['program_digest']=_digest(p); yield p
            for action in ('INSERT','REPLACE'):
                for ch in cls.CHARS:
                    p={'schema':'yado.g2.generic_compile_repair_program.v1','anchor':anchor,'action':action,'char':ch,'max_edits':1}
                    p['program_digest']=_digest(p); yield p

    @classmethod
    def accuracy(cls,program,examples):
        if not examples: return 0.0
        ok=0
        for row in examples:
            got=cls.execute(program,row['broken'])
            ok += (got==row['expected'])
        return ok/len(examples)

    @classmethod
    def ablations(cls,program):
        out=[]
        for a in cls.ANCHORS:
            if a==program['anchor']: continue
            p=copy.deepcopy(program); p['anchor']=a; p['program_digest']=_digest({k:v for k,v in p.items() if k!='program_digest'})
            out.append({'field':'anchor','value':a,'program':p})
        for action in cls.ACTIONS:
            if action==program['action']: continue
            chars=(None,) if action=='DELETE' else cls.CHARS
            for ch in chars:
                p=copy.deepcopy(program); p['action']=action; p['char']=ch
                p['program_digest']=_digest({k:v for k,v in p.items() if k!='program_digest'})
                out.append({'field':'action','value':action,'char':ch,'program':p})
        return out

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.generic_compile_repair_meta_language.v1',
          'component_id':cls.COMPONENT_ID,
          'primitives':['COMPILER_ERROR_LOCATION','LOCAL_CHARACTER_EDIT','INSERT','DELETE','REPLACE','COMPILE_ORACLE'],
          'anchors':list(cls.ANCHORS),'actions':list(cls.ACTIONS),'characters':list(cls.CHARS),
          'single_edit_only':True,'bounded_search':True,
          'domain_specific_patch_encoded':False,
          'semantic_boundary':'GENERIC SINGLE-CHARACTER COMPILE-REPAIR META-LANGUAGE. IT DOES NOT CONTAIN THE BROKEN CONTROLLER PATCH, LINE NUMBER, OR EXPECTED REPAIRED SOURCE.'
        }
        x['component_digest']=_digest(x); return x

__all__=['GenericCompileRepairMetaLanguageV1']
