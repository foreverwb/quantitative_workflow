"""
Agent 5 JSON Schema - 场景分析输出
"""

def get_schema() -> dict:
    """返回 Agent 5 的 JSON Schema"""
    return {
        "type": "object",
        "required": [
            "gamma_regime",
            "scoring",
            "scenario_classification",
            "entry_threshold_check"
        ],
        "properties": {
            "gamma_regime": {
                "type": "object",
                "required": ["vol_trigger", "spot_vs_trigger", "regime_note"],
                "properties": {
                    "vol_trigger": {"type": "number"},
                    "spot_vs_trigger": {
                        "enum": ["above", "below", "near"],
                        "type": "string"
                    },
                    "regime_note": {"type": "string"}
                }
            },
            "scoring": {
                "type": "object",
                "properties": {
                    "gamma_regime_score": {"type": "number"},
                    "break_wall_score": {"type": "number"},
                    "direction_score": {"type": "number"},
                    "iv_score": {"type": "number"},
                    "total_score": {"type": "number"},
                    "weight_breakdown": {"type": "string"}
                }
            },
            "scenario_classification": {
                "type": "object",
                "properties": {
                    "primary_scenario": {"type": "string"},
                    "scenario_probability": {"type": "integer"},
                    "secondary_scenarios": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "probability": {"type": "integer"}
                            }
                        }
                    }
                }
            },
            "entry_threshold_check": {
                "enum": ["入场", "轻仓试探", "观望"],
                "type": "string"
            },
            "risk_warning": {"type": "string"}
        }
    }
