"""Run the existing genetic controller inside the main kernel's causal journal.

Selection, admission and gene implementations come from ``generation``. This
adapter changes their storage and public execution seam, not their fitness rules.
No second SQLite state or separately running kernel is needed.
"""
from __future__ import annotations

import copy

from .generation import GenerationKernel, execute_component, inventory, parent_profile, sources
from .kernel import decode, fingerprint

EVENT = 'COMPONENT_GENERATION'
STORAGE = 'SUCCESSOR_CAUSAL_JOURNAL_V1'


class ComponentJournal(GenerationKernel):
    def __init__(self, kernel):
        # Deliberately borrow both handles; ownership stays with SuccessorKernel.
        self.kernel = kernel
        self.db = kernel.db
        self.archive = kernel.archive
        self.birth = None
        self.pinned_sources = sources()
        if not hasattr(kernel, '_component_verified_replays'):
            kernel._component_verified_replays = set()
        self._verified_replays = kernel._component_verified_replays

    def close(self):
        """Borrowed handles are closed by SuccessorKernel, never by this adapter."""

    def records(self):
        records = []
        for row in self.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick'):
            body = decode(row['body'])
            if body.get('kind') == EVENT:
                if set(body) != {'kind', 'event'} or not isinstance(body['event'], dict):
                    raise ValueError('COMPONENT_JOURNAL_EVENT_CONTRACT')
                if {'tick', 'event_hash'} & body['event'].keys():
                    raise ValueError('COMPONENT_JOURNAL_RESERVED_FIELDS')
                records.append({**body['event'], 'tick': row['tick'], 'event_hash': row['event_hash']})
        return records

    def _append(self, body):
        row = self.kernel._append({'kind': EVENT, 'event': copy.deepcopy(body)})
        return {**row['event'], 'tick': row['tick'], 'event_hash': row['event_hash']}

    def _ensure_birth(self):
        if self.records():
            return
        parent = self.kernel.verify_state()
        self._append({'kind': 'BIRTH', 'sources': sources(),
                      'parent_identity': self.kernel.identity, 'parent_state': parent,
                      'archive_sha256': self.kernel.manifest['archive_sha256'],
                      'branches': inventory(self.archive), 'storage': STORAGE,
                      'scope': 'EXECUTABLE_COMPONENT_GENERATIONS',
                      'canonical_generation': self.kernel.parent_audit['generation']})

    def snapshot(self):
        records = self.records()
        if not records:
            profile = parent_profile()
            return {'component_generation': 0, 'profile': profile,
                    'profile_digest': fingerprint(profile), 'execution_admitted': True,
                    'events': 0, 'storage': STORAGE}
        self.birth = records[0]
        if (self.birth.get('kind') != 'BIRTH' or self.birth.get('storage') != STORAGE
                or self.birth.get('parent_identity') != self.kernel.identity
                or self.birth.get('sources') != sources()
                or self.birth.get('archive_sha256') != self.kernel.manifest['archive_sha256']
                or self.birth.get('branches') != inventory(self.archive)
                or self.birth['parent_state']['tick'] != self.birth['tick'] - 1):
            raise ValueError('COMPONENT_JOURNAL_BIRTH_PROVENANCE')
        self._check_parent_state(self.birth['parent_state'])
        # Source migrations belong to the existing continuity procedure. A
        # separate GenerationKernel journal cannot be pasted into this stream.
        if any(r['kind'] in {'SOURCE_UPGRADE', 'READMISSION', 'BIRTH'} for r in records[1:]):
            raise ValueError('COMPONENT_JOURNAL_UNSUPPORTED_TRANSITION')
        self.pinned_sources = self.birth['sources']
        state = super().snapshot()
        profile, proposal = parent_profile(), None
        executions = {}
        for row in records[1:]:
            if row['kind'] == 'PROPOSE':
                proposal = row
            elif row['kind'] == 'ACTIVATE':
                profile = proposal['profile']
            elif row['kind'] == 'ROLLBACK':
                profile = parent_profile()
            elif row['kind'] == 'EXECUTE':
                if row['event_hash'] not in self._verified_replays:
                    actual = execute_component(profile[row['task']['organ']], row['task'])
                    if (fingerprint(actual) != fingerprint(row['result'])
                            or row['status'] != 'EXECUTED_REQUIRES_INDEPENDENT_CHECK'):
                        raise ValueError('COMPONENT_EXECUTION_NOT_REPRODUCIBLE')
                    self._verified_replays.add(row['event_hash'])
                executions[row['tick']] = row
        # A main task must point to its actual execution, not just any admitted
        # profile or a result claimed by the caller.
        for row in self.db.execute('SELECT tick,body FROM events ORDER BY tick'):
            body = decode(row['body'])
            if body.get('task', {}).get('kind') != 'component' or 'result' not in body:
                continue
            result = body['result']
            execution = executions.get(result.get('component_execution_tick'))
            if (execution is None or execution['tick'] >= row['tick']
                    or fingerprint(body['task'].get('payload', {})) != fingerprint(execution['task'])
                    or fingerprint(result) != fingerprint(self.public_result(execution))):
                raise ValueError('COMPONENT_MAIN_EXECUTION_LINK')
        return {**state, 'storage': STORAGE}

    @staticmethod
    def public_result(execution):
        return {**execution['result'], 'component_generation': execution['generation'],
                'profile_digest': execution['profile_digest'],
                'component_execution_tick': execution['tick']}

    def _transaction(self, operation):
        self.kernel._check_sources()
        owns_transaction = not self.db.in_transaction
        if owns_transaction:
            self.db.execute('BEGIN IMMEDIATE')
        try:
            self.kernel.verify_state()
            self._ensure_birth()
            self.snapshot()
            result = operation()
            if owns_transaction:
                self.db.execute('COMMIT')
            return result
        except BaseException:
            if owns_transaction and self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise
