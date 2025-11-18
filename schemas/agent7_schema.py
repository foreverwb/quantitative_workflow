"""Agent 7: 策略对比 Schema"""
def get_schema() -> dict:
    return {
        "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "comparison_summary": {
                        "type": "object",
                        "properties": {
                            "analysis_timestamp": {"type": "string"},
                            "positive_ev_count": {"type": "integer"},
                            "recommended_count": {"type": "integer"},
                            "total_strategies": {"type": "integer"}
                        }
                    },
                    "ranking": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rank": {"type": "integer"},
                                "strategy_type": {"type": "string"},
                                "structure": {"type": "string"},
                                "metrics": {
                                    "type": "object",
                                    "properties": {
                                        "ev": {"type": "number"},
                                        "max_loss": {"type": "number"},
                                        "max_profit": {"type": "number"},
                                        "pw": {"type": "number"},
                                        "rar": {"type": "number"},
                                        "rr_ratio": {"type": "string"}
                                    }
                                },
                                "assessment": {
                                    "type": "object",
                                    "properties": {
                                        "composite_score": {"type": "integer"},
                                        "liquidity_note": {"type": "string"},
                                        "liquidity_pass": {"type": "boolean"},
                                        "match_reason": {"type": "string"},
                                        "scenario_match": {"type": "string"}
                                    }
                                },
                                "recommendation": {"type": "string"},
                                "note": {"type": "string"}
                            }
                        }
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
                                }
                            },
                            "secondary": {
                                "type": "object",
                                "properties": {
                                    "strategy_type": {"type": "string"},
                                    "allocation": {"type": "string"},
                                    "rationale": {"type": "string"}
                                }
                            },
                            "avoid": {
                                "type": "object",
                                "properties": {
                                    "strategy_type": {"type": "string"},
                                    "reason": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "required": [
                    "symbol",
                    "comparison_summary",
                    "ranking",
                    "final_recommendation",
                    "execution_priority"
                ]
            }