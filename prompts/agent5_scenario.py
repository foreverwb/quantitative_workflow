"""
Agent 5: 场景分析 Prompt
基于四维评分生成多种市场场景
新增：0DTE 择时逻辑修正（不降权，只预警）
"""
import json

def get_system_prompt() -> str:
    """系统提示词"""
    return """你是一位期权交易场景分析专家。

**核心任务**:
基于四维评分(Gamma Regime、Break Wall、Direction、IV)，推演3-5种可能的市场场景。

**前置验证与风险标记（关键修改）**:
在确认主导剧本之前，必须检查 `validation_metrics`：

1. **0DTE 拥挤度评估 (Crowding Check)**:
   - 检查 `zero_dte_ratio` (0DTE GEX 占比)
   - 若 > 0.4：标记为 **"日内Gamma钉住 (Gamma Pinning)"** 或 **"短期情绪主导"**。
   - **关键指令**：**严禁**仅仅因为 0DTE 占比高而降低主导剧本（如趋势/区间）的发生概率（Probability）。Swing 交易关注多日结构，0DTE 只是日内的噪音。
   - **必须**在输出的 `validation_warnings` 中明确注明："0DTE占比较高，日内价格可能受阻，需优化入场择时 (避免追单/等待尾盘)"。

2. **真假突破检测**:
   - 如果价格突破了 GEX 墙，检查 `net_volume_signal`。
   - 若方向相反（如突破 Call Wall 但量能看跌），标记为 **"假突破风险 (Bull/Bear Trap)"**。

3. **波动率陷阱检测**:
   - 如果 IV 升但 Dealer Short Vega，标记为 **"波动率受压 (Vol Suppression)"**，IV 扩张剧本概率下调。

**输出要求**:
1. **场景定义**: 明确价格方向、波动率变化、时间维度。
2. **概率评估**: 总和接近 100%。
3. **关键价位**: 引用 Monthly Wall 作为最终目标，Weekly Wall 作为首要阻力。
4. **验证标记**: 将上述风险写入 `validation_warnings`。

**场景类型示例**:
- 趋势突破(概率60%): 价格站稳 Weekly Wall，目标指向 Monthly Wall。
- 区间震荡(概率30%): 受困于 0DTE 拥挤区，日内波幅收窄。

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
        2. **特别注意 0DTE 数据**: 若 `zero_dte_ratio` 较高，请在场景描述中强调"日内择时风险"，但不要轻易否定趋势剧本。
        3. 每个场景需包含:
           - scenario_name, probability, direction
           - volatility_expectation, time_horizon
           - key_levels (support/resistance)
           - validation_warnings (验证警告列表)
           - notes

        请返回JSON格式的场景分析。
        """