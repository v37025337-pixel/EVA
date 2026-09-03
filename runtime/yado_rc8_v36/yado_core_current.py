from yado_bootstrap import load_active_kernel_class, active_contract

_contract=active_contract()
UnifiedYADOKernelCurrent=load_active_kernel_class()
ACTIVE_PROFILE=_contract['profile']
ACTIVE_STATE=_contract['state']
ACTIVE_STATE_SHA256=_contract['state_sha256']

__all__=['UnifiedYADOKernelCurrent','ACTIVE_PROFILE','ACTIVE_STATE','ACTIVE_STATE_SHA256']
