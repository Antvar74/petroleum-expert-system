# PETROEXPERT Knowledge Base

## Structure

```
knowledge_base/
├── README_MASTER.md          ← This file
├── modules/                  ← AI Agent evaluation reference (14 modules + framework)
│   ├── README.md             ← Master index with standards quick reference
│   ├── _evaluation_framework.md  ← Universal DICA evaluation methodology
│   ├── torque_drag.md        ← Torque & Drag formulas, thresholds, checklist
│   ├── hydraulics.md         ← Hydraulics (API RP 13D, ECD, surge/swab)
│   ├── stuck_pipe.md         ← Stuck Pipe (IADC decision trees, 9 mechanisms)
│   ├── well_control.md       ← Well Control (IWCF, kill methods, Z-factor)
│   ├── casing_design.md      ← Casing Design (API 5CT, biaxial, NACE)
│   ├── cementing.md          ← Cementing (API 10A, displacement, U-tube)
│   ├── completion_design.md  ← Completion (IPR, VLP, nodal, perforation)
│   ├── sand_control.md       ← Sand Control (Saucier, gravel pack)
│   ├── packer_forces.md      ← Packer Forces (Lubinski, thermal, APB)
│   ├── wellbore_cleanup.md   ← Wellbore Cleanup (HCI, transport ratio)
│   ├── workover_hydraulics.md ← Workover/CT (ICoTA, reach analysis)
│   ├── vibrations.md         ← Vibrations (Paslay-Dawson, FEA, Campbell)
│   ├── shot_efficiency.md    ← Shot Efficiency (Archie, Simandoux, ranking)
│   └── petrophysics.md       ← Petrophysics (Waxman-Smits, dual-water)
├── drilling/                 ← Operational drilling knowledge (8 files)
├── fluids/                   ← Fluids knowledge (placeholder)
├── geology/                  ← Geology knowledge (placeholder)
├── pressure_analysis/        ← Pressure analysis knowledge (placeholder)
└── well_design/              ← Well design knowledge (placeholder)
```

## Purpose

The `modules/` directory contains technical reference documents for the AI evaluation agents.
Each file maps directly to a calculation engine in `orchestrator/` and provides:

1. **Exact formulas** matching the engine code
2. **Standards citations** (API, SPE, IADC, IWCF, NACE, NORSOK)
3. **Result interpretation thresholds** (Normal / Caution / Critical)
4. **Failure pattern recognition** guides
5. **Evaluation checklists** for systematic analysis
6. **Bilingual terminology** tables (EN/ES)

The `_evaluation_framework.md` defines the universal DICA methodology
(Dato → Interpretación → Consecuencia → Acción) that all agents must follow.
