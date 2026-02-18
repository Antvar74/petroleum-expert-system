# API RP 585 INCIDENT INVESTIGATION FORMAT (Level 2)

## INSTRUCTIONS
Output your Root Cause Analysis using this strict structure based on API Recommended Practice 585.

## REPORT STRUCTURE

### 1. EXECUTIVE SUMMARY
- **Incident Level**: Level 2 (Major) / Level 1 (Minor)
- **Brief Description**: [One sentence summary]
- **Actual Consequence**: [Cost/Time/Safety Impact]
- **Potential Consequence**: [Worst case scenario]

### 2. SEQUENCE OF EVENTS (Timeline)
*Reconstruct the timeline leading to the event*
- [Time/Date]: [Event 1]
- [Time/Date]: [Event 2]
- [Time/Date]: [Incident Occurs]
- [Time/Date]: [Immediate Response]

### 3. 5-WHYS ANALYSIS
*Drill down to the root cause*
1. **Why** [Event]? -> [Answer]
2. **Why** [Previous Answer]? -> [Answer]
3. **Why** [Previous Answer]? -> [Answer]
4. **Why** [Previous Answer]? -> [Answer]
5. **Why** [Previous Answer]? -> [ROOT CAUSE]

### 4. ISHIKAWA (FISHBONE) DIMENSIONS
*Categorize contributing factors*
- **Man**: [Human factors, communication, training]
- **Machine**: [Equipment failure, design, maintenance]
- **Method**: [Procedures, standards, planning]
- **Material**: [Fluids, chemicals, raw materials]
- **Measurement**: [Sensors, data quality, alarms]
- **Environment**: [Weather, sea state, formation]

### 5. BARRIER ANALYSIS
| Barrier Type | Description | Status | Why it failed/succeeded |
|--------------|-------------|--------|-------------------------|
| Prevention | [Description] | FAILED | [Reason] |
| Detection | [Description] | FAILED | [Reason] |
| Mitigation | [Description] | EFFECTIVE | [Reason] |

### 6. CORRECTIVE ACTIONS MATRIX (Recommendations)
| ID | Recommendation | Responsibility | Priority |
|----|----------------|----------------|----------|
| RC-01 | [Action] | [Role] | High |
| RC-02 | [Action] | [Role] | Medium |
