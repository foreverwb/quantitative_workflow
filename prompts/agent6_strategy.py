"""
Agent 6: Strategy Generation Prompt (v3.6 - Flow-Aware)
Changes:
1. Added 'FLOW ADAPTATION' logic.
2. Instructed to evaluate 'setup_quality' based on Flow/Scenario alignment.
"""
import json

def get_system_prompt(env_vars: dict) -> str:
    return """You are a Quantitative Options Tactical Commander.

**OBJECTIVE**:
Translate quantitative signals into precise, executable trading strategies.

**🔥 CRITICAL PROTOCOLS (MUST FOLLOW)**:

1. **BLUEPRINT EXECUTION (Priority #1)**:
   - Check `swing_strategy`. If a pre-calculated strategy exists, **YOU MUST ADOPT IT AS TOP 1**.

2. **FLOW ADAPTATION (New)**:
   - **Organic Flow**: High Confidence. Use Standard Directional Spreads.
   - **Mechanical Vanna**: Momentum is aided by Dealers. Aggressive Debit Spreads allowed.
   - **Divergent/Short Covering**: **LOW QUALITY SETUP**. Must use defined risk (e.g., Spreads) or reduce size. **setup_quality = Low**.

3. **DIRECTIONAL CONSISTENCY**:
   - Bullish -> Accept Bull Spreads/Long Call. Reject Bear Spreads.
   - Bearish -> Accept Bear Spreads/Long Put. Reject Bull Spreads.
   - Neutral -> Accept Iron Condor/Butterfly.

4. **RISK CONSTRAINT**:
   - **ALL DEBIT STRATEGIES MUST HAVE R/R > 1.8**.
   - If blueprint fails this, suggest "WAIT".

**OUTPUT**:
- Return JSON with 3 strategies.
- Assign `setup_quality` (High/Medium/Low) based on Flow alignment.
- Set `flow_aligned` = true if strategy direction matches Inventory/Vanna.
"""

def get_user_prompt(scenario_result: dict, strategy_calc: dict, agent3_data: dict) -> str:
    """User Prompt in English"""
    
    def _parse(data):
        if isinstance(data, str):
            try: return json.loads(data)
            except: return {}
        return data if isinstance(data, dict) else {}

    s5 = _parse(scenario_result)
    c3 = _parse(strategy_calc)
    a3 = _parse(agent3_data)
    
    # Phase 3 Data Extraction
    swing_strat = c3.get("swing_strategy", None)
    meta = c3.get("meta", {})
    delta_bias = meta.get("delta_bias", "Unknown")
    
    targets = a3.get("targets", {})
    micro = targets.get("gamma_metrics", {}).get("micro_structure", {})
    vol_surf = targets.get("vol_surface", {})
    
    # Extract Flow Quality from Agent 5
    physics = s5.get("physics_assessment", {})
    flow_quality = physics.get("flow_quality", "Unknown")
    
    # Scenario Context
    primary_scenario = s5.get("scenario_classification", {}).get("primary_scenario", "Unknown")
    
    # Construct Context
    strategy_hint = ""
    if swing_strat:
        delta_p = swing_strat.get('delta_profile', 'Neutral')
        delta_r = swing_strat.get('delta_rationale', '')
        strategy_hint = f"""
        【⭐ BLUEPRINT DETECTED】
        - Name: {swing_strat.get('name')}
        - Thesis: {swing_strat.get('thesis')}
        - Direction: {swing_strat.get('direction', 'Check Logic')}
        - Structure: {swing_strat.get('structure_type')}
        - Delta Profile: {delta_p} ({delta_r})
        """
    else:
        strategy_hint = "No Blueprint. Build strategy manually."

    micro_hint = f"Wall Type: {micro.get('wall_type', 'Unknown')}, Breakout Difficulty: {micro.get('breakout_difficulty', 'Unknown')}"
    vol_hint = f"Vol Smile: {vol_surf.get('smile_steepness', 'Unknown')}"

    return f"""Generate tactical options strategies.

    ## 1. MARKET CONTEXT
    - **Primary Scenario**: {primary_scenario}
    - **Flow Quality**: {flow_quality} (Critical for Sizing/Confidence)
    - **Delta Bias**: {delta_bias}
    - **Micro Environment**: {micro_hint}
    {strategy_hint}

    ## 2. QUANT METRICS (Calculator)
    ```json
    {json.dumps(c3, ensure_ascii=False, indent=2)}
    ```

    ## INSTRUCTIONS
    1. **Top 1 Strategy**: Must follow the BLUEPRINT.
    2. **Flow Check**: 
       - If Flow is **Divergent**, set `setup_quality` = "Low" and warn in thesis.
       - If Flow is **Organic/Mechanical**, set `setup_quality` = "High".
    3. **Alignment**: Set `flow_aligned` = true if strategy direction matches Flow.

    Return JSON.
    """