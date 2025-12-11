"""
Agent 6: 策略生成 Schema (v2.1)

变更:
1. execution_plan 中 entry_timing 设为 required
"""


def get_schema() -> dict:
    """获取 Agent 6 输出 Schema"""
    return {
        "type": "object",
        "required": ["meta_info", "strategies"],
        "properties": {
            
            "meta_info": {
                "type": "object",
                "required": ["trade_style", "t_scale", "lambda_factor", "em1_dollar"],
                "properties": {
                    "trade_style": {"type": "string", "enum": ["SCALP", "SWING", "POSITION"]},
                    "t_scale": {"type": "number"},
                    "lambda_factor": {"type": "number"},
                    "em1_dollar": {"type": "number"}
                },
                "additionalProperties": False
            },
            
            "validation_flags": {
                "type": "object",
                "properties": {
                    "is_vetoed": {"type": "boolean"},
                    "veto_reason": {"type": "string"},
                    "strategy_bias": {"type": "string", "enum": ["Credit_Favored", "Debit_Favored", "Neutral"]},
                    "confidence_penalty": {"type": "number"}
                },
                "additionalProperties": False
            },
            
            "strategies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "strategy_name",
                        "strategy_type",
                        "structure",
                        "legs",
                        "execution_plan",
                        "quant_metrics",
                        "risk_management"
                    ],
                    "properties": {
                        "strategy_name": {"type": "string"},
                        "strategy_type": {
                            "type": "string",
                            "enum": ["directional", "volatility", "income", "hedge", "WAIT"]
                        },
                        "structure": {"type": "string"},
                        "description": {"type": "string"},
                        "suitability_score": {"type": "integer"},
                        
                        "legs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["action", "strike", "rationale"],
                                "properties": {
                                    "action": {"type": "string", "enum": ["buy", "sell"]},
                                    "option_type": {"type": "string", "enum": ["call", "put"]},
                                    "strike": {"type": "number"},
                                    "quantity": {"type": "integer"},
                                    "expiry_dte": {"type": "integer"},
                                    "rationale": {"type": "string"}
                                },
                                "additionalProperties": False
                            }
                        },
                        
                        # ------------------------------------------
                        # 执行计划 (变更)
                        # ------------------------------------------
                        "execution_plan": {
                            "type": "object",
                            "required": [
                                "entry_trigger", 
                                "entry_timing",  # ✅ 新增：必须输出，承载 execution_guidance
                                "holding_period", 
                                "exit_plan"
                            ],
                            "properties": {
                                "entry_trigger": {"type": "string"},
                                "entry_timing": {
                                    "type": "string",
                                    "description": "入场时机描述，必须包含上游的执行建议 (如等待尾盘)"
                                },
                                "holding_period": {"type": "string"},
                                "exit_plan": {
                                    "type": "object",
                                    "required": ["profit_target", "stop_loss"],
                                    "properties": {
                                        "profit_target": {"type": "string"},
                                        "stop_loss": {"type": "string"},
                                        "time_decay_exit": {"type": "string"},
                                        "adjustment": {"type": "string"}
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "additionalProperties": False
                        },
                        
                        "quant_metrics": {
                            "type": "object",
                            "properties": {
                                "setup_cost": {"type": "string"},
                                "max_profit": {"type": "number"},
                                "max_loss": {"type": "number"},
                                "rr_ratio": {"type": "string"},
                                "pw_estimate": {"type": "string"},
                                "breakeven": {"type": "array", "items": {"type": "number"}},
                                "greeks_exposure": {
                                    "type": "object",
                                    "properties": {
                                        "delta": {"type": "string"},
                                        "gamma": {"type": "string"},
                                        "vega": {"type": "string"},
                                        "theta": {"type": "string"}
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "additionalProperties": False
                        },
                        
                        "risk_management": {"type": "string"},
                        "pros": {"type": "array", "items": {"type": "string"}},
                        "cons": {"type": "array", "items": {"type": "string"}}
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False
    }