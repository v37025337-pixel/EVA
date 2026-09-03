from __future__ import annotations
import hashlib, json

def _digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def predict(tree,row):
    cur=tree
    while 'label' not in cur:
        cur=cur['true'] if bool(row.get(cur['feature'])) else cur['false']
    return cur['label']

class OpenAPIContractRuntime:
    def __init__(self, state_section:dict):
        self.state=state_section or {}
        self.tree=self.state.get('policy_tree') or {'label':'SEEK_MORE_EVIDENCE'}
        self.contracts=self.state.get('contract_registry') or {}
    def classify(self,contract_id:str):
        c=self.contracts.get(contract_id)
        if not c:return {'action':'SEEK_MORE_EVIDENCE','reason':'UNKNOWN_CONTRACT'}
        return {'action':predict(self.tree,c),'contract_id':contract_id,'source_id':c.get('source_id')}
    def compile_plan(self,contract_id:str):
        c=self.contracts.get(contract_id)
        if not c:return {'action':'SEEK_MORE_EVIDENCE','reason':'UNKNOWN_CONTRACT','network_execute':False}
        action=predict(self.tree,c)
        slots={'path':[],'query':[],'header':[],'body':[]}
        for p in c.get('required',[]):
            slots.setdefault(p['in'],[]).append({'name':p['name'],'type':p.get('type','unknown'),'required':True})
        plan={'contract_id':contract_id,'source_id':c['source_id'],'source_sha':c['source_sha'],'method':c['method'],'path':c['path'],
              'required_slots':slots,'action':action,'network_execute':False,
              'credential_gate':action=='SEEK_CREDENTIAL','evidence_gate':action=='SEEK_MORE_EVIDENCE',
              'primary_verification_required':action=='SEEK_PRIMARY_VERIFY',
              'read_only_candidate':c['method']=='GET' and not c.get('redirect_semantic',False)}
        plan['contract_digest']=_digest(plan)
        return plan
