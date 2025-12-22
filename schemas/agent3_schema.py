"""
Agent 3 JSON Schema - v3（符合新 RuntimeLabel 规范）

变更:
1. 添加 abs_gex_peaks 数组结构
2. 更新 validation_metrics 结构
"""

def get_schema() -> dict:
    """返回 Agent 3 的 JSON Schema"""
    return {
        "type": "object",
        "required": ["targets", "indices"],
        "properties": {
            # ============================================
            # 2. 标的数据
            # ============================================
            "targets": {
                "type": "object",
                "required": [
                    "symbol",
                    "spot_price",
                    "walls",
                    "gamma_metrics",
                    "directional_metrics",
                    "atm_iv",
                    "validation_metrics"
                ],
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码"
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
                            "major_wall"
                        ],
                        "properties": {
                            "call_wall": {"type": "number"},
                            "put_wall": {"type": "number"},
                            "major_wall": {"type": "number"}
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
                            "gap_distance_dollar"
                        ],
                        "properties": {
                            "vol_trigger": {"type": "number"},
                            "spot_vs_trigger": {
                                "type": "string",
                                "enum": ["above", "below", "near", "N/A"]
                            },
                            "net_gex": {
                                "type": "string",
                                "enum": ["positive_gamma", "negative_gamma"]
                            },
                            
                            "gap_distance_dollar": {"type": "number"},
                        },
                        "additionalProperties": False
                    },
                    
                    # ------------------------
                    # 2.3 方向指标
                    # ------------------------
                    "directional_metrics": {
                        "type": "object",
                        "required": [
                            "dex_bias",
                            "dex_bias_strength",
                            "vanna_dir",
                            "vanna_confidence",
                            "iv_path",
                            "iv_path_confidence"
                        ],
                        "properties": {
                            "dex_bias": {
                                "type": "string",
                                "enum": ["support", "mixed", "oppose"],
                                "description": "DEX方向偏好：support=支持当前趋势, mixed=混合信号, oppose=反向信号"
                            },
                            "dex_bias_strength": {
                                "type": "string",
                                "enum": ["strong", "mid", "weak"],
                                "description": "DEX信号强度"
                            },
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
                                "enum": ["high", "medium", "low", "N/A"]
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
                            "iv_7d": {"type": "number"},
                            "iv_14d": {"type": "number"},
                            "iv_source": {
                                "type": "string",
                                "enum": ["7d", "14d", "21d_fallback", "N/A"]
                            }
                        },
                        "additionalProperties": False
                    },
                    
                    # ------------------------
                    # 2.5 验证指标
                    # ------------------------
                    "validation_metrics": {
                        "type": "object",
                        "description": "验证型数据",
                        "required": [
                            "net_volume_signal",
                            "net_vega_exposure"
                        ],
                        "properties": {
                            "net_volume_signal": {
                                "type": ["string", "null"],
                                "enum": ["Bullish_Call_Buy", "Bearish_Put_Buy", "Neutral", "Divergence", None],
                                "description": "净成交量方向，来自 !volumen 命令"
                            },
                            "net_vega_exposure": {
                                "type": ["string", "null"],
                                "enum": ["Long_Vega", "Short_Vega", "Unknown", None],
                                "description": "Dealer Vega 敞口，来自 !vexn 命令"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            },
            
            # ============================================
            # 3. 指数数据
            # ============================================
            "indices": {
                "type": "object",
                "description": "指数背景数据",
                "required": [],
                "properties": {},
                "patternProperties": {
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
                                "enum": ["positive_gamma", "negative_gamma"]
                            },
                            "spot_price_idx": {"type": "number"},
                            "iv_7d": {"type": "number"},
                            "iv_14d": {"type": "number"}
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }