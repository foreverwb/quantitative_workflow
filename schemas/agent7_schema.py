"""
Agent 7: 策略排序 Schema (v2.0)

变更:
1. ranking 数组增加 quality_adjustment, quality_filter_notes 字段
2. 新增 quality_filter_summary 顶层字段
3. 增强 assessment 结构
"""


def get_schema() -> dict:
    """返回 Agent 7 的 JSON Schema"""
    return {
        "type": "object",
        "required": [
            "symbol",
            "comparison_summary",
            "ranking",
            "quality_filter_summary", 
            "final_recommendation",
            "execution_priority"
        ],
        "properties": {
            
            "symbol": {"type": "string"},
            
            "comparison_summary": {
                "type": "object",
                "properties": {
                    "analysis_timestamp": {"type": "string"},
                    "total_strategies": {"type": "integer"},
                    "positive_ev_count": {"type": "integer"},
                    "recommended_count": {"type": "integer"},
                    "filtered_count": {"type": "integer"}
                },
                "additionalProperties": False
            },
            
            # ==========================================
            # 3. 质量过滤摘要 (新增)
            # ==========================================
            "quality_filter_summary": {
                "type": "object",
                "required": ["filters_triggered", "overall_confidence"],
                "properties": {
                    "filters_triggered": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "affected_strategies": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "overall_confidence": {"type": "number"},
                    "zero_dte_ratio": {"type": "number"},
                    "is_vetoed": {"type": "boolean"},
                    "strategy_bias": {"type": "string", "enum": ["Credit_Favored", "Debit_Favored", "Neutral"]},
                    "filter_notes": {"type": "string"}
                },
                "additionalProperties": False
            },
            
            "ranking": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["rank", "strategy_name", "overall_score", "rating"],
                    "properties": {
                        "rank": {"type": "integer"},
                        "strategy_name": {"type": "string"},
                        "strategy_type": {"type": "string"},
                        "structure": {"type": "string"},
                        
                        "overall_score": {"type": "number"},
                        "quality_adjustment": {
                            "type": "number",
                            "description": "【新增】质量调整分数 (正/负)"
                        },
                        "rating": {"type": "string", "enum": ["strong_buy", "buy", "hold", "avoid"]},
                        
                        "score_breakdown": {
                            "type": "object",
                            "properties": {
                                "scenario_match_score": {"type": "number"},
                                "risk_reward_score": {"type": "number"},
                                "greeks_health_score": {"type": "number"},
                                "execution_difficulty_score": {"type": "number"},
                                "volatility_fit_score": {"type": "number"},
                                "quality_score": {"type": "number"}
                            },
                            "additionalProperties": False
                        },
                        
                        "metrics": {
                            "type": "object",
                            "properties": {
                                "ev": {"type": "number"},
                                "rar": {"type": "number"},
                                "pw": {"type": "number"},
                                "rr_ratio": {"type": "string"},
                                "max_profit": {"type": "number"},
                                "max_loss": {"type": "number"}
                            },
                            "additionalProperties": False
                        },
                        
                        "assessment": {
                            "type": "object",
                            "properties": {
                                "scenario_match": {"type": "string"},
                                "match_reason": {"type": "string"},
                                "liquidity_pass": {"type": "boolean"},
                                "liquidity_note": {"type": "string"},
                                "composite_score": {"type": "number"}
                            },
                            "additionalProperties": False
                        },
                        
                        "quality_filter_notes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "【新增】质量过滤说明 (触发了哪些规则)"
                        },
                        
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                        "recommendation_reason": {"type": "string"},
                        "best_for": {"type": "string"},
                        "note": {"type": "string"}
                    },
                    "additionalProperties": False
                }
            },
            
            "top3_comparison": {
                "type": "object",
                "properties": {
                    "comparison_table": {"type": "string"},
                    "winner": {"type": "string"},
                    "winner_reason": {"type": "string"}
                },
                "additionalProperties": False
            },
            
            "final_recommendation": {"type": "string"},
            
            "execution_priority": {
                "type": "object",
                "properties": {
                    "primary": {
                        "type": "object",
                        "properties": {
                            "strategy_type": {"type": "string"},
                            "allocation": {"type": "string"},
                            "rationale": {"type": "string"}
                        },
                        "additionalProperties": False
                    },
                    "secondary": {
                        "type": "object",
                        "properties": {
                            "strategy_type": {"type": "string"},
                            "allocation": {"type": "string"},
                            "rationale": {"type": "string"}
                        },
                        "additionalProperties": False
                    },
                    "avoid": {
                        "type": "object",
                        "properties": {
                            "strategy_type": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            },
            
            "combination_advice": {
                "type": "object",
                "properties": {
                    "is_recommended": {"type": "boolean"},
                    "strategies": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"}
                },
                "additionalProperties": False
            },
            
            "risk_warnings": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "additionalProperties": False
    }