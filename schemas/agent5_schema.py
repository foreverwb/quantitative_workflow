"""
Agent 5: 场景分析 Schema (v2.2)

变更:
1. 移除 validation_summary 中的 noise_level
"""


def get_schema() -> dict:
    """返回 Agent 5 的 JSON Schema"""
    return {
        "type": "object",
        "required": [
            "gamma_regime",
            "scoring",
            "scenario_classification",
            "scenarios",
            "validation_summary",
            "entry_threshold_check"
        ],
        "properties": {
            "gamma_regime": {
                "type": "object",
                "required": ["vol_trigger", "spot_vs_trigger", "regime_note"],
                "properties": {
                    "vol_trigger": {"type": "number"},
                    "spot_vs_trigger": {"type": "string", "enum": ["above", "below", "near"]},
                    "base_scenario": {"type": "string"},
                    "regime_note": {"type": "string"}
                }
            },
            "scoring": {
                "type": "object",
                "properties": {
                    "total_score": {"type": "number"},
                    "weight_breakdown": {"type": "string"}
                }
            },
            "scenario_classification": {
                "type": "object",
                "required": ["primary_scenario", "scenario_probability"],
                "properties": {
                    "primary_scenario": {"type": "string"},
                    "scenario_probability": {"type": "integer"}
                }
            },
            "scenarios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "scenario_name", 
                        "probability", 
                        "direction",
                        "validation_warnings"
                    ],
                    "properties": {
                        "scenario_name": {"type": "string"},
                        "probability": {"type": "integer"},
                        "direction": {"type": "string"},
                        "volatility_expectation": {"type": "string"},
                        "validation_warnings": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            },
            "validation_summary": {
                "type": "object",
                "required": ["warnings", "overall_confidence_adjustment"],
                "properties": {
                    "has_fake_breakout_risk": {"type": "boolean"},
                    "has_vol_suppression": {"type": "boolean"},
                    # 移除了 noise_level
                    "overall_confidence_adjustment": {"type": "number"},
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "entry_threshold_check": {"type": "string"},
            "entry_rationale": {"type": "string"},
            "key_levels": {"type": "object"},
            "risk_warning": {"type": "string"}
        }
    }