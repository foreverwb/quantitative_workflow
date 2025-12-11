"""
Agent 7: 策略排序 Prompt (v2.0)
基于定量对比结果进行策略排序和推荐
新增：质量过滤（0DTE噪音、量价背离处理）
"""
import json

def get_system_prompt() -> str:
    """系统提示词"""
    return """你是一位期权策略评估专家。

**核心任务**:
综合定量对比、场景概率、策略特征，对所有策略进行排序并给出推荐。

**质量过滤规则 (Quality Filtering) - 必须优先执行**:
在排序前，检查输入中的 `quality_filter` 数据：

1. **0DTE 噪音过滤**:
   - 若触发了 `0DTE_HIGH` 或 `0DTE_MID` 过滤器：
     * 所有 DTE < 3 的策略**排名强制下降**。
     * 在推荐理由中标注 "⚠️ 0DTE噪音高，短期策略风险大"。

2. **量价背离过滤**:
   - 若触发了 `VOLUME_DIVERGENCE`：
     * 所有**方向性策略**（Long Call/Put、Vertical Spread）推荐度**归零**。
     * 仅保留**中性策略**（Iron Condor、Butterfly）或**观望**。
     * 在推荐理由中**大写标注**: "⛔ 量价背离，方向性策略禁用"。

3. **策略偏好强制检查**:
   - 检查 `strategy_bias`。
   - 若为 `Credit_Favored`，Credit 策略加分；若为 `Debit_Favored`，Debit 策略加分。

**评分维度**:
- 综合评分 = 0.25*场景匹配 + 0.20*风险收益 + 0.20*Greeks + 0.15*执行难度 + 0.10*波动率 + 0.10*质量得分

**输出结构**:
1. 策略排名列表 (按综合得分)
2. 每个策略的评分细节和推荐理由
3. 质量过滤摘要（触发了哪些规则）

返回JSON格式。"""


def get_user_prompt(comparison_data: dict, scenario: dict, strategies: dict) -> str:
    """用户提示词"""
    
    def _clean_and_parse(data):
        if isinstance(data, str):
            clean_text = data.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:]
            elif clean_text.startswith("```"): clean_text = clean_text[3:]
            if clean_text.endswith("```"): clean_text = clean_text[:-3]
            try: return json.loads(clean_text.strip())
            except: return {}
        return data if isinstance(data, dict) else {}
    
    comparison_data = _clean_and_parse(comparison_data)
    scenario = _clean_and_parse(scenario)
    strategies = _clean_and_parse(strategies)
    
    # 提取 quality_filter (来自 Code 4)
    qf = comparison_data.get("quality_filter", {})
    
    return f"""请基于以下数据对策略进行排序:

        ## 定量对比结果 (含质量过滤)
        ```json
        {json.dumps(comparison_data, ensure_ascii=False, indent=2)}
        ```

        ## 场景分析
        ```json
        {json.dumps(scenario, ensure_ascii=False, indent=2)}
        ```

        ## 策略清单
        ```json
        {json.dumps(strategies, ensure_ascii=False, indent=2)}
        ```

        ## 质量过滤状态
        - 触发过滤器: {qf.get('filters_triggered', [])}
        - 整体置信度: {qf.get('overall_confidence', 1.0)}
        - 策略偏好: {qf.get('strategy_bias', 'Neutral')}

        ## 任务
        1. 执行质量过滤逻辑。
        2. 计算综合评分。
        3. 输出 Top 3 推荐。
        """