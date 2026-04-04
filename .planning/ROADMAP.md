# Roadmap: papyr.bck

## Overview

This is a brownfield audit-and-fix milestone. The app exists and is feature-complete but has never run in production. The goal is to surface every implementation bug, security problem, and documentation gap — as explicit lists, reviewed by the user — before a single fix is applied. Fixes come last, after full audit approval.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Code Audit** - Identify and document all bugs, security issues, and robustness gaps in app.py
- [ ] **Phase 2: Documentation Audit** - Audit README, code comments, and compose files for gaps and inaccuracies
- [ ] **Phase 3: Fix & Harden** - Apply approved fixes for all identified issues and verify the setup flow

## Phase Details

### Phase 1: Code Audit
**Goal**: Every implementation bug, security vulnerability, and robustness gap in the codebase is identified and documented as a reviewable list before any fix is applied
**Depends on**: Nothing (first phase)
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-05
**Success Criteria** (what must be TRUE):
  1. A written list of all implementation bugs in app.py exists, with file location and description for each
  2. A written list of all security issues (auth, Docker socket, input handling) exists, with severity and location for each
  3. A written list of all robustness gaps (error handling, edge cases, race conditions) exists, with reproduction trigger for each
  4. Container detection correctness and backup-lock race conditions are explicitly evaluated and documented
**Plans:** 1 plan
Plans:
- [ ] 01-01-PLAN.md — Comprehensive code audit of app.py (security, bugs, robustness, container detection, thread safety)

### Phase 2: Documentation Audit
**Goal**: Every gap, inaccuracy, or missing piece in the project's documentation is identified and documented as a reviewable list before any correction is applied
**Depends on**: Phase 1
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. A written list of all README gaps exists — missing setup steps, incorrect config options, or unstated limitations
  2. A written list of all stale or misleading code comments in app.py exists, with line references
  3. docker-compose.yml and docker-compose.secure.yml documentation gaps are identified and listed
  4. All environment variables are cross-checked against README; any missing or incorrect entries are listed
**Plans**: TBD

### Phase 3: Fix & Harden
**Goal**: All issues identified in Phases 1 and 2 are resolved; the app is safe to run in production for the first time
**Depends on**: Phase 2
**Requirements**: AUDIT-04, SETUP-01, SETUP-02
**Success Criteria** (what must be TRUE):
  1. Every bug and security issue approved for fixing in Phase 1 is resolved in app.py
  2. README and code comments accurately reflect the current codebase with no missing env vars or misleading steps
  3. setup.sh and setup_web.py complete without error on a clean system and produce a working Docker deployment
  4. The web UI surfaces a clear, actionable error message for each known failure mode (no Docker, wrong container, bad auth)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Code Audit | 0/1 | Planning complete | - |
| 2. Documentation Audit | 0/? | Not started | - |
| 3. Fix & Harden | 0/? | Not started | - |
