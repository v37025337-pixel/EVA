from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import copy,hashlib,json,math,os,tempfile

from yado_g2_cognitive_clock_v1 import G2CognitiveClockV1
from yado_g2_unified_execution_fabric_v4 import G2UnifiedExecutionFabricV4,_digest_v4

def _json_bytes_v5(o):
    return json.dumps(
        o,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False
    ).encode('utf-8')

def _sha256_bytes_v5(b):
    return hashlib.sha256(b).hexdigest()

class _TypedJSONV2:
    ENCODING='YADO_TYPED_JSON_V1'
    MAX_DEPTH=128
    MAX_NODES=250000

    @classmethod
    def encode(cls,obj):
        counter=[0]
        def enc(x,depth):
            counter[0]+=1
            if counter[0]>cls.MAX_NODES:raise ValueError('TYPED_JSON_NODE_LIMIT')
            if depth>cls.MAX_DEPTH:raise ValueError('TYPED_JSON_DEPTH_LIMIT')
            if x is None:return {'t':'none'}
            if isinstance(x,bool):return {'t':'bool','v':x}
            if isinstance(x,int):return {'t':'int','v':str(x)}
            if isinstance(x,Fraction):
                return {'t':'fraction','n':str(x.numerator),'d':str(x.denominator)}
            if isinstance(x,float):
                if not math.isfinite(x):raise ValueError('NON_FINITE_FLOAT_NOT_ALLOWED')
                return {'t':'float','v':repr(x)}
            if isinstance(x,str):return {'t':'str','v':x}
            if isinstance(x,tuple):
                return {'t':'tuple','v':[enc(v,depth+1) for v in x]}
            if isinstance(x,list):
                return {'t':'list','v':[enc(v,depth+1) for v in x]}
            if isinstance(x,dict):
                return {'t':'dict','v':[[enc(k,depth+1),enc(v,depth+1)] for k,v in x.items()]}
            raise TypeError('UNSUPPORTED_CHECKPOINT_OBJECT:'+type(x).__name__)
        return enc(obj,0)

    @classmethod
    def decode(cls,node):
        counter=[0]
        def dec(n,depth):
            counter[0]+=1
            if counter[0]>cls.MAX_NODES:raise ValueError('TYPED_JSON_NODE_LIMIT')
            if depth>cls.MAX_DEPTH:raise ValueError('TYPED_JSON_DEPTH_LIMIT')
            if not isinstance(n,dict):raise ValueError('TYPED_JSON_NODE_NOT_OBJECT')
            t=n.get('t')
            if t=='none':
                if set(n)!={'t'}:raise ValueError('TYPED_JSON_NONE_FIELDS')
                return None
            if t=='bool':
                if set(n)!={'t','v'} or not isinstance(n.get('v'),bool):raise ValueError('TYPED_JSON_BOOL')
                return n['v']
            if t=='int':
                if set(n)!={'t','v'} or not isinstance(n.get('v'),str):raise ValueError('TYPED_JSON_INT')
                try:return int(n['v'])
                except Exception as e:raise ValueError('TYPED_JSON_INT') from e
            if t=='fraction':
                if set(n)!={'t','n','d'} or not isinstance(n.get('n'),str) or not isinstance(n.get('d'),str):
                    raise ValueError('TYPED_JSON_FRACTION')
                try:return Fraction(int(n['n']),int(n['d']))
                except Exception as e:raise ValueError('TYPED_JSON_FRACTION') from e
            if t=='float':
                if set(n)!={'t','v'} or not isinstance(n.get('v'),str):raise ValueError('TYPED_JSON_FLOAT')
                try:x=float(n['v'])
                except Exception as e:raise ValueError('TYPED_JSON_FLOAT') from e
                if not math.isfinite(x):raise ValueError('NON_FINITE_FLOAT_NOT_ALLOWED')
                return x
            if t=='str':
                if set(n)!={'t','v'} or not isinstance(n.get('v'),str):raise ValueError('TYPED_JSON_STR')
                return n['v']
            if t in ('tuple','list'):
                if set(n)!={'t','v'} or not isinstance(n.get('v'),list):raise ValueError('TYPED_JSON_SEQUENCE')
                xs=[dec(v,depth+1) for v in n['v']]
                return tuple(xs) if t=='tuple' else xs
            if t=='dict':
                if set(n)!={'t','v'} or not isinstance(n.get('v'),list):raise ValueError('TYPED_JSON_DICT')
                out={}
                for pair in n['v']:
                    if not isinstance(pair,list) or len(pair)!=2:raise ValueError('TYPED_JSON_DICT_PAIR')
                    k=dec(pair[0],depth+1);v=dec(pair[1],depth+1)
                    try:
                        if k in out:raise ValueError('TYPED_JSON_DUPLICATE_KEY')
                        out[k]=v
                    except TypeError as e:
                        raise ValueError('TYPED_JSON_UNHASHABLE_KEY') from e
                return out
            raise ValueError('TYPED_JSON_UNKNOWN_TAG:'+str(t))
        return dec(node,0)

class G2UnifiedExecutionFabricV5(G2UnifiedExecutionFabricV4):
    COMPONENT_ID='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5'
    FILE_SCHEMA='yado.g2.cognitive_continuity_file.v2'
    FILE_ENCODING=_TypedJSONV2.ENCODING
    MAX_CHECKPOINT_FILE_BYTES=16*1024*1024

    def __init__(self,base_runtime,api_state=None,temporal_state=None,continuity_state=None,checkpoint_path=None):
        if isinstance(continuity_state,dict) and continuity_state.get('schema')==self.FILE_SCHEMA:
            raise ValueError('FILE_ENVELOPE_MUST_BE_LOADED_VIA_CHECKPOINT_PATH_OR_LOAD_METHOD')
        p=Path(checkpoint_path) if checkpoint_path else None
        loaded=None
        if continuity_state is not None:
            if temporal_state is not None:
                raise ValueError('CONTINUITY_AND_TEMPORAL_STATE_ARE_MUTUALLY_EXCLUSIVE')
            loaded=copy.deepcopy(continuity_state)
            self._prevalidate_state(loaded)
        elif p is not None and p.exists():
            if temporal_state is not None:
                raise ValueError('CHECKPOINT_PATH_AND_TEMPORAL_STATE_ARE_MUTUALLY_EXCLUSIVE')
            loaded=self.load_continuity_checkpoint(p)
        # Feed an already fully validated in-memory v1 checkpoint to V4 so no
        # caller-supplied base runtime is mutated before all file/cross-layer checks pass.
        super().__init__(
            base_runtime,api_state=api_state,
            temporal_state=temporal_state if loaded is None else None,
            continuity_state=loaded,
            checkpoint_path=None,
        )
        self._checkpoint_path=p

    @classmethod
    def _cross_layer_validate_without_runtime(cls,state):
        temporal=state['temporal_state']
        recurrent=state['recurrent_memory_state']
        records={int(r.get('tick_id',0)):r for r in temporal.get('records',[]) if isinstance(r,dict)}
        for e in recurrent.get('episodes',[]):
            if e.get('kind')!='TEMPORAL_TRANSITION':continue
            tid=int(e.get('tick_id',0))
            r=records.get(tid)
            if r is None:raise ValueError('CONTINUITY_TEMPORAL_TRANSITION_TICK_MISSING:'+str(tid))
            if e.get('tick_digest')!=r.get('tick_digest'):
                raise ValueError('CONTINUITY_TEMPORAL_TRANSITION_DIGEST_MISMATCH:'+str(tid))
        cross=state.get('cross_layer') or {}
        if int(cross.get('temporal_tick_id',-1))!=int(temporal.get('tick_id',-2)):
            raise ValueError('CONTINUITY_CROSS_LAYER_TICK_MISMATCH')
        if int(cross.get('recurrent_sequence',-1))!=int(recurrent.get('sequence',-2)):
            raise ValueError('CONTINUITY_CROSS_LAYER_SEQUENCE_MISMATCH')

    @classmethod
    def _prevalidate_state(cls,state):
        cls._validate_continuity_state(state)
        # G2CognitiveClockV1 validates the temporal state digest/shape without
        # touching the supplied recurrent base runtime.
        G2CognitiveClockV1(copy.deepcopy(state['temporal_state']))
        cls._cross_layer_validate_without_runtime(state)
        return state

    @classmethod
    def _file_envelope(cls,state):
        typed=_TypedJSONV2.encode(state)
        body={
          'schema':cls.FILE_SCHEMA,
          'encoding':cls.FILE_ENCODING,
          'checkpoint_schema':cls.CHECKPOINT_SCHEMA,
          'checkpoint_digest':state.get('checkpoint_digest'),
          'typed_checkpoint':typed,
          'executable_objects':False,
        }
        body['file_digest']=_sha256_bytes_v5(_json_bytes_v5(body))
        return body

    @classmethod
    def _validate_file_envelope(cls,envelope):
        if not isinstance(envelope,dict):raise ValueError('CONTINUITY_FILE_NOT_OBJECT')
        expected=envelope.get('file_digest')
        if not isinstance(expected,str) or len(expected)!=64:raise ValueError('CONTINUITY_FILE_DIGEST_MISSING')
        body=copy.deepcopy(envelope);body.pop('file_digest',None)
        if _sha256_bytes_v5(_json_bytes_v5(body))!=expected:
            raise ValueError('CONTINUITY_FILE_DIGEST_MISMATCH')
        if body.get('schema')!=cls.FILE_SCHEMA:raise ValueError('CONTINUITY_FILE_SCHEMA')
        if body.get('encoding')!=cls.FILE_ENCODING:raise ValueError('CONTINUITY_FILE_ENCODING')
        if body.get('checkpoint_schema')!=cls.CHECKPOINT_SCHEMA:raise ValueError('CONTINUITY_FILE_CHECKPOINT_SCHEMA')
        if body.get('executable_objects') is not False:raise ValueError('CONTINUITY_FILE_EXECUTABLE_OBJECT_FLAG')
        state=_TypedJSONV2.decode(body.get('typed_checkpoint'))
        if not isinstance(state,dict):raise ValueError('CONTINUITY_FILE_CHECKPOINT_NOT_OBJECT')
        if state.get('checkpoint_digest')!=body.get('checkpoint_digest'):
            raise ValueError('CONTINUITY_FILE_BOUND_CHECKPOINT_DIGEST_MISMATCH')
        cls._prevalidate_state(state)
        return state

    @classmethod
    def load_continuity_checkpoint(cls,path):
        p=Path(path)
        try:
            size=p.stat().st_size
        except OSError as e:
            raise ValueError('CONTINUITY_FILE_STAT_FAILED') from e
        if size<2 or size>cls.MAX_CHECKPOINT_FILE_BYTES:
            raise ValueError('CONTINUITY_FILE_SIZE_LIMIT')
        raw=p.read_bytes()
        if len(raw)>cls.MAX_CHECKPOINT_FILE_BYTES:raise ValueError('CONTINUITY_FILE_SIZE_LIMIT')
        try:
            text=raw.decode('utf-8')
        except UnicodeDecodeError as e:
            raise ValueError('CONTINUITY_FILE_UTF8') from e
        def bad_constant(x):
            raise ValueError('NON_FINITE_JSON_CONSTANT:'+str(x))
        try:
            doc=json.loads(text,parse_constant=bad_constant)
        except Exception as e:
            if isinstance(e,ValueError) and str(e).startswith('NON_FINITE_JSON_CONSTANT:'):raise
            raise ValueError('CONTINUITY_FILE_JSON_PARSE') from e
        if isinstance(doc,dict) and doc.get('schema')==cls.FILE_SCHEMA:
            return cls._validate_file_envelope(doc)
        # Backward-compatible valid plain JSON v1 checkpoint. Types already lost
        # by that old file format cannot be reconstructed heuristically.
        if isinstance(doc,dict) and doc.get('schema')==cls.CHECKPOINT_SCHEMA:
            cls._prevalidate_state(doc)
            return doc
        raise ValueError('CONTINUITY_FILE_UNSUPPORTED_SCHEMA')

    def save_continuity_checkpoint(self,path=None):
        p=Path(path) if path is not None else self._checkpoint_path
        if p is None:raise ValueError('CHECKPOINT_PATH_REQUIRED')
        state=self.export_continuity_state()
        envelope=self._file_envelope(state)
        raw=json.dumps(
            envelope,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False
        ).encode('utf-8')+b'\n'
        if len(raw)>self.MAX_CHECKPOINT_FILE_BYTES:
            raise ValueError('CONTINUITY_FILE_SIZE_LIMIT')
        p.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp_name=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=str(p.parent))
        tmp=Path(tmp_name)
        try:
            with os.fdopen(fd,'wb',closefd=True) as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
            os.replace(tmp,p)
            try:
                dfd=os.open(str(p.parent),os.O_RDONLY)
                try:os.fsync(dfd)
                finally:os.close(dfd)
            except Exception:
                pass
        except Exception:
            try:
                if tmp.exists():tmp.unlink()
            except Exception:
                pass
            raise
        return copy.deepcopy(state)

    @classmethod
    def component(cls):
        parent=G2UnifiedExecutionFabricV4.component()
        x={
          'schema':'yado.g2.unified_execution_fabric.v5',
          'component_id':cls.COMPONENT_ID,
          'parent_component':G2UnifiedExecutionFabricV4.COMPONENT_ID,
          'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH',
          'dispatches':parent.get('dispatches',[]),
          'continuity':copy.deepcopy(parent.get('continuity',{}))|{
            'file_schema':cls.FILE_SCHEMA,
            'typed_json_encoding':cls.FILE_ENCODING,
            'preserves_integer_dict_keys':True,
            'preserves_tuples':True,
            'preserves_fraction_exactness':True,
            'file_digest_validation_before_restore':True,
            'temporal_digest_validation_before_restore':True,
            'recurrent_digest_validation_before_restore':True,
            'cross_layer_validation_before_restore':True,
            'unique_temp_file':True,
            'failed_replace_preserves_previous_checkpoint':True,
            'max_checkpoint_file_bytes':cls.MAX_CHECKPOINT_FILE_BYTES,
            'unsupported_objects_fail_closed':True,
            'non_finite_numbers_fail_closed':True,
            'executable_object_deserialization':False,
            'legacy_plain_json_v1_accepted_if_valid':True,
          },
          'network_execution':parent.get('network_execution'),
          'canonical_active':False,
          'architecture_mutation':False,
          'automatic_canonical_promotion':False,
          'semantic_boundary':'SHADOW SUCCESSOR OF CANONICAL V4 REPAIRING FILE-SERIALIZATION INTEGRITY. IN-MEMORY CHECKPOINT CONTRACT REMAINS V1; NEW FILES USE A TYPED V2 ENVELOPE. THIS IS INFRASTRUCTURE REPAIR AUTHORED BY THE ASSISTANT, NOT KERNEL-GENERATED SOURCE OR EVIDENCE OF GENERAL-INTELLIGENCE GAIN.'
        }
        x['component_digest']=_digest_v4(x)
        return x

__all__=['G2UnifiedExecutionFabricV5']
