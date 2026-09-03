# YADO RC7 — GitHub runtime deployment

This repository contains the verified YADO 3.0-rc7 runtime snapshot and a GitHub Actions launcher.

The workflow restores the current live SQLite state from `state/yado_rc7_live_state.sql`, verifies the frozen RC7 manifest, instantiates `UnifiedYADOKernelV30RC7DeepIntegrity`, writes a runtime receipt, and runs the strict RC7 test suite.

The GitHub Actions run is finite. It is a real boot/verification execution, not a permanent daemon. Canonical RC7 state is not rewritten by the launcher.
