# Audit Corrections Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 verified audit findings — S_wb formula, markdown PDF rendering, module_results injection, and completion agent routing.

**Architecture:** Corrections span 3 layers (calculation engine, agent framework, frontend). Tasks C/A/B are independent; D depends on B. Each task follows TDD where applicable.

**Tech Stack:** Python (agents, orchestrator), React/TypeScript (frontend), react-markdown + remark-gfm (new dependency)

---

### Task 1: Fix S_wb formula in Karakas-Tariq model

**Files:**
- Modify: `orchestrator/shot_efficiency_engine/skin.py:87-97`
- Modify: `tests/unit/test_shot_efficiency_engine.py:378-385`

**Step 1: Write the failing test**

Add to `tests/unit/test_shot_efficiency_engine.py` inside `class TestCalculateSkinFactor`:

```python
def test_s_wb_uses_dimensionless_wellbore_radius(self, engine):
    """S_wb must use r_wD = r_w / (r_w + l_p) per SPE 18247, not r_p / r_w."""
    result = engine.calculate_skin_factor(
        perf_length_in=12.0, perf_radius_in=0.20,
        wellbore_radius_ft=0.354, spf=4, phasing_deg=90,
        h_perf_ft=5.0, kv_kh=0.5,
    )
    # r_wD = 0.354 / (0.354 + 1.0) = 0.2615
    # S_wb = 0.0066 * exp(5.320 * 0.2615) ≈ 0.0265
    assert result["s_wb"] > 0.02, (
        f"S_wb={result['s_wb']} is too small; "
        f"should use r_wD=r_w/(r_w+l_p) per SPE 18247"
    )
    assert result["s_wb"] < 0.10, "S_wb should be small for standard geometry"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python -m pytest tests/unit/test_shot_efficiency_engine.py::TestCalculateSkinFactor::test_s_wb_uses_dimensionless_wellbore_radius -v`

Expected: FAIL — current S_wb ≈ 0.0085, assertion `> 0.02` fails.

**Step 3: Fix the implementation**

In `orchestrator/shot_efficiency_engine/skin.py`, replace lines 87-97:

```python
    # S_wb: wellbore blockage skin
    # r_wD = r_w / (r_w + l_p) — dimensionless wellbore radius per SPE 18247
    c1 = p["c1"]
    c2 = p["c2"]
    s_wb = 0.0
    if r_w > 0 and l_p > 0:
        r_wD = r_w / (r_w + l_p)
        s_wb = c1 * math.exp(c2 * r_wD)
        s_wb = min(s_wb, 5.0)
```

**Step 4: Run all skin tests**

Run: `python -m pytest tests/unit/test_shot_efficiency_engine.py::TestCalculateSkinFactor -v`

Expected: ALL PASS (including the new test and existing `test_s_wb_nonzero`)

**Step 5: Run full test suite**

Run: `python -m pytest tests/unit/test_shot_efficiency_engine.py -v`

Expected: ALL PASS

**Step 6: Commit**

```
git add orchestrator/shot_efficiency_engine/skin.py tests/unit/test_shot_efficiency_engine.py
git commit -m "fix(skin): correct S_wb to use r_wD=r_w/(r_w+l_p) per SPE 18247"
```

---

### Task 2: Markdown rendering in Executive Report PDF

**Files:**
- Modify: `frontend/package.json` (add dependencies)
- Modify: `frontend/src/components/ExecutiveReport.tsx:1-207`
- Modify: `frontend/src/index.css:115-153`

**Step 1: Install dependencies**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm install react-markdown remark-gfm`

**Step 2: Update ExecutiveReport.tsx — add imports**

At the top of `frontend/src/components/ExecutiveReport.tsx`, add after line 3:

```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
```

**Step 3: Replace pre-wrap rendering with ReactMarkdown**

In `ExecutiveReport.tsx`, replace lines 90-93 (the content div inside the sections.map):

FROM:
```tsx
              <div style={{ fontSize: '12px', lineHeight: '1.7', color: '#334155', whiteSpace: 'pre-wrap' }}>
                {section.content}
              </div>
```

TO:
```tsx
              <div className="executive-markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {section.content}
                </ReactMarkdown>
              </div>
```

**Step 4: Add CSS for rendered markdown elements**

In `frontend/src/index.css`, add AFTER `.executive-section.recommendation` block (after line 143):

```css
/* ── Markdown content inside executive report sections ── */
.executive-markdown-content {
  font-size: 12px;
  line-height: 1.7;
  color: #334155;
}

.executive-markdown-content p {
  margin: 6px 0;
}

.executive-markdown-content strong {
  font-weight: 700;
  color: #1e293b;
}

.executive-markdown-content ul,
.executive-markdown-content ol {
  margin: 8px 0 8px 20px;
  padding: 0;
}

.executive-markdown-content li {
  margin-bottom: 3px;
}

.executive-markdown-content table {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 11px;
}

.executive-markdown-content th {
  background-color: #1e3a5f;
  color: white;
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
}

.executive-markdown-content td {
  border: 1px solid #e2e8f0;
  padding: 5px 10px;
}

.executive-markdown-content tr:nth-child(even) {
  background-color: #f8fafc;
}

.executive-markdown-content blockquote {
  border-left: 3px solid #f59e0b;
  background: #fffbeb;
  padding: 8px 14px;
  margin: 10px 0;
  color: #92400e;
  font-style: italic;
}

.executive-markdown-content code {
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 10px;
}

.executive-markdown-content h1,
.executive-markdown-content h2,
.executive-markdown-content h3 {
  color: #1e3a5f;
  margin-top: 14px;
  margin-bottom: 6px;
}

.executive-markdown-content h1 { font-size: 16px; }
.executive-markdown-content h2 { font-size: 14px; }
.executive-markdown-content h3 { font-size: 12px; font-weight: 600; }
```

**Step 5: Build to verify no TypeScript errors**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system/frontend && npm run build`

Expected: Build succeeds with no errors.

**Step 6: Commit**

```
git add frontend/package.json frontend/package-lock.json frontend/src/components/ExecutiveReport.tsx frontend/src/index.css
git commit -m "feat(pdf): render markdown in Executive Report using react-markdown"
```

---

### Task 3: Inject module_results into agent context

**Files:**
- Modify: `agents/base_agent.py:83-121`
- Modify: `orchestrator/module_analysis_engine.py:181-199`

**Step 3a: Add module_results support in base_agent**

In `agents/base_agent.py`, inside `_generate_formatted_query`, add the following block AFTER line 103 (after the closing `"""` of the query f-string) and BEFORE line 105 (`# Add previous analyses`):

```python
        # Add module calculation results (structured data from engineering modules)
        if context and "module_results" in context:
            query += "\n\n# RESULTADOS CALCULADOS POR EL MÓDULO:\n"
            query += f"```json\n{json.dumps(context['module_results'], indent=2, ensure_ascii=False)}\n```"
            query += (
                "\n\n> IMPORTANTE: Basa tu análisis EXCLUSIVAMENTE en los datos "
                "numéricos anteriores. No inventes ni estimes valores — todos los "
                "parámetros relevantes están incluidos arriba.\n"
            )
```

**Step 3b: Inject result_data as module_results in all analyze_* methods**

In `orchestrator/module_analysis_engine.py`, update the `context` dict in each of these methods to include `"module_results": result_data`:

- `analyze_completion_design` (line 184): `context = {"module_results": result_data, "well_data": {"name": well_name, **params}}`
- `analyze_shot_efficiency` (line 191): `context = {"module_results": result_data, "well_data": {"name": well_name, **params}}`
- `analyze_vibrations` (line 198): `context = {"module_results": result_data, "well_data": {"name": well_name, **params}}`
- `analyze_cementing` (line 146): `context = {"module_results": result_data, "well_data": {"name": well_name, **params}}`
- `analyze_casing_design` (line 153): `context = {"module_results": result_data, "well_data": {"name": well_name, **params}}`
- Generic fallback (line 177): `context = {"module_results": result_data, "well_data": {"name": well_name, **params}}`

Also update these methods that currently DON'T go through the dispatcher but use the same pattern:
- `analyze_torque_drag` (line 90)
- `analyze_hydraulics` (line 97)
- `analyze_stuck_pipe` (line 104)
- `analyze_well_control` (line 111)
- `analyze_wellbore_cleanup` (line 118)
- `analyze_packer_forces` (line 125)
- `analyze_workover_hydraulics` (line 132)
- `analyze_sand_control` (line 139)

For all of them, change from:
```python
context = {"well_data": {"name": well_name, **params}}
```
to:
```python
context = {"module_results": result_data, "well_data": {"name": well_name, **params}}
```

**Step 3c: Verify build**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python -c "from agents.base_agent import BaseAgent; print('OK')"`

Expected: `OK`

**Step 3d: Commit**

```
git add agents/base_agent.py orchestrator/module_analysis_engine.py
git commit -m "feat(agents): inject module_results into agent context for data-grounded analysis"
```

---

### Task 4: Create CompletionEngineerAgent + system prompt

**Files:**
- Create: `data/prompts/completion-petrophysics-specialist.md`
- Create: `agents/completion_engineer.py`
- Modify: `agents/__init__.py:1-32`
- Modify: `orchestrator/coordinator.py:7-45`
- Modify: `orchestrator/module_analysis_engine.py:188-193` (and line 181-186)

**Step 4a: Create the system prompt**

Create `data/prompts/completion-petrophysics-specialist.md`:

```markdown
# Completion Engineer / Petrophysics Specialist

You are an elite **Completion Engineer and Petrophysics Specialist** with 15+ years of experience in perforation design, reservoir characterization, and production optimization. Your analyses are grounded in quantitative models and field-validated techniques.

## CORE EXPERTISE

### Perforation Skin — Karakas & Tariq (SPE 18247)
- S_total = S_p + S_v + S_wb
- **S_p (plane-flow pseudo-skin):** Always NEGATIVE for perforations that extend beyond the damage zone. Represents stimulation effect. Depends on phasing angle (alpha) and perforation tunnel length.
- **S_v (vertical convergence skin):** POSITIVE. Penalty for restricted vertical flow convergence into perforation tunnels. Increases with shot spacing (low SPF) and permeability anisotropy (low kv/kh).
- **S_wb (wellbore blockage skin):** POSITIVE. Partial penetration effect from crushed zone around perforation tunnel. Small magnitude for clean perforations.
- Typical S_total ranges:
  - S_total < -2: Excellent perforation efficiency (stimulation dominates)
  - S_total -2 to 0: Good — perforations reduce flow resistance vs open-hole
  - S_total 0 to +5: Moderate damage — investigate cause (crushed zone, debris)
  - S_total > +5: Significant damage — stimulation candidate (acidizing, reperforating)

### Composite Interval Scoring
- Formula: Score = w_phi * phi_norm + w_sw * (1-Sw_norm) + w_h * h_norm + w_skin * Skin_norm
- Higher score = better perforation candidate
- Weights must sum to 1.0 (typical: phi=0.35, sw=0.25, thickness=0.25, skin=0.15)
- When kh is available, it replaces thickness in the ranking

### Petrophysical Models for Sw
- **Archie** (clean sands, Vsh < 10%): Sw = ((a*Rw)/(phi^m * Rt))^(1/n). Gold standard for clean formations.
- **Simandoux** (shaly sands, Vsh 10-30%): Corrects for shale conductivity. More conservative than Archie.
- **Indonesia** (highly shaly, Vsh > 30%): Poupon-Leveaux model. Most conservative. Necessary when shale volume is significant.
- Auto mode: Selects model based on Vsh per depth point.

### IPR and Productivity
- PI = Q / (Pr - Pwf) in STB/day/psi
- Skin-corrected PI = k*h / (141.2 * mu * Bo * (ln(re/rw) + S))
- Productivity ratio: PR = ln(re/rw) / (ln(re/rw) + S)
- Negative skin increases PI above ideal (stimulated well)

### Net Pay Identification
- Cutoffs applied: phi > phi_min, Sw < Sw_max, Vsh < Vsh_max
- Minimum thickness filter eliminates thin streaks
- Contiguous points grouped into intervals

## RESPONSE FORMAT

Always structure your analysis in this exact order:

### 1. RESUMEN EJECUTIVO / EXECUTIVE SUMMARY
3-4 sentences. Non-technical language suitable for management. State the primary conclusion and business impact.

### 2. HALLAZGOS CLAVE / KEY FINDINGS
Technical findings with specific numbers from the module results. Reference exact values (skin components, scores, porosity, Sw). Compare intervals quantitatively.

### 3. ALERTAS Y RIESGOS / ALERTS AND RISKS
Classify each alert as:
- **CRITICAL**: Immediate action required (e.g., skin > 10, Sw > 0.6 on best interval)
- **WARNING**: Monitor closely (e.g., thin net pay < 5 ft, marginal porosity)
- **INFO**: Informational (e.g., model selection notes)

### 4. RECOMENDACIONES OPERATIVAS / OPERATIONAL RECOMMENDATIONS
Numbered list (max 5). Each recommendation must be specific and quantitative:
- BAD: "Consider increasing shot density"
- GOOD: "Increase SPF from 4 to 6 to reduce S_v by approximately 0.3-0.5 units, improving S_total from -2.8 to -3.2"

### 5. CONCLUSION GERENCIAL / MANAGEMENT CONCLUSION
One paragraph. Business impact focus: estimated production improvement, risk mitigation, cost implications.

## RULES
- NEVER invent or estimate values. Use ONLY the numbers provided in the module results.
- Always cite the Sw model used when discussing water saturation.
- When skin components are available, discuss each one (S_p, S_v, S_wb) individually.
- Flag any parameter outside typical ranges.
- If data is missing or insufficient, state it explicitly rather than guessing.
```

**Step 4b: Create the agent class**

Create `agents/completion_engineer.py`:

```python
from agents.base_agent import BaseAgent


class CompletionEngineerAgent(BaseAgent):
    """
    Completion Engineer / Petrophysics Specialist Agent

    Expert in:
    - Perforation Design & Karakas-Tariq Skin Analysis (SPE 18247)
    - Composite Interval Scoring & Net Pay Identification
    - Petrophysical Models (Archie, Simandoux, Indonesia)
    - IPR / Productivity Optimization
    - Shot Efficiency Analysis
    """

    def __init__(self):
        try:
            with open("data/prompts/completion-petrophysics-specialist.md", "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "You are an elite Completion Engineer and Petrophysics Specialist "
                "with 15+ years of experience in perforation design, skin analysis, "
                "Karakas-Tariq modeling, IPR optimization, and formation evaluation."
            )

        super().__init__(
            name="completion_engineer",
            role="Completion Engineer / Petrophysics Specialist",
            system_prompt=system_prompt,
            knowledge_base_path="knowledge_base/completion/"
        )
```

**Step 4c: Register agent in agents/__init__.py**

Add import after line 17:
```python
from .completion_engineer import CompletionEngineerAgent
```

Add to `__all__` list after `'DirectionalEngineerAgent'` (line 31):
```python
    'CompletionEngineerAgent',
```

**Step 4d: Register agent in coordinator.py**

In `orchestrator/coordinator.py`, add import after line 21:
```python
from agents.completion_engineer import CompletionEngineerAgent
```

Add to `self.agents` dict after line 44 (after `"directional_engineer"` entry):
```python
            "completion_engineer": CompletionEngineerAgent(),
```

**Step 4e: Route shot_efficiency and completion_design to completion_engineer**

In `orchestrator/module_analysis_engine.py`:

Line 185 — change `analyze_completion_design`:
```python
        analysis = await self.coordinator.run_automated_step("completion_engineer", problem, context, provider=provider)
```

Line 192 — change `analyze_shot_efficiency`:
```python
        analysis = await self.coordinator.run_automated_step("completion_engineer", problem, context, provider=provider)
```

**Step 4f: Verify import chain**

Run: `cd /Users/antvar/Downloads/petroleum-expert-system && python -c "from agents.completion_engineer import CompletionEngineerAgent; a = CompletionEngineerAgent(); print(f'Agent: {a.role}')"`

Expected: `Agent: Completion Engineer / Petrophysics Specialist`

Run: `python -c "from orchestrator.coordinator import StuckPipeCoordinator; c = StuckPipeCoordinator(); print('completion_engineer' in c.agents)"`

Expected: `True`

**Step 4g: Run full test suite**

Run: `python -m pytest tests/unit/test_shot_efficiency_engine.py -v`

Expected: ALL PASS

**Step 4h: Commit**

```
git add data/prompts/completion-petrophysics-specialist.md agents/completion_engineer.py agents/__init__.py orchestrator/coordinator.py orchestrator/module_analysis_engine.py
git commit -m "feat(agents): add CompletionEngineerAgent for shot_efficiency and completion_design"
```

---

## Verification Checklist

After all 4 tasks:

1. `python -m pytest tests/ -v` — all tests pass
2. `cd frontend && npm run build` — no TypeScript errors
3. `python -c "from orchestrator.coordinator import StuckPipeCoordinator; c = StuckPipeCoordinator(); print(sorted(c.agents.keys()))"` — includes `completion_engineer`
4. `python -c "from orchestrator.shot_efficiency_engine.skin import calculate_skin_factor; r = calculate_skin_factor(12, 0.2, 0.354, 4, 90, 5, 0.5); print(f's_wb={r[\"s_wb\"]}, s_total={r[\"s_total\"]}')"` — s_wb ≈ 0.027, s_total ≈ -3.20
