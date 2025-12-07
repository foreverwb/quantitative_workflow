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
            
            # ==========================================
            # 1. 基础信息
            # ==========================================
            "symbol": {
                "type": "string",
                "description": "标的代码"
            },
            
            # ==========================================
            # 2. 对比摘要
            # ==========================================
            "comparison_summary": {
                "type": "object",
                "properties": {
                    "analysis_timestamp": {
                        "type": "string",
                        "description": "分析时间戳"
                    },
                    "total_strategies": {
                        "type": "integer",
                        "description": "总策略数"
                    },
                    "positive_ev_count": {
                        "type": "integer",
                        "description": "正 EV 策略数"
                    },
                    "recommended_count": {
                        "type": "integer",
                        "description": "推荐策略数"
                    },
                    "filtered_count": {
                        "type": "integer",
                        "description": "【新增】被过滤策略数"
                    }
                }
            },
            
            # ==========================================
            # 3. 质量过滤摘要 (新增)
            # ==========================================
            "quality_filter_summary": {
                "type": "object",
                "description": "【新增】质量过滤执行结果",
                "required": ["filters_triggered", "overall_confidence"],
                "properties": {
                    "filters_triggered": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "触发的过滤规则列表 (0DTE_HIGH/VOLUME_DIVERGENCE/BIAS_MISMATCH)"
                    },
                    "affected_strategies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "受影响的策略名称"
                    },
                    "overall_confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "整体置信度 (0-1)，考虑噪音后"
                    },
                    "zero_dte_ratio": {
                        "type": "number",
                        "description": "0DTE 占比"
                    },
                    "is_vetoed": {
                        "type": "boolean",
                        "description": "是否存在量价背离"
                    },
                    "strategy_bias": {
                        "type": "string",
                        "enum": ["Credit_Favored", "Debit_Favored", "Neutral"],
                        "description": "策略偏好"
                    },
                    "filter_notes": {
                        "type": "string",
                        "description": "过滤说明"
                    }
                }
            },
            
            # ==========================================
            # 4. 策略排名数组
            # ==========================================
            "ranking": {
                "type": "array",
                "description": "按综合得分排序的策略列表",
                "items": {
                    "type": "object",
                    "required": ["rank", "strategy_name", "overall_score", "rating"],
                    "properties": {
                        "rank": {
                            "type": "integer",
                            "description": "排名"
                        },
                        "strategy_name": {
                            "type": "string",
                            "description": "策略名称"
                        },
                        "strategy_type": {
                            "type": "string",
                            "description": "策略类型"
                        },
                        "structure": {
                            "type": "string",
                            "description": "策略结构"
                        },
                        
                        # ---------- 评分 ----------
                        "overall_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "综合评分 (0-100)"
                        },
                        "quality_adjustment": {
                            "type": "number",
                            "description": "【新增】质量调整分数 (正/负)"
                        },
                        "rating": {
                            "type": "string",
                            "enum": ["strong_buy", "buy", "hold", "avoid"],
                            "description": "评级"
                        },
                        
                        # ---------- 分项评分 ----------
                        "score_breakdown": {
                            "type": "object",
                            "description": "分项评分",
                            "properties": {
                                "scenario_match_score": {
                                    "type": "number",
                                    "description": "场景匹配分 (0-100)"
                                },
                                "risk_reward_score": {
                                    "type": "number",
                                    "description": "风险收益分 (0-100)"
                                },
                                "greeks_health_score": {
                                    "type": "number",
                                    "description": "Greeks 健康分 (0-100)"
                                },
                                "execution_difficulty_score": {
                                    "type": "number",
                                    "description": "执行难度分 (0-100)"
                                },
                                "volatility_fit_score": {
                                    "type": "number",
                                    "description": "波动率适配分 (0-100)"
                                },
                                "quality_score": {
                                    "type": "number",
                                    "description": "【新增】质量得分 (0-100)"
                                }
                            }
                        },
                        
                        # ---------- 量化指标 ----------
                        "metrics": {
                            "type": "object",
                            "properties": {
                                "ev": {"type": "number"},
                                "rar": {"type": "number"},
                                "pw": {"type": "number"},
                                "rr_ratio": {"type": "string"},
                                "max_profit": {"type": "number"},
                                "max_loss": {"type": "number"}
                            }
                        },
                        
                        # ---------- 评估 ----------
                        "assessment": {
                            "type": "object",
                            "properties": {
                                "scenario_match": {
                                    "type": "string",
                                    "enum": ["高", "中", "低"],
                                    "description": "场景匹配度"
                                },
                                "match_reason": {"type": "string"},
                                "liquidity_pass": {"type": "boolean"},
                                "liquidity_note": {"type": "string"},
                                "composite_score": {"type": "number"}
                            }
                        },
                        
                        # ---------- 质量过滤 (新增) ----------
                        "quality_filter_notes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "【新增】质量过滤说明 (触发了哪些规则)"
                        },
                        
                        # ---------- 推荐 ----------
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "主要优势"
                        },
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "主要劣势"
                        },
                        "recommendation_reason": {
                            "type": "string",
                            "description": "推荐理由 (100字以内)"
                        },
                        "best_for": {
                            "type": "string",
                            "description": "最适合的投资者类型/市场环境"
                        },
                        "note": {
                            "type": "string",
                            "description": "补充说明"
                        }
                    }
                }
            },
            
            # ==========================================
            # 5. Top 3 对比
            # ==========================================
            "top3_comparison": {
                "type": "object",
                "description": "前 3 名策略详细对比",
                "properties": {
                    "comparison_table": {
                        "type": "string",
                        "description": "对比表格 (Markdown 格式)"
                    },
                    "winner": {
                        "type": "string",
                        "description": "最优策略"
                    },
                    "winner_reason": {
                        "type": "string",
                        "description": "胜出原因"
                    }
                }
            },
            
            # ==========================================
            # 6. 最终推荐
            # ==========================================
            "final_recommendation": {
                "type": "string",
                "description": "最终推荐总结"
            },
            
            # ==========================================
            # 7. 执行优先级
            # ==========================================
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
                        "description": "首选策略"
                    },
                    "secondary": {
                        "type": "object",
                        "properties": {
                            "strategy_type": {"type": "string"},
                            "allocation": {"type": "string"},
                            "rationale": {"type": "string"}
                        },
                        "description": "备选策略"
                    },
                    "avoid": {
                        "type": "object",
                        "properties": {
                            "strategy_type": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "description": "应避免的策略"
                    }
                }
            },
            
            # ==========================================
            # 8. 组合建议
            # ==========================================
            "combination_advice": {
                "type": "object",
                "description": "多策略组合建议",
                "properties": {
                    "is_recommended": {
                        "type": "boolean",
                        "description": "是否推荐组合"
                    },
                    "strategies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "组合策略列表"
                    },
                    "rationale": {
                        "type": "string",
                        "description": "组合理由"
                    }
                }
            },
            
            # ==========================================
            # 9. 风险警示
            # ==========================================
            "risk_warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "风险警示列表"
            }
        }
    }