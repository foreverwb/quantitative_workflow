"""
Agent 5: 场景分析 Schema (v2.1)

变更:
1. 将 validation_summary 加入顶层 required
2. 将 validation_warnings 加入 scenarios required
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
            
            # ==========================================
            # 1. Gamma Regime 状态
            # ==========================================
            "gamma_regime": {
                "type": "object",
                "required": ["vol_trigger", "spot_vs_trigger", "regime_note"],
                "properties": {
                    "vol_trigger": {
                        "type": "number",
                        "description": "Vol Trigger 价格"
                    },
                    "spot_vs_trigger": {
                        "type": "string",
                        "enum": ["above", "below", "near"],
                        "description": "现价相对 Vol Trigger 位置"
                    },
                    "base_scenario": {
                        "type": "string",
                        "description": "基础场景 (区间/趋势/过渡)"
                    },
                    "regime_note": {
                        "type": "string",
                        "description": "Gamma Regime 说明"
                    }
                },
                "additionalProperties": False
            },
            
            # ==========================================
            # 2. 四维评分
            # ==========================================
            "scoring": {
                "type": "object",
                "properties": {
                    "gamma_regime_score": {"type": "number"},
                    "break_wall_score": {"type": "number"},
                    "direction_score": {"type": "number"},
                    "iv_score": {"type": "number"},
                    "total_score": {"type": "number"},
                    "weight_breakdown": {"type": "string"},
                    "weight_regime": {
                        "type": "string",
                        "enum": ["panic", "normal", "calm"],
                        "description": "权重模式"
                    }
                },
                "additionalProperties": False
            },
            
            # ==========================================
            # 3. 场景分类 (主导剧本)
            # ==========================================
            "scenario_classification": {
                "type": "object",
                "required": ["primary_scenario", "scenario_probability"],
                "properties": {
                    "primary_scenario": {
                        "type": "string",
                        "description": "主导剧本 (趋势上行/趋势下行/区间震荡/Gamma翻转)"
                    },
                    "scenario_probability": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "主导剧本概率 (%)"
                    },
                    "scenario_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "置信度等级"
                    },
                    "secondary_scenarios": {
                        "type": "array",
                        "description": "次要剧本列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "probability": {"type": "integer"}
                            },
                            "additionalProperties": False
                        }
                    }
                },
                "additionalProperties": False
            },
            
            # ==========================================
            # 4. 场景详情数组 (含验证警告)
            # ==========================================
            "scenarios": {
                "type": "array",
                "description": "3-5 个差异化场景",
                "items": {
                    "type": "object",
                    "required": [
                        "scenario_name", 
                        "probability", 
                        "direction",
                        "validation_warnings" 
                    ],
                    "properties": {
                        "scenario_name": {
                            "type": "string",
                            "description": "场景名称"
                        },
                        "probability": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "发生概率 (%)"
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["bullish", "bearish", "neutral"],
                            "description": "方向"
                        },
                        "volatility_expectation": {
                            "type": "string",
                            "enum": ["expanding", "contracting", "stable"],
                            "description": "IV 变化预期"
                        },
                        "time_horizon": {
                            "type": "integer",
                            "description": "时间窗口 (天)"
                        },
                        "trigger_conditions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "触发条件列表"
                        },
                        "greeks_impact": {
                            "type": "string",
                            "description": "Greeks 表现描述"
                        },
                        "risk_reward_ratio": {
                            "type": "string",
                            "description": "风险收益比"
                        },
                        "key_levels": {
                            "type": "object",
                            "properties": {
                                "support": {"type": "number"},
                                "resistance": {"type": "number"},
                                "pivot": {"type": "number"}
                            },
                            "description": "关键价格位",
                            "additionalProperties": False
                        },
                        "validation_warnings": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "【新增】验证警告 (假突破风险/波动率受压/结构噪音高)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "补充说明"
                        }
                    },
                    "additionalProperties": False
                }
            },
            
            # ==========================================
            # 5. 验证摘要 (新增顶层字段)
            # ==========================================
            "validation_summary": {
                "type": "object",
                "description": "【新增】validation_metrics 检查摘要",
                "required": ["warnings", "overall_confidence_adjustment"],
                "properties": {
                    "has_fake_breakout_risk": {
                        "type": "boolean",
                        "description": "是否存在假突破风险"
                    },
                    "has_vol_suppression": {
                        "type": "boolean",
                        "description": "是否存在波动率受压"
                    },
                    "noise_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "0DTE 噪音等级"
                    },
                    "overall_confidence_adjustment": {
                        "type": "number",
                        "description": "整体置信度调整 (-1 到 0)"
                    },
                    "warnings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "所有验证警告汇总"
                    }
                },
                "additionalProperties": False
            },
            
            # ==========================================
            # 6. 入场建议
            # ==========================================
            "entry_threshold_check": {
                "type": "string",
                "enum": ["入场", "轻仓试探", "观望"],
                "description": "基于评分的入场建议"
            },
            "entry_rationale": {
                "type": "string",
                "description": "入场理由"
            },
            
            # ==========================================
            # 7. 关键价位
            # ==========================================
            "key_levels": {
                "type": "object",
                "description": "全市场关键价位汇总",
                "properties": {
                    "support": {"type": "number"},
                    "resistance": {"type": "number"},
                    "trigger_line": {"type": "number"},
                    "current_spot": {"type": "number"}
                },
                "additionalProperties": False
            },
            
            # ==========================================
            # 8. 风险警示
            # ==========================================
            "risk_warning": {
                "type": "string",
                "description": "综合风险警示信息"
            }
        },
        "additionalProperties": False
    }