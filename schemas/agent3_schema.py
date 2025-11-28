"""
Agent 3 JSON Schema - 仅包含原始提取字段（24个）
计算字段由 Calculator 节点添加，不出现在 Schema 中
"""

def get_schema() -> dict:
    """返回 Agent 3 的 JSON Schema（精简版）"""
    return {
  "type": "object",
  "required": ["targets", "indices"],
  "properties": {

    "timestamp": { "type": "string" },

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
        "symbol": {"type": "string"},

        "spot_price": {"type": "number"},

        "walls": {
          "type": "object",
          "required": [
            "call_wall", "put_wall",
            "major_wall", "major_wall_type"
          ],
          "properties": {
            "call_wall": {"type": "number"},
            "put_wall": {"type": "number"},
            "major_wall": {"type": "number"},
            "major_wall_type": {
              "type": "string",
              "enum": ["call", "put", "N/A"]
            }
          }
        },

        "gamma_metrics": {
          "type": "object",
          "required": [
            "vol_trigger",
            "spot_vs_trigger",
            "net_gex",
            "net_gex_sign",
            "nearby_peak",
            "next_cluster_peak",
            "gap_distance_dollar",
            "monthly_data",
            "weekly_data",
          ],
          "properties": {
            "vol_trigger": {"type": "number"},
            "spot_vs_trigger": {
              "type": "string",
              "enum": ["above", "below", "near", "N/A"]
            },
            "net_gex": {"type": "number"},
            "net_gex_sign": {
              "type": "string",
              "enum": ["positive_gamma", "negative_gamma", "neutral", "N/A"]
            },

            "nearby_peak": {
              "type": "object",
              "required": ["price", "abs_gex"],
              "properties": {
                "price": {"type": "number"},
                "abs_gex": {"type": "number"}
              }
            },

            "next_cluster_peak": {
              "type": "object",
              "required": ["price", "abs_gex"],
              "properties": {
                "price": {"type": "number"},
                "abs_gex": {"type": "number"}
              }
            },

            "gap_distance_dollar": {"type": "number"},

            "monthly_data": {
              "type": "object",
              "properties": {
                "cluster_strength": {
                  "type": "object",
                  "properties": {
                    "price": {"type": "number"},
                    "abs_gex": {"type": "number"}
                  }
                }
              }
            },
            "weekly_data": {
              "type": "object",
              "properties": {
                "cluster_strength": {
                  "type": "object",
                  "properties": {
                    "price": {"type": "number"},
                    "abs_gex": {"type": "number"}
                  }
                }
              }
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
              "enum": ["high", "medium", "low", "N/A"]
            }
          }
        },

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
          "properties": {
            "net_gex_idx": {"type": "number"},
            "spot_idx": {"type": "number"},
            "atm_iv_idx": {"type": "number"}
          }
        },
        "qqq": {
          "type": "object",
          "properties": {
            "net_gex_idx": {"type": "number"},
            "spot_idx": {"type": "number"},
            "atm_iv_idx": {"type": "number"}
          }
        }
      }
    },
  }
}
