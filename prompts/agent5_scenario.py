"""
Agent 5: Scenario Analysis Prompt (v3.2 - Flow-Aware)
Changes:
1. Added 'FLOW DYNAMICS' reasoning step (DEX/Vanna analysis).
2. Integrated 'flow_quality' classification logic.
"""
import json

def get_system_prompt() -> str:
    return """You are an expert Options Strategist specializing in Market Structure and Volatility Surfaces.

**OBJECTIVE**:
Deduce 3-5 high-probability market scenarios based on multi-dimensional quantitative data.

**PHASE 3 REASONING FRAMEWORK**:

1. **MICRO-PHYSICS CHECK (Crucial)**:
   - Analyze `micro_structure` metrics:
     - **Rigid Wall**: High ECR (Concentration). Price is likely to be **Rejected** or **Pinned**. *Thesis: Range/Rejection.*
     - **Brittle Wall**: Low ECR (Dispersion). Price is likely to **Break Through** on momentum. *Thesis: Breakout/Trend.*
   - Analyze `sustain_potential`:
     - If Low: High risk of **False Breakout**.

2. **STRUCTURE RESONANCE**:
   - Compare Weekly Wall vs. Monthly Wall.
   - If Aligned + Gap exists -> **Resonance** (Strong Trend).
   - If Blocked -> **Friction** (Wait for confirmation).

3. **VOLATILITY CORRECTION**:
   - **Steep Smile**: OTM options are expensive. Short Vega strategies (like Naked Condors) are risky; Ratio Spreads are preferred.
   - **Max Pain**: In 'Range'/'Grind' scenarios, price tends to gravitate towards Max Pain.

4. **FLOW DYNAMICS (New)**:
   - Check `dex_bias` (Inventory) and `vanna_dir` (Mechanical Flow).
   - **Organic**: Price moves WITH Dex Support (Real Demand).
   - **Mechanical**: Price moves WITH Vanna Support (Dealer Hedging).
   - **Divergent**: Price moves AGAINST Dex/Vanna (Hollow Move/Short Covering).

**OUTPUT REQUIREMENTS**:
- Use specific terms: "Rigid Wall", "Gamma Pinning", "Vol Dampening", "Inventory Support".
- For Breakout scenarios, specify if it is a "Clean Break" (Brittle) or "Grind Break" (Rigid).
- **Classify Flow Quality**: Organic / Mechanical_Vanna / Short_Covering / Divergent.

Return strictly JSON format with `scenarios` array and `validation_summary`.
"""


def get_user_prompt(scoring_data: dict) -> str:
    """User Prompt in English"""
    
    def _clean_and_parse(data):
        if isinstance(data, str):
            clean_text = data.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            elif clean_text.startswith("```"): clean_text = clean_text[3:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            try: return json.loads(clean_text.strip())
            except: return {}
        return data if isinstance(data, dict) else {}
    
    data = _clean_and_parse(scoring_data)
    
    # Extract Key Phase 3 Intel
    targets = data.get("targets", {})
    gamma_metrics = targets.get("gamma_metrics", {})
    micro = gamma_metrics.get("micro_structure", {})
    anchors = targets.get("sentiment_anchors", {})
    
    # Flow Data extraction
    directional = targets.get("directional_metrics", {})
    dex_bias = directional.get("dex_bias", "Unknown")
    dex_strength = directional.get("dex_bias_strength", "Unknown")
    vanna_dir = directional.get("vanna_dir", "Unknown")
    
    micro_hint = f"Wall Physics: {micro.get('wall_type', 'Unknown')}, Breakout Difficulty: {micro.get('breakout_difficulty', 'Unknown')}"
    anchor_hint = f"Sentiment Anchor (Max Pain): {anchors.get('max_pain', 'N/A')}"
    flow_hint = f"Inventory: {dex_bias} ({dex_strength}), Mechanical Flow: {vanna_dir}"
    
    return f"""Analyze the market scenarios.

    ## PHASE 3 INTELLIGENCE
    - **Physics**: {micro_hint}
    - **Flows**: {flow_hint}
    - **Anchors**: {anchor_hint}

    ## SCORING DATA
    ```json
    {json.dumps(data, ensure_ascii=False, indent=2)}
    ```
    
    ## INSTRUCTIONS
    1. Generate 3-5 scenarios.
    2. **Physics Check**: IF Wall is 'Rigid', increase probability of 'Pinning/Rejection'.
    3. **Flow Check**: 
       - IF Price Direction matches Inventory (DEX), mark as **Organic**.
       - IF Price matches Vanna but not DEX, mark as **Mechanical_Vanna**.
       - IF Price opposes Inventory, mark as **Divergent** (High Risk).
    4. **Range Logic**: IF Scenario is 'Range', treat Max Pain as a magnetic target.

    Return JSON.
    """