"""Agent 6: 策略生成 Schema"""

def get_schema() -> dict:
    return {
        "type": "object",
                "properties": {
                    "strategies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "strategy_type": {"type": "string"},
                                "structure": {"type": "string"},
                                "description": {"type": "string"},
                                "legs": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "action": {"type": "string"},
                                            "quantity": {"type": "number"},
                                            "rationale": {"type": "string"},
                                            "strike": {"type": "number"},
                                            "type": {"type": "string"}
                                        }
                                    }
                                },
                                "dte": {"type": "string"},
                                "dte_rationale": {"type": "string"},
                                "greeks_target": {
                                    "type": "object",
                                    "properties": {
                                        "delta": {"type": "string"},
                                        "delta_range": {"type": "string"},
                                        "theta_min": {"type": "string"},
                                        "vega_max": {"type": "string"},
                                        "vega_min": {"type": "string"}
                                    }
                                },
                                "rr_calculation": {
                                    "type": "object",
                                    "properties": {
                                        "credit": {"type": "number"},
                                        "debit": {"type": "number"},
                                        "formula": {"type": "string"},
                                        "max_loss": {"type": "number"},
                                        "max_profit": {"type": "number"},
                                        "rr_note": {"type": "string"},
                                        "rr_ratio": {"type": "string"}
                                    }
                                },
                                "pw_calculation": {
                                    "type": "object",
                                    "properties": {
                                        "formula": {"type": "string"},
                                        "pw_estimate": {"type": "string"},
                                        "pw_note": {"type": "string"},
                                        "pw_综合判断": {"type": "string"}
                                    }
                                },
                                "entry_trigger": {"type": "string"},
                                "entry_timing": {"type": "string"},
                                "exit_plan": {
                                    "type": "object",
                                    "properties": {
                                        "adjustment": {"type": "string"},
                                        "profit_target": {"type": "string"},
                                        "stop_loss": {"type": "string"},
                                        "time_decay_exit": {"type": "string"}
                                    }
                                },
                                "risk_note": {"type": "string"}
                            },
                            "required": [
                                "strategy_type",
                                "structure",
                                "description",
                                "legs",
                                "dte",
                                "greeks_target",
                                "rr_calculation",
                                "pw_calculation",
                                "entry_trigger",
                                "exit_plan",
                                "risk_note"
                            ]
                        }
                    }
                },
                "required": ["strategies"]
            }