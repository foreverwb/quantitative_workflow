"""
Agent 6: 策略生成 Schema (动态适配版 v2.0)

变更:
1. 新增 meta_info 顶层元数据
2. 新增 validation_flags 验证旗标
3. 增强 execution_plan 结构
4. legs 增加 rationale 必填字段
"""


def get_schema() -> dict:
    """获取 Agent 6 输出 Schema"""
    return {
        "type": "object",
        "required": ["meta_info", "strategies"],
        "properties": {
            
            # ==========================================
            # 1. 顶层元数据
            # ==========================================
            "meta_info": {
                "type": "object",
                "description": "策略生成的元数据，记录关键动态参数",
                "required": ["trade_style", "t_scale", "lambda_factor", "em1_dollar"],
                "properties": {
                    "trade_style": {
                        "type": "string",
                        "enum": ["SCALP", "SWING", "POSITION"],
                        "description": "交易风格: SCALP(<5天)/SWING(5-25天)/POSITION(>25天)"
                    },
                    "t_scale": {
                        "type": "number",
                        "description": "波动率时间缩放系数，<0.8高波快节奏，>1.2低波慢节奏"
                    },
                    "lambda_factor": {
                        "type": "number",
                        "description": "空间安全边际系数，用于调整行权价宽窄"
                    },
                    "em1_dollar": {
                        "type": "number",
                        "description": "修正后的预期波幅 = EM1$ × λ"
                    }
                }
            },
            
            # ==========================================
            # 2. 验证旗标
            # ==========================================
            "validation_flags": {
                "type": "object",
                "description": "从 Code 3 传递的验证旗标",
                "required": ["is_vetoed"],
                "properties": {
                    "is_vetoed": {
                        "type": "boolean",
                        "description": "是否被否决（量价背离等）"
                    },
                    "veto_reason": {
                        "type": "string",
                        "description": "否决原因"
                    },
                    "strategy_bias": {
                        "type": "string",
                        "enum": ["Credit_Favored", "Debit_Favored", "Neutral"],
                        "description": "策略偏好: Credit_Favored(卖方)/Debit_Favored(买方)/Neutral"
                    },
                    "confidence_penalty": {
                        "type": "number",
                        "description": "噪音惩罚系数 (0-1)，用于仓位缩减建议"
                    }
                }
            },
            
            # ==========================================
            # 3. 策略数组
            # ==========================================
            "strategies": {
                "type": "array",
                "description": "生成的策略列表，通常包含保守/均衡/进取三种",
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
                        
                        # 基础信息
                        "strategy_name": {
                            "type": "string",
                            "description": "策略名称，格式: 风格 - 结构名 (如: 保守 - Iron Condor)"
                        },
                        "strategy_type": {
                            "type": "string",
                            "enum": ["directional", "volatility", "income", "hedge", "WAIT"],
                            "description": "策略类型: directional(方向)/volatility(波动率)/income(收入)/hedge(对冲)/WAIT(观望)"
                        },
                        "structure": {
                            "type": "string",
                            "description": "策略结构名称 (如: Iron Condor, Bull Call Spread)"
                        },
                        "description": {
                            "type": "string",
                            "description": "策略简要描述"
                        },
                        "suitability_score": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "适用性评分 (1-10)"
                        },
                        
                        # ------------------------------------------
                        # 腿部信息
                        # ------------------------------------------
                        "legs": {
                            "type": "array",
                            "description": "策略腿部列表",
                            "items": {
                                "type": "object",
                                "required": ["action", "strike", "rationale"],
                                "properties": {
                                    "action": {
                                        "type": "string",
                                        "enum": ["buy", "sell"],
                                        "description": "买入或卖出"
                                    },
                                    "option_type": {
                                        "type": "string",
                                        "enum": ["call", "put"],
                                        "description": "期权类型"
                                    },
                                    "strike": {
                                        "type": "number",
                                        "description": "行权价"
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "数量"
                                    },
                                    "expiry_dte": {
                                        "type": "integer",
                                        "description": "到期天数"
                                    },
                                    "rationale": {
                                        "type": "string",
                                        "description": "【必填】行权价选择理由，必须解释基于 em1_dollar 的选择逻辑"
                                    }
                                }
                            }
                        },
                        
                        # ------------------------------------------
                        # 执行计划 (增强版)
                        # ------------------------------------------
                        "execution_plan": {
                            "type": "object",
                            "description": "策略执行计划",
                            "required": ["entry_trigger", "holding_period", "exit_plan"],
                            "properties": {
                                "entry_trigger": {
                                    "type": "string",
                                    "description": "入场触发条件，必须使用微结构战术 (GEX-ORB/Wall Rejection/Flip Crossing)"
                                },
                                "entry_timing": {
                                    "type": "string",
                                    "description": "入场时机描述"
                                },
                                "holding_period": {
                                    "type": "string",
                                    "description": "建议持有周期，必须基于 T_scale 计算"
                                },
                                "exit_plan": {
                                    "type": "object",
                                    "description": "出场计划",
                                    "required": ["profit_target", "stop_loss"],
                                    "properties": {
                                        "profit_target": {
                                            "type": "string",
                                            "description": "止盈目标"
                                        },
                                        "stop_loss": {
                                            "type": "string",
                                            "description": "止损位"
                                        },
                                        "time_decay_exit": {
                                            "type": "string",
                                            "description": "时间衰减出场规则"
                                        },
                                        "adjustment": {
                                            "type": "string",
                                            "description": "调仓建议"
                                        }
                                    }
                                }
                            }
                        },
                        
                        # ------------------------------------------
                        # 量化指标
                        # ------------------------------------------
                        "quant_metrics": {
                            "type": "object",
                            "description": "量化指标，引用 Code 3 计算结果",
                            "properties": {
                                "setup_cost": {
                                    "type": "string",
                                    "description": "建仓成本 (Debit 为正, Credit 为负)"
                                },
                                "max_profit": {
                                    "type": "number",
                                    "description": "最大盈利"
                                },
                                "max_loss": {
                                    "type": "number",
                                    "description": "最大亏损"
                                },
                                "rr_ratio": {
                                    "type": "string",
                                    "description": "盈亏比 (如 1:2.3)"
                                },
                                "pw_estimate": {
                                    "type": "string",
                                    "description": "胜率估算 (如 65%)"
                                },
                                "breakeven": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                    "description": "盈亏平衡点列表"
                                },
                                "greeks_exposure": {
                                    "type": "object",
                                    "description": "Greeks 敞口",
                                    "properties": {
                                        "delta": {"type": "string"},
                                        "gamma": {"type": "string"},
                                        "vega": {"type": "string"},
                                        "theta": {"type": "string"}
                                    }
                                }
                            }
                        },
                        
                        # ------------------------------------------
                        # 风险管理
                        # ------------------------------------------
                        "risk_management": {
                            "type": "string",
                            "description": "风险管理说明，必须包含噪音惩罚提示（如有）和最大亏损说明"
                        },
                        
                        # 优劣势
                        "pros": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "策略优势"
                        },
                        "cons": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "策略劣势"
                        }
                    }
                }
            }
        }
    }