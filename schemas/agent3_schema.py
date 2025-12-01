"""
Agent 3 JSON Schema - 修复版（符合 Vision Structured Output 规范）

修复要点：
1. 确保 required 和 properties 的键完全一致
2. 使用 patternProperties 支持动态指数
3. 移除 additionalProperties（Strict Mode 自动禁止）
"""

def get_schema() -> dict:
    """返回 Agent 3 的 JSON Schema（Vision Strict Mode 兼容版）"""
    return {
        "type": "object",
        "required": ["timestamp", "targets", "indices"],  # ✅ 与 properties 键一致
        "properties": {
            # ============================================
            # 1. 时间戳（必需）
            # ============================================
            "timestamp": {
                "type": "string",
                "description": "数据提取时间戳（ISO 8601 格式）"
            },
            
            # ============================================
            # 2. 标的数据（必需）
            # ============================================
            "targets": {
                "type": "object",
                "required": [
                    "symbol",
                    "spot_price",
                    "walls",
                    "gamma_metrics",
                    "directional_metrics",
                    "atm_iv"
                ],
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码（如 NVDA）"
                    },
                    
                    "spot_price": {
                        "type": "number",
                        "description": "现价"
                    },
                    
                    # ------------------------
                    # 2.1 墙位数据
                    # ------------------------
                    "walls": {
                        "type": "object",
                        "required": [
                            "call_wall",
                            "put_wall",
                            "major_wall",
                            "major_wall_type"
                        ],
                        "properties": {
                            "call_wall": {
                                "type": "number",
                                "description": "Call 墙位价格"
                            },
                            "put_wall": {
                                "type": "number",
                                "description": "Put 墙位价格"
                            },
                            "major_wall": {
                                "type": "number",
                                "description": "主墙位价格"
                            },
                            "major_wall_type": {
                                "type": "string",
                                "enum": ["call", "put", "N/A"],
                                "description": "主墙类型"
                            }
                        },
                        "additionalProperties": False
                    },
                    
                    # ------------------------
                    # 2.2 Gamma 指标
                    # ------------------------
                    "gamma_metrics": {
                        "type": "object",
                        "required": [
                            "vol_trigger",
                            "spot_vs_trigger",
                            "net_gex",
                            "nearby_peak",
                            "next_cluster_peak",
                            "gap_distance_dollar",
                            "monthly_data",
                            "weekly_data"
                        ],
                        "properties": {
                            "vol_trigger": {
                                "type": "number",
                                "description": "VOL_TRIGGER / Gamma Flip 价格"
                            },
                            "spot_vs_trigger": {
                                "type": "string",
                                "enum": ["above", "below", "near", "N/A"],
                                "description": "现价相对 Trigger 的位置"
                            },
                            "net_gex": {
                                "type": "string",
                                "enum": ["positive_gamma", "negative_gamma"],
                                "description": "净 Gamma 方向"
                            },
                            
                            # 近旁峰高
                            "nearby_peak": {
                                "type": "object",
                                "required": ["price", "abs_gex"],
                                "properties": {
                                    "price": {
                                        "type": "number",
                                        "description": "峰值价格"
                                    },
                                    "abs_gex": {
                                        "type": "number",
                                        "description": "绝对 GEX 值"
                                    }
                                },
                                "additionalProperties": False
                            },
                            
                            # 下一簇峰高
                            "next_cluster_peak": {
                                "type": "object",
                                "required": ["price", "abs_gex"],
                                "properties": {
                                    "price": {
                                        "type": "number",
                                        "description": "簇峰价格"
                                    },
                                    "abs_gex": {
                                        "type": "number",
                                        "description": "簇峰 GEX 值"
                                    }
                                },
                                "additionalProperties": False
                            },
                            
                            "gap_distance_dollar": {
                                "type": "number",
                                "description": "到主墙的美元距离"
                            },
                            
                            # 月度数据
                            "monthly_data": {
                                "type": "object",
                                "required": ["cluster_strength"],
                                "properties": {
                                    "cluster_strength": {
                                        "type": "object",
                                        "required": ["price", "abs_gex"],
                                        "properties": {
                                            "price": {"type": "number"},
                                            "abs_gex": {"type": "number"}
                                        },
                                        "additionalProperties": False
                                    }
                                },
                                "additionalProperties": False
                            },
                            
                            # 周度数据
                            "weekly_data": {
                                "type": "object",
                                "required": ["cluster_strength"],
                                "properties": {
                                    "cluster_strength": {
                                        "type": "object",
                                        "required": ["price", "abs_gex"],
                                        "properties": {
                                            "price": {"type": "number"},
                                            "abs_gex": {"type": "number"}
                                        },
                                        "additionalProperties": False
                                    }
                                },
                                "additionalProperties": False
                            }
                        },
                        "additionalProperties": False
                    },
                    
                    # ------------------------
                    # 2.3 方向指标
                    # ------------------------
                    "directional_metrics": {
                        "type": "object",
                        "required": [
                            "dex_same_dir_pct",
                            "vanna_dir",
                            "vanna_confidence",
                            "iv_path",
                            "iv_path_confidence"
                        ],
                        "properties": {
                            "dex_same_dir_pct": {
                                "type": "number",
                                "description": "DEX 同向百分比（0.0-1.0）"
                            },
                            "vanna_dir": {
                                "type": "string",
                                "enum": ["up", "down", "flat", "N/A"],
                                "description": "Vanna 方向"
                            },
                            "vanna_confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low", "N/A"],
                                "description": "Vanna 置信度"
                            },
                            "iv_path": {
                                "type": "string",
                                "enum": ["升", "降", "平", "数据不足"],
                                "description": "IV 路径趋势"
                            },
                            "iv_path_confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low", "N/A"],
                                "description": "IV 路径置信度"
                            }
                        },
                        "additionalProperties": False
                    },
                    
                    # ------------------------
                    # 2.4 ATM IV
                    # ------------------------
                    "atm_iv": {
                        "type": "object",
                        "required": ["iv_7d", "iv_14d", "iv_source"],
                        "properties": {
                            "iv_7d": {
                                "type": "number",
                                "description": "7 日 ATM IV"
                            },
                            "iv_14d": {
                                "type": "number",
                                "description": "14 日 ATM IV"
                            },
                            "iv_source": {
                                "type": "string",
                                "enum": ["7d", "14d", "21d_fallback", "N/A"],
                                "description": "IV 数据来源"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            },
            "indices": {
                "type": "object",
                "description": "指数背景数据（仅包含实际上传的指数）",
                "required": [],  # ✅ 空数组，因为指数是动态的
                "properties": {},  # ✅ 空对象，使用 patternProperties
                "patternProperties": {
                    # 匹配任意 2-5 个大写字母的指数代码
                    "^[A-Z]{2,5}$": {
                        "type": "object",
                        "required": [
                            "net_gex_idx",
                            "spot_price_idx",
                            "iv_7d",
                            "iv_14d"
                        ],
                        "properties": {
                            "net_gex_idx": {
                                "type": "string",
                                "enum": ["positive_gamma", "negative_gamma"],
                                "description": "指数净 Gamma 方向"
                            },
                            "spot_price_idx": {
                                "type": "number",
                                "description": "指数现价"
                            },
                            "iv_7d": {
                                "type": "number",
                                "description": "指数 7 日 ATM IV"
                            },
                            "iv_14d": {
                                "type": "number",
                                "description": "指数 14 日 ATM IV"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False  # ✅ 禁止非指数代码的键
            }
        },
        "additionalProperties": False
    }