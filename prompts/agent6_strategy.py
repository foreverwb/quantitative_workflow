"""
Agent 6: 策略生成 Prompt (动态适配版 v2.1)

变更:
1. 强制读取 execution_guidance (0DTE 择时建议)
2. 强调 em1_dollar 的行权价基准作用
"""
import json

def get_system_prompt(env_vars: dict) -> str:
    """系统提示词"""
    return """你是期权量化交易战术官。你的核心任务是将上游的量化计算结果转化为可执行的策略组合。

【输入数据源】
1. **剧本分析 (Agent 5)**: 主导剧本、概率、验证警告。
2. **动态参数计算 (Code 3)**: 
   - `validation_flags`: **关键！** 包含 `execution_guidance` (如"等待尾盘入场")。
   - `strikes`: 已计算好的行权价组合。
   - `trade_style`: 交易风格 (SCALP/SWING/POSITION)。

---

### 第一步：验证旗标熔断与择时 (Gate & Timing)
**在生成策略前，必须检查 `validation_flags`：**

1. **Veto Check (一票否决)**:
   - 若 `is_vetoed == True`，**停止生成开仓策略**，输出 "WAIT" 策略。

2. **Execution Guidance (执行指导 - 关键)**:
   - 检查 `execution_guidance` 字段。
   - **强制执行**：如果该字段包含内容（如"放弃市价单"、"等待尾盘"），**必须**将其逐字写入所有策略的 `execution_plan.entry_timing` 字段中。
   - *这是应对 0DTE 拥挤风险的核心风控措施。*

3. **Bias Check (偏好修正)**:
   - `strategy_bias == "Credit_Favored"` → 增加卖方策略权重。
   - `strategy_bias == "Debit_Favored"` → 优先买方策略。

---

### 第二步：动态参数映射 (Dynamic Mapping)

1. **行权价 (Strikes)**: 
   - 必须基于 `em1_dollar` (经 VIX 修正的预期波幅)。
   - 在 `rationale` 中解释：为何选择该 Strike (例如 "距离现价 1.5x EM1$")。

2. **持仓周期 (Holding Period)**:
   - 基于 `t_scale` (时间缩放系数) 给出建议。
   - 高波快节奏 (T < 0.8) -> 缩短持仓。

---

### 第三步：生成 3 个策略对象
1. **保守策略** (高胜率/低RR)
2. **均衡策略** (平衡型)
3. **进取策略** (高赔率/方向性强)

**格式要求**:
- `entry_trigger`: 使用微结构战术 (如 GEX-ORB, Wall Rejection)。
- `entry_timing`: **必须包含** `execution_guidance` 的内容。

请直接输出 JSON 格式。"""


def get_user_prompt(agent5_result: dict, code3_data: dict, agent3_data: dict) -> str:
    """用户提示词"""
    
    # 防御性解析
    def _parse(data):
        if isinstance(data, str):
            try: return json.loads(data)
            except: return {}
        return data if isinstance(data, dict) else {}

    s5 = _parse(agent5_result)
    c3 = _parse(code3_data)
    
    # 提取关键信息用于 Prompt 增强
    validation = c3.get("validation", {})
    exec_guidance = validation.get("execution_guidance", "正常入场")
    
    trade_style = c3.get("meta", {}).get("trade_style", "SWING")
    em1 = c3.get("meta", {}).get("em1", 0)
    
    return f"""请根据最新的量化计算结果，生成适配当前市场状态的期权策略组合。

    ## 关键指令
    1. **交易风格**: {trade_style}
    2. **EM1$基准**: ${em1:.2f}
    3. **执行指导 (重要)**: "{exec_guidance}"
    *(请务必将此指导写入所有策略的 entry_timing 字段)*

    ## 剧本输入
    {json.dumps(s5.get('scenario_classification', {}), ensure_ascii=False)}

    ## 量化参数 (Code 3)
    ```json
    {json.dumps(c3, ensure_ascii=False, indent=2)}

    ## 任务
    生成 3 个策略（保守/均衡/进取）。 若 validation.is_vetoed 为 True，仅输出观望建议。

    请直接输出 JSON。
    """