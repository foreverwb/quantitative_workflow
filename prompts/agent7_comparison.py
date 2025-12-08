"""
Agent 7: 策略排序 Prompt
基于定量对比结果进行策略排序和推荐
新增：质量过滤（0DTE噪音、量价背离处理）
"""
import json

def get_system_prompt() -> str:
    """系统提示词"""
    return """你是一位期权策略评估专家。

**核心任务**:
综合定量对比、场景概率、策略特征，对所有策略进行排序并给出推荐。

**质量过滤规则 (Quality Filtering)**:
在排序前，你必须先执行以下过滤检查：

1. **0DTE 噪音过滤**:
   - 检查输入中的 `zero_dte_ratio`
   - 若 `zero_dte_ratio > 0.5` (严重噪音)：
     * 所有 DTE < 3 的策略**排名强制下降**（扣除 20 分）
     * 在推荐理由中标注 "⚠️ 0DTE噪音高，短期策略风险大"
   - 若 `zero_dte_ratio > 0.3` (中度噪音)：
     * 短期策略扣除 10 分

2. **量价背离过滤**:
   - 检查输入中的 `is_vetoed` 或 `veto_reason`
   - 若存在量价背离：
     * 所有**方向性策略**（Long Call/Put、Vertical Spread）推荐度**归零**
     * 仅保留**中性策略**（Iron Condor、Butterfly）或**观望**
     * 在推荐理由中**大写标注**: "⛔ 量价背离，方向性策略禁用"

3. **策略偏好强制检查**:
   - 检查 `strategy_bias`
   - 若为 `Credit_Favored`：
     * Debit 策略（Long Call/Put）排名下降 15 分
   - 若为 `Debit_Favored`：
     * Credit 策略（Iron Condor、Credit Spread）排名下降 15 分

**评估维度**:
1. **场景匹配度**: 策略与高概率场景的契合度
2. **风险收益比**: RR Ratio和Kelly准则评分
3. **Greeks健康度**: 敞口是否平衡合理
4. **执行难度**: 流动性、滑点、保证金压力
5. **时间衰减**: Theta影响和时间窗口匹配
6. **波动率敏感度**: Vega敞口与IV环境的适配
7. **质量得分**: validation_flags 的加减分

**排序规则**:
- 综合评分 = 0.25*场景匹配 + 0.20*风险收益 + 0.20*Greeks + 0.15*执行难度 + 0.10*波动率 + 0.10*质量得分
- 必须标注"强烈推荐"、"推荐"、"可选"、"不推荐"等级
- 对每个策略给出清晰的理由
- 若质量过滤触发，在理由中明确说明

**输出结构**:
1. 策略排名列表(按综合得分排序)
2. 每个策略的评分细节和推荐理由
3. 前3名策略的详细对比
4. 风险提示和注意事项
5. 组合建议(如可以同时使用多个策略)
6. 质量过滤摘要（触发了哪些过滤规则）

返回JSON格式。"""


def get_user_prompt(comparison_data: dict, scenario: dict, strategies: dict) -> str:  # ✅ 改为字典
    """用户提示词"""
    
    # 辅助函数：清理 markdown 并解析 JSON
    def _clean_and_parse(data):
        if isinstance(data, str):
            clean_text = data.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            try:
                return json.loads(clean_text.strip())
            except json.JSONDecodeError:
                return {}
        return data if isinstance(data, dict) else {}
    
    # 防御性检查：确保输入是字典
    comparison_data = _clean_and_parse(comparison_data)
    scenario = _clean_and_parse(scenario)
    strategies = _clean_and_parse(strategies)
    
    # 提取 quality_filter（来自 Code 4 输出）
    quality_filter = comparison_data.get("quality_filter", {})
    zero_dte_ratio = quality_filter.get("zero_dte_ratio", 0)
    is_vetoed = quality_filter.get("is_vetoed", False)
    veto_reason = quality_filter.get("veto_reason", "")
    strategy_bias = quality_filter.get("strategy_bias", "Neutral")
    overall_confidence = quality_filter.get("overall_confidence", 1.0)
    filters_triggered = quality_filter.get("filters_triggered", [])
    
    return f"""请基于以下数据对策略进行排序:

        ## 定量对比结果
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

        ## 质量过滤输入
        - 0DTE 比例: {zero_dte_ratio if zero_dte_ratio else "未知"}
        - 是否被否决: {is_vetoed}
        - 否决原因: {veto_reason if veto_reason else "无"}
        - 策略偏好: {strategy_bias}
        - 整体置信度: {overall_confidence}
        - 触发的过滤器: {', '.join(filters_triggered) if filters_triggered else "无"}

        ## 排序要求
        1. **首先执行质量过滤**:
           - 若 is_vetoed = True，方向性策略评分归零
           - 若 0DTE > 50%，DTE<3 策略扣 20 分
           - 若 strategy_bias 与策略类型冲突，扣 15 分

        2. 计算每个策略的综合评分(0-100)
        
        3. 按评分从高到低排序
        
        4. 对每个策略给出:
        - rank: 排名
        - strategy_name: 策略名称
        - overall_score: 综合评分
        - quality_adjustment: 质量调整分数（正/负）
        - rating: 评级(strong_buy/buy/hold/avoid)
        - scenario_match_score: 场景匹配分(0-100)
        - risk_reward_score: 风险收益分(0-100)
        - greeks_health_score: Greeks健康分(0-100)
        - execution_difficulty_score: 执行难度分(0-100)
        - quality_filter_notes: 质量过滤说明（触发了哪些规则）
        - strengths: 主要优势列表
        - weaknesses: 主要劣势列表
        - recommendation_reason: 推荐理由(100字以内)
        - best_for: 最适合的投资者类型/市场环境

        5. 输出top3策略的详细对比表
        
        6. 给出组合建议(如果多个策略可以互补)
        
        7. 标注特殊风险警示（若触发质量过滤）
        
        8. 输出 quality_filter_summary:
           - filters_triggered: 触发的过滤规则列表
           - affected_strategies: 受影响的策略
           - overall_confidence: 整体置信度（考虑噪音后）
        """