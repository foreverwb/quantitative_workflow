"""
Agent 6: 策略生成 Schema (v3.6 - Flow-Aware)
变更:
1. 新增 setup_quality 和 flow_aligned 字段，供 Code 4 评分使用
"""

def get_schema() -> dict:
    """获取 Agent 6 输出 Schema"""
    return {
        "type": "object",
        "required": ["strategies"],
        "properties": {
            "meta_info": {
                "type": "object",
                "properties": {
                    "trade_style": {"type": "string"},
                    "t_scale": {"type": "number"},
                    "lambda_factor": {"type": "number"}
                }
            },
            "validation_flags": {
                "type": "object",
                "properties": {
                    "is_vetoed": {"type": "boolean"},
                    "veto_reason": {"type": "string"},
                    "strategy_bias": {"type": "string"}
                }
            },
            "strategies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "name", 
                        "structure_type",
                        "thesis", 
                        "legs",
                        "delta_profile",
                        "setup_quality" # [新增] 必填
                    ],
                    "properties": {
                        "name": {"type": "string"}, 
                        "strategy_name": {"type": "string"}, 
                        "source_blueprint": {"type": "string"},
                        "structure_type": {"type": "string"},
                        
                        "thesis": {
                            "type": "string", 
                            "description": "策略的核心逻辑 (Thesis)"
                        },
                        "description": {"type": "string"},
                        
                        "delta_profile": {"type": "string"},
                        "delta_rationale": {"type": "string"},
                        
                        # [新增] 质量评估字段
                        "setup_quality": {
                            "type": "string",
                            "enum": ["High", "Medium", "Low"],
                            "description": "基于 Flow 和 结构的综合质量评估"
                        },
                        "flow_aligned": {
                            "type": "boolean",
                            "description": "策略方向是否与资金流向一致"
                        },
                        
                        "legs": {
                            "anyOf": [
                                {"type": "object"},
                                {"type": "array"}
                            ]
                        },
                        
                        "execution_plan": {"type": "object"},
                        "quant_metrics": {"type": "object"}
                    }
                }
            }
        },
        "additionalProperties": False
    }