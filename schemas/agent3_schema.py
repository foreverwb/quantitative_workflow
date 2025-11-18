"""
Agent 3 JSON Schema - 数据校验输出结构
"""

def get_schema() -> dict:
    """返回 Agent 3 的 JSON Schema"""
    return {
        "type": "object",
        "required": [
            "status",
            "timestamp",
            "validation_summary",
            "targets",
            "indices",
            "missing_fields",
            "next_step",
            "补齐指引",
            "补齐后续"
        ],
        "properties": {
            "status": {
                "type": "string",
                "description": "数据状态",
                "enum": ["data_ready", "missing_data"]
            },
            "timestamp": {
                "type": "string",
                "description": "时间戳,格式 YYYY-MM-DDTHH:mm:ss"
            },
            "validation_summary": {
                "type": "object",
                "required": [
                    "total_targets",
                    "targets_ready",
                    "total_fields_required",
                    "fields_provided",
                    "missing_count",
                    "completion_rate"
                ],
                "properties": {
                    "total_targets": {"type": "integer"},
                    "targets_ready": {"type": "integer"},
                    "total_fields_required": {"type": "integer"},
                    "fields_provided": {"type": "integer"},
                    "missing_count": {"type": "integer"},
                    "completion_rate": {"type": "integer"},
                    "optional_fields_provided": {
                        "type": "integer",
                        "description": "技术面字段提供数量(可选)"
                    },
                    "background_fields_provided": {
                        "type": "integer",
                        "description": "指数背景字段提供数量(可选)"
                    },
                    "warnings": {
                        "type": "array",
                        "description": "警告信息列表(可选)",
                        "items": {"type": "string"}
                    }
                }
            },
            "targets": {
                "type": "object",
                "required": [
                    "symbol",
                    "status",
                    "spot_price",
                    "em1_dollar",
                    "walls",
                    "gamma_metrics",
                    "directional_metrics",
                    "atm_iv"
                ],
                "properties": {
                    "symbol": {"type": "string"},
                    "status": {
                        "enum": ["ready", "missing_data"],
                        "type": "string"
                    },
                    "spot_price": {
                        "description": "现价,若缺失使用 -999",
                        "type": "number"
                    },
                    "em1_dollar": {
                        "description": "预期单日波幅,若缺失使用 -999",
                        "type": "number"
                    },
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
                                "description": "看涨期权墙价位,若缺失使用 -999",
                                "type": "number"
                            },
                            "put_wall": {
                                "description": "看跌期权墙价位,若缺失使用 -999",
                                "type": "number"
                            },
                            "major_wall": {
                                "description": "主要墙价位,若缺失使用 -999",
                                "type": "number"
                            },
                            "major_wall_type": {
                                "description": "主要墙类型,若缺失使用 N/A",
                                "enum": ["call", "put", "N/A"],
                                "type": "string"
                            }
                        }
                    },
                    "gamma_metrics": {
                        "type": "object",
                        "required": [
                            "gap_distance_dollar",
                            "gap_distance_em1_multiple",
                            "cluster_strength_ratio",
                            "net_gex",
                            "net_gex_sign",
                            "vol_trigger",
                            "spot_vs_trigger",
                            "monthly_cluster_override"
                        ],
                        "properties": {
                            "gap_distance_dollar": {
                                "description": "跳墙距离美元值,若缺失使用 -999",
                                "type": "number"
                            },
                            "gap_distance_em1_multiple": {
                                "description": "跳墙距离EM1倍数,若缺失使用 -999",
                                "type": "number"
                            },
                            "cluster_strength_ratio": {
                                "description": "簇强度比,若缺失使用 -999",
                                "type": "number"
                            },
                            "net_gex": {
                                "description": "净Gamma敞口,若缺失使用 -999",
                                "type": "number"
                            },
                            "net_gex_sign": {
                                "description": "净Gamma符号,若缺失使用 N/A",
                                "enum": ["positive_gamma", "negative_gamma", "neutral", "N/A"],
                                "type": "string"
                            },
                            "vol_trigger": {
                                "description": "波动率触发价位,若缺失使用 -999",
                                "type": "number"
                            },
                            "spot_vs_trigger": {
                                "description": "现价相对触发线位置,若缺失使用 N/A",
                                "enum": ["above", "below", "near", "N/A"],
                                "type": "string"
                            },
                            "monthly_cluster_override": {
                                "description": "是否月度簇占优",
                                "enum": ["true", "false"],
                                "type": "string"
                            }
                        }
                    },
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
                                "description": "DEX方向一致性百分比,若缺失使用 -999",
                                "type": "number"
                            },
                            "vanna_dir": {
                                "description": "Vanna方向,若缺失使用 N/A",
                                "enum": ["up", "down", "flat", "N/A"],
                                "type": "string"
                            },
                            "vanna_confidence": {
                                "description": "Vanna置信度,若缺失使用 N/A",
                                "enum": ["high", "medium", "low", "N/A"],
                                "type": "string"
                            },
                            "iv_path": {
                                "description": "隐含波动率路径",
                                "enum": ["升", "降", "平", "数据不足"],
                                "type": "string"
                            },
                            "iv_path_confidence": {
                                "description": "IV路径置信度",
                                "enum": ["high", "medium", "low"],
                                "type": "string"
                            }
                        }
                    },
                    "atm_iv": {
                        "type": "object",
                        "required": ["iv_7d", "iv_14d", "iv_source"],
                        "properties": {
                            "iv_7d": {
                                "description": "7日ATM隐含波动率,若缺失使用 -999",
                                "type": "number"
                            },
                            "iv_14d": {
                                "description": "14日ATM隐含波动率,若缺失使用 -999",
                                "type": "number"
                            },
                            "iv_source": {
                                "description": "IV数据源",
                                "enum": ["7d", "14d", "21d_fallback", "N/A"],
                                "type": "string"
                            }
                        }
                    }
                }
            },
            "indices": {
                "type": "object",
                "required": ["spx", "qqq"],
                "properties": {
                    "spx": {
                        "type": "object",
                        "required": ["net_gex_idx", "em1_dollar_idx", "spot_idx"],
                        "properties": {
                            "net_gex_idx": {
                                "description": "SPX的NET-GEX,若缺失使用 -999",
                                "type": "number"
                            },
                            "em1_dollar_idx": {
                                "description": "SPX的EM1$,若缺失使用 -999",
                                "type": "number"
                            },
                            "spot_idx": {
                                "description": "SPX现价,若缺失使用 -999",
                                "type": "number"
                            }
                        }
                    },
                    "qqq": {
                        "type": "object",
                        "required": ["net_gex_idx", "em1_dollar_idx", "spot_idx"],
                        "properties": {
                            "net_gex_idx": {
                                "description": "QQQ净Gamma,若不需要使用 -999",
                                "type": "number"
                            },
                            "em1_dollar_idx": {
                                "description": "QQQ的EM1$,若不需要使用 -999",
                                "type": "number"
                            },
                            "spot_idx": {
                                "description": "QQQ现价,若不需要使用 -999",
                                "type": "number"
                            }
                        }
                    }
                }
            },
            "missing_fields": {
                "type": "array",
                "description": "缺失字段列表,若无缺失则为空数组",
                "items": {
                    "type": "object",
                    "required": ["field", "target", "severity", "category"],
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
            },
            "next_step": {
                "type": "string",
                "enum": ["proceed_to_analysis", "request_missing_data"]
            },
            "补齐指引": {
                "type": "array",
                "description": "补齐指引列表,当status=data_ready时为空数组",
                "items": {
                    "type": "object",
                    "required": [
                        "missing_field",
                        "description",
                        "command",
                        "alternative",
                        "extraction_note",
                        "priority",
                        "impact"
                    ],
                    "properties": {
                        "missing_field": {
                            "description": "缺失字段名",
                            "type": "string"
                        },
                        "description": {
                            "description": "字段说明",
                            "type": "string"
                        },
                        "command": {
                            "description": "建议执行的命令",
                            "type": "string"
                        },
                        "alternative": {
                            "description": "备选方案,若无则填 N/A",
                            "type": "string"
                        },
                        "extraction_note": {
                            "description": "数据提取说明",
                            "type": "string"
                        },
                        "priority": {
                            "description": "优先级1-5",
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "impact": {
                            "description": "缺失影响说明",
                            "type": "string"
                        }
                    }
                }
            },
            "补齐后续": {
                "description": "补齐后的后续步骤,当status=data_ready时填 N/A",
                "type": "string"
            },
            "technical_analysis": {
                "description": "技术面数据(可选)",
                "type": "object",
                "properties": {
                    "ta_score": {
                        "description": "技术面评分(0-2分)",
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 2
                    },
                    "ta_commentary": {
                        "description": "技术面评分理由",
                        "type": "string"
                    }
                    # 其他技术指标字段...
                }
            }
        }
    }