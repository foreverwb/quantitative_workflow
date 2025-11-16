"""
JSON Schema 集中管理
避免在多个文件中重复定义

使用方式:
    from models.schemas import SchemaManager
    
    # Agent 3
    schema = SchemaManager.get_data_validation_schema()
    
    # Agent 5
    schema = SchemaManager.get_scenario_analysis_schema()
"""

class SchemaManager:
    """统一管理所有 Agent 的 JSON Schema"""
    
    @staticmethod
    def get_data_validation_schema():
        """Agent 3: 数据校验 Schema"""
        return {
            "name": "data_validation_result",
            "schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["data_ready", "missing_data"],
                        "description": "数据状态"
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "时间戳,格式 YYYY-MM-DDTHH:mm:ss"
                    },
                    "targets": {
                        "type": "object",
                        "description": "标的数据(必须是字典)",
                        "properties": {
                            "symbol": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["ready", "missing_data"]
                            },
                            "spot_price": {
                                "type": "number",
                                "description": "现价,若缺失使用 -999"
                            },
                            "em1_dollar": {
                                "type": "number",
                                "description": "预期单日波幅,若缺失使用 -999"
                            },
                            "walls": {
                                "type": "object",
                                "properties": {
                                    "call_wall": {"type": "number"},
                                    "put_wall": {"type": "number"},
                                    "major_wall": {"type": "number"},
                                    "major_wall_type": {
                                        "type": "string",
                                        "enum": ["call", "put", "N/A"]
                                    }
                                },
                                "required": ["call_wall", "put_wall", "major_wall", "major_wall_type"]
                            },
                            "gamma_metrics": {
                                "type": "object",
                                "properties": {
                                    "gap_distance_dollar": {"type": "number"},
                                    "gap_distance_em1_multiple": {"type": "number"},
                                    "cluster_strength_ratio": {"type": "number"},
                                    "net_gex": {"type": "number"},
                                    "net_gex_sign": {
                                        "type": "string",
                                        "enum": ["positive_gamma", "negative_gamma", "neutral", "N/A"]
                                    },
                                    "vol_trigger": {"type": "number"},
                                    "spot_vs_trigger": {
                                        "type": "string",
                                        "enum": ["above", "below", "near", "N/A"]
                                    },
                                    "monthly_cluster_override": {"type": "boolean"}
                                },
                                "required": [
                                    "gap_distance_dollar",
                                    "gap_distance_em1_multiple",
                                    "cluster_strength_ratio",
                                    "net_gex",
                                    "net_gex_sign",
                                    "vol_trigger",
                                    "spot_vs_trigger",
                                    "monthly_cluster_override"
                                ]
                            },
                            "directional_metrics": {
                                "type": "object",
                                "properties": {
                                    "dex_same_dir_pct": {"type": "number"},
                                    "vanna_dir": {
                                        "type": "string",
                                        "enum": ["up", "down", "flat", "N/A"]
                                    },
                                    "vanna_confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low", "N/A"]
                                    },
                                    "iv_path": {
                                        "type": "string",
                                        "enum": ["升", "降", "平", "数据不足"]
                                    },
                                    "iv_path_confidence": {
                                        "type": "string",
                                        "enum": ["high", "medium", "low"]
                                    }
                                },
                                "required": [
                                    "dex_same_dir_pct",
                                    "vanna_dir",
                                    "vanna_confidence",
                                    "iv_path",
                                    "iv_path_confidence"
                                ]
                            },
                            "atm_iv": {
                                "type": "object",
                                "properties": {
                                    "iv_7d": {"type": "number"},
                                    "iv_14d": {"type": "number"},
                                    "iv_source": {
                                        "type": "string",
                                        "enum": ["7d", "14d", "21d_fallback", "N/A"]
                                    }
                                },
                                "required": ["iv_7d", "iv_14d", "iv_source"]
                            }
                        },
                        "required": [
                            "symbol",
                            "status",
                            "spot_price",
                            "em1_dollar",
                            "walls",
                            "gamma_metrics",
                            "directional_metrics",
                            "atm_iv"
                        ]
                    },
                    "indices": {
                        "type": "object",
                        "description": "指数背景(可选)",
                        "properties": {
                            "spx": {
                                "type": "object",
                                "properties": {
                                    "net_gex_idx": {"type": "number"},
                                    "em1_dollar_idx": {"type": "number"},
                                    "spot_idx": {"type": "number"}
                                }
                            },
                            "qqq": {
                                "type": "object",
                                "properties": {
                                    "net_gex_idx": {"type": "number"},
                                    "em1_dollar_idx": {"type": "number"},
                                    "spot_idx": {"type": "number"}
                                }
                            }
                        }
                    },
                    "technical_analysis": {
                        "type": "object",
                        "description": "技术面(可选)",
                        "properties": {
                            "ta_score": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 2
                            },
                            "ta_commentary": {"type": "string"},
                            "chart_metadata": {
                                "type": "object",
                                "properties": {
                                    "platform": {"type": "string"},
                                    "timeframe": {"type": "string"},
                                    "latest_timestamp": {"type": "string"}
                                }
                            },
                            "indicators_raw": {
                                "type": "object",
                                "properties": {
                                    "price": {"type": "object"},
                                    "rsi": {"type": "object"},
                                    "bb": {"type": "object"},
                                    "macd": {"type": "object"},
                                    "volume": {"type": "object"}
                                }
                            }
                        }
                    },
                    "validation_summary": {
                        "type": "object",
                        "properties": {
                            "total_targets": {"type": "integer"},
                            "targets_ready": {"type": "integer"},
                            "total_fields_required": {"type": "integer"},
                            "fields_provided": {"type": "integer"},
                            "missing_count": {"type": "integer"},
                            "completion_rate": {"type": "integer"},
                            "warnings": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": [
                            "total_targets",
                            "targets_ready",
                            "total_fields_required",
                            "fields_provided",
                            "missing_count",
                            "completion_rate"
                        ]
                    },
                    "missing_fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "target": {"type": "string"},
                                "severity": {
                                    "type": "string",
                                    "enum": ["critical", "high", "medium", "low"]
                                },
                                "category": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["status", "timestamp", "targets", "validation_summary", "missing_fields"]
            }
        }
    
    @staticmethod
    def get_scenario_analysis_schema():
        """Agent 5: 剧本分析 Schema"""
        return {
            "name": "scenario_analysis_result",
            "schema": {
                "type": "object",
                "properties": {
                    "gamma_regime": {
                        "type": "object",
                        "properties": {
                            "vol_trigger": {"type": "number"},
                            "spot_vs_trigger": {
                                "type": "string",
                                "enum": ["above", "below", "near"]
                            },
                            "regime_note": {"type": "string"}
                        },
                        "required": ["vol_trigger", "spot_vs_trigger", "regime_note"]
                    },
                    "break_wall_assessment": {
                        "type": "object",
                        "properties": {
                            "break_note": {"type": "string"},
                            "break_probability": {"type": "string"},
                            "cluster_strength": {"type": "number"},
                            "gap_distance_em1": {"type": "number"}
                        }
                    },
                    "directional_signals": {
                        "type": "object",
                        "properties": {
                            "dex_same_dir": {"type": "number"},
                            "direction_note": {"type": "string"},
                            "direction_strength": {"type": "string"},
                            "vanna_confidence": {"type": "string"},
                            "vanna_dir": {"type": "string"}
                        }
                    },
                    "iv_dynamics": {
                        "type": "object",
                        "properties": {
                            "iv_note": {"type": "string"},
                            "iv_path": {"type": "string"},
                            "iv_path_confidence": {"type": "string"},
                            "iv_signal": {"type": "string"}
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
                            "adjustment_note": {"type": "string"},
                            "primary_scenario": {"type": "string"},
                            "scenario_probability": {"type": "integer"},
                            "secondary_scenarios": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "probability": {"type": "integer"},
                                        "type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "entry_threshold_check": {
                        "type": "string",
                        "enum": ["入场", "轻仓试探", "观望"]
                    },
                    "entry_rationale": {"type": "string"},
                    "key_levels": {
                        "type": "object",
                        "properties": {
                            "current_spot": {"type": "number"},
                            "resistance": {"type": "number"},
                            "support": {"type": "number"},
                            "trigger_line": {"type": "number"}
                        }
                    },
                    "risk_warning": {"type": "string"}
                },
                "required": [
                    "gamma_regime",
                    "scoring",
                    "scenario_classification",
                    "entry_threshold_check"
                ]
            }
        }
    
    @staticmethod
    def get_strategy_generation_schema():
        """Agent 6: 策略生成 Schema"""
        return {
            "name": "strategy_generation_result",
            "schema": {
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
        }
    
    @staticmethod
    def get_comparison_schema():
        """Agent 7: 策略对比 Schema"""
        return {
            "name": "comparison_result",
            "schema": {
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
        }