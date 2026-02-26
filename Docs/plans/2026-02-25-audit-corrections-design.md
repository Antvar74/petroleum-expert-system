# PetroExpert — Audit Corrections Design

**Date:** 2026-02-25
**Scope:** 4 verified corrections from post-improvement audit
**Status:** Approved

---

## Context

A technical audit identified 5 issues. Critical evaluation against the actual codebase confirmed 4 are real and 1 was misdiagnosed (K-T S_p bug — the guard clause is dead code that never triggers; S_p correctly computes -3.25). The audit's proposed S_wb fix (using r_wb in inches) was also rejected as it would produce S_wb=5.0 (capped), which is physically incorrect.

## Corrections

### A — Markdown Rendering in PDF (Frontend)

**Problem:** `ExecutiveReport.tsx:90` renders with `whiteSpace: pre-wrap`. Inline markdown (`**bold**`, `- lists`, `| tables |`) appears as raw text in PDFs.

**Solution:** Install `react-markdown` + `remark-gfm`. Replace pre-wrap div with `<ReactMarkdown>` component. Add print-friendly CSS for rendered HTML elements under `.executive-report`.

**Files:** `frontend/package.json`, `frontend/src/components/ExecutiveReport.tsx`, `frontend/src/index.css`

### B — Module Results in Agent Context

**Problem:** `_build_se_problem()` passes only 4 summary metrics as text. Complete calculation results (intervals, skin components, rankings, parameters) never reach the LLM.

**Solution:**
- B1: Add `module_results` support in `base_agent._generate_formatted_query()` — inject full JSON before other context blocks
- B2: Pass `result_data` as `context["module_results"]` in all `analyze_*` methods in `module_analysis_engine.py`

**Files:** `agents/base_agent.py`, `orchestrator/module_analysis_engine.py`

### C — S_wb Karakas-Tariq (SPE 18247)

**Problem:** `skin.py:92` uses `r_p / r_w` (~0.047). SPE 18247 defines `r_wD = r_w / (r_w + l_p)` (~0.261). Difference is small (~0.02 skin units) but technically incorrect.

**Solution:** Replace `ratio = r_p / r_w` with `r_wD = r_w / (r_w + l_p)`. Keep cap at 5.0.

**Files:** `orchestrator/shot_efficiency_engine/skin.py`, `tests/unit/test_shot_efficiency_engine.py`

### D — CompletionAgent + Routing for Shot Efficiency

**Problem:** `analyze_shot_efficiency` uses `well_engineer` agent whose system prompt covers trajectory/T&D. Analysis uses wrong domain terminology.

**Solution:**
- D1: Create `data/prompts/completion-petrophysics-specialist.md` with K-T, IPR, score composite expertise
- D2: Create `agents/completion_engineer.py` extending BaseAgent
- D3: Route `shot_efficiency` and `completion_design` to `completion_engineer` in module_analysis_engine and api_coordinator

**Files:** `data/prompts/completion-petrophysics-specialist.md` (new), `agents/completion_engineer.py` (new), `agents/__init__.py`, `orchestrator/module_analysis_engine.py`, `orchestrator/api_coordinator.py`

## Execution Order

```
C (S_wb) → independent, smallest change
A (Markdown) → independent, frontend only
B (module_results) → independent, backend
D (CompletionAgent) → depends on B
```

C, A, B are parallelizable. D requires B to be complete.
