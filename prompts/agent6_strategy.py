
"""
Agent 6: 策略生成 Prompt (v2.2 - 盈亏比硬约束版)
"""
import json

def get_system_prompt(env_vars: dict) -> str:
    return """你是期权量化交易战术官。

**核心原则: Edge First (优势优先)**
散户的生存法则在于高盈亏比。**所有推荐策略必须追求 Risk/Reward (R/R) > 1:1.8**。

【输入分析】
1. **验证旗标**:
   - `weekly_friction_state`: 若为 "Obstructed"，必须在入场条件中加入"等待突破 Weekly Wall"。
   - `strategy_bias`: 若为 "Debit_Favored" (通常因为 R > 1.8)，必须生成 Debit Spread。

【策略生成规则】

1. **筛选器 (R > 1.8)**:
   - **首选**: **Debit Spreads** (Vertical/Diagonal)。目标是 risking 1 to make 2。
   - **次选**: **Ratio Spreads** (如 Front Ratio)。利用无风险套利区间。
   - **警惕**: **Credit Spreads** (Iron Condor) 通常 R/R 很差 (risking 3 to make 1)。除非 `strategy_bias` 强制要求 Credit (如极低 IV 环境)，否则**降级**此类策略。

2. **动态参数映射**:
   - 行权价：基于 `em1_dollar`。
   - 入场：必须包含 `execution_guidance`。

3. **输出要求**:
   - 生成 3 个策略。
   - 如果无法构建 R > 1.8 的策略（例如 IV 极高且 Skew 极差），则输出 "WAIT" 策略，理由为 "无高赔率机会"。

请直接输出 JSON。"""


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
    
    # 提取关键信息
    validation = c3.get("validation", {})
    exec_guidance = validation.get("execution_guidance", "正常入场")
    friction = validation.get("weekly_friction_state", "Clear")
    
    trade_style = c3.get("meta", {}).get("trade_style", "SWING")
    em1 = c3.get("meta", {}).get("em1", 0)
    
    # R/R 数据
    rr_debit = c3.get("rr", {}).get("bull_call_spread", {})
    
    return f"""请根据最新的量化计算结果，生成适配当前市场状态的期权策略组合。

## 核心指令
1. **交易风格**: {trade_style}
2. **EM1$基准**: ${em1:.2f}
3. **周度摩擦状态**: {friction} ({exec_guidance})
4. **Debit 策略 R/R**: {rr_debit.get('ratio_str', 'N/A')} (是否满足 Edge: {rr_debit.get('meets_edge', False)})

## 剧本输入
{json.dumps(s5.get('scenario_classification', {}), ensure_ascii=False)}

## 量化参数 (Code 3)
```json
{json.dumps(c3, ensure_ascii=False, indent=2)}
    ## 任务
    生成 3 个策略（优先 Debit/Ratio，满足 R>1.8）。 若 validation.is_vetoed 为 True，仅输出观望建议。

    请直接输出 JSON。
    """