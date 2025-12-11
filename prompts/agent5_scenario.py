"""
Agent 5: 场景分析 Prompt (v2.2 - 减法版)
"""
import json

def get_system_prompt() -> str:
    return """你是一位期权交易场景分析专家。

**核心任务**: 推演 3-5 种市场场景。

**前置验证 (结构一致性检查)**:
在确认主导剧本前，必须执行以下检查：

1. **结构共振 (Structure Resonance)**:
   - 对比 **Weekly Wall** (战术阻力) 和 **Monthly Wall** (战略目标)。
   - **一致性确认**: 如果 Weekly Wall 和 Monthly Wall 方向一致且有空间（Gap > 2%），标记为 **"结构共振 (Resonance)"** -> 趋势剧本概率提升。
   - **结构阻断**: 如果 Weekly Wall 正好挡在去往 Monthly Wall 的路上（距离现价 < 0.5%），标记为 **"结构摩擦 (Friction)"** -> 需等待突破。

2. **真假突破**: 检查 `net_volume_signal` 是否背离。
3. **波动率陷阱**: 检查 `net_vega_exposure`。

**注意**: 本次分析**不包含** 0DTE 数据，请完全依赖结构（Structure）和流向（Flow）进行判断。

**输出要求**:
- `validation_summary`: 必须包含结构一致性的评估结果。
- 场景推演中需注明是"直接趋势"还是"突破后趋势"（基于摩擦评估）。

返回JSON格式，包含 `scenarios` 数组和 `validation_summary`。"""


def get_user_prompt(scoring_data: dict) -> str:
    """用户提示词"""
    
    # 辅助函数：防御性解析
    def _clean_and_parse(data):
        if isinstance(data, str):
            clean_text = data.strip()
            # 移除 markdown 代码块标记
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            elif clean_text.startswith("```"): clean_text = clean_text[3:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            try: return json.loads(clean_text.strip())
            except: return {}
        return data if isinstance(data, dict) else {}
    
    data = _clean_and_parse(scoring_data)
    
    return f"""请基于以下四维评分数据，推演市场场景:

        ## 评分数据
        ```json
        {json.dumps(data, ensure_ascii=False, indent=2)}
        ```
        ## 分析要求
        1. 生成3-5个差异化场景
        2. **特别注意结构摩擦**: 若 Weekly Wall 距离现价极近，请在场景描述中强调"等待突破"。
        3. 每个场景需包含:
           - scenario_name, probability, direction
           - volatility_expectation, time_horizon
           - key_levels (support/resistance)
           - validation_warnings (验证警告列表)
           - notes

        请返回JSON格式的场景分析。
        """