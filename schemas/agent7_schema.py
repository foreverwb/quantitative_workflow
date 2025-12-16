"""
Agent 7: 策略排序 Schema
"""

def get_schema() -> dict:
    return {
        "type": "object",
        "required": ["symbol", "ranking", "quality_filter_summary"],
        "properties": {
            "symbol": {"type": "string"},
            "ranking": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["rank", "strategy_name", "overall_score"],
                    "properties": {
                        "rank": {"type": "integer"},
                        "strategy_name": {"type": "string"},
                        "overall_score": {"type": "number"},
                        "quality_adjustment": {"type": "number"},
                        "quality_filter_notes": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "rating": {"type": "string"},
                        "metrics": {"type": "object"},
                        "recommendation_reason": {"type": "string"}
                    }
                }
            },
            "quality_filter_summary": {
                "type": "object",
                "properties": {
                    "filters_triggered": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "is_vetoed": {"type": "boolean"},
                    "strategy_bias": {"type": "string"}
                }
            }
        }
    }