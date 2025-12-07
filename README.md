### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行命令

**标准方式**：
```bash
python app.py analyze AAPL --mode full
```

**简化命令**（配置 alias）：
```bash
# 进入项目目录，配置别名
cd ~/quantitative_workflow  
echo "alias quick='python $(pwd)/app.py quick'" >> ~/.zshrc
echo "alias analyze='python $(pwd)/app.py analyze'" >> ~/.zshrc
echo "alias update='python $(pwd)/app.py update'" >> ~/.zshrc
echo "alias refresh='python $(pwd)/app.py refresh'" >> ~/.zshrc
source ~/.zshrc
```

**常用命令**：
```bash
# 完整分析（从图表解析到策略生成）
analyze AAPL -m full

# 快速分析（跳过 Agent3 解析，使用缓存数据）
quick AAPL

# 增量更新（补充缺失字段）
update AAPL

# 刷新分析（清除缓存重新开始）
refresh AAPL
```

### 命令参数

| 参数 | 简写 | 说明 | 示例 |
|------|------|------|------|
| `--mode` | `-m` | 分析模式 (full/quick/update) | `-m quick` |
| `--vix` | `-v` | VIX 指数值 | `-v 18.5` |
| `--ivr` | `-i` | IV Rank (0-100) | `-i 45` |
| `--beta` | `-b` | 股票 Beta 值 | `-b 1.2` |
| `--earning` | `-e` | 财报日期 (YYYY-MM-DD) | `-e 2025-01-15` |
| `--hv20` | `-h` | 20日历史波动率 | `-h 25` |
| `--iv30` | `-iv` | 30日隐含波动率 | `-iv 30` |

**示例**：
```bash
# 完整参数
analyze AAPL --mode quick --vix 18.5 --ivr 45 --beta 1.2

# 简写形式
analyze AAPL -m quick -v 18.5 -i 45 -b 1.2

# 带财报日期
analyze NVDA -m full -e 2025-01-20 -b 1.5

# 组合多个参数
analyze TSLA -m full -v 22 -i 60 -b 1.8 -h 35 -iv 40

# 快速分析
quick AAPL -v 18.5 -i 45
```

---

## 系统架构

### 数据流向图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据输入层                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  用户上传图表 + 命令参数 (--vix, --ivr, --beta, --earning)                   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent 2 - 命令生成                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  生成数据抓取命令列表：!gex, !exp, !volumen, !vexn, !tex, !0dte 等          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent 3 - 图表解析                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  解析图表数据，输出结构化 JSON (27 个原始字段)                               │
│  输出：targets { walls, gamma_metrics, directional_metrics,                 │
│                  atm_iv, validation_metrics }                               │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Code Aggregator - 数据聚合                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  增量合并多次上传的数据，补齐缺失字段                                         │
│  检查 27 个字段完整性 (23 核心 + 4 验证)                                     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Field Calculator - 字段计算                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  计算衍生字段：em1_dollar, t_scale, lambda, gap_distance 等                  │
│  验证原始字段完整性，输出 validation 报告                                     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │                                           │
              ▼                                           ▼
┌─────────────────────────────┐           ┌─────────────────────────────────┐
│  Code 1 - 事件检测           │           │  Code 2 - 四维评分               │
├─────────────────────────────┤           ├─────────────────────────────────┤
│  财报日期、VIX 事件检测       │           │  Gamma/Break/Direction/IV 评分  │
│  输出：event_data            │           │  指数一致性评分                  │
└─────────────────────────────┘           └─────────────────────────────────┘
              │                                           │
              └─────────────────────┬─────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent 5 - 场景分析                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  基于 GEX 结构推演市场场景 (Trend/Range/Transition)                          │
│  前置验证：假突破/波动率陷阱/0DTE 噪音检测                                    │
│  输出：scenarios[], validation_summary                                      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Code 3 - 策略计算 (核心)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ① 处理 validation_metrics → validation_flags                              │
│     - is_vetoed (一票否决)                                                   │
│     - strategy_bias (策略偏好)                                               │
│     - confidence_penalty (噪音惩罚)                                          │
│  ② 计算动态参数：strikes, DTE, Pw, RR                                       │
│  ③ 判断交易风格：SCALP/SWING/POSITION                                       │
│  输出：validation, strikes, pw, rr, exit_params, trade_style_info          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent 6 - 策略生成                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  基于 validation_flags 执行熔断检查                                          │
│  生成 3 个策略：保守/均衡/进取                                               │
│  包含：legs, execution_plan, risk_management                                │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Code 4 - 策略对比                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  执行质量过滤（0DTE 噪音/量价背离/策略偏好）                                  │
│  计算综合评分：EV(40%) + RAR(30%) + Pw(20%) + Quality(10%)                  │
│  输出：quality_filter, top3[], ranking[]                                    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent 7 - 策略排序                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  应用质量过滤规则，输出最终排名                                               │
│  输出：quality_filter_summary, ranking[], top3_comparison                   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Agent 8 - 报告生成                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  生成最终分析报告                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心字段说明

### 原始字段 (27个)

#### 1. 顶层字段 (2个)
| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |
| `spot_price` | number | 当前股价 |

#### 2. walls (4个)
| 字段 | 类型 | 说明 |
|------|------|------|
| `call_wall` | number | Call Wall 价格 |
| `put_wall` | number | Put Wall 价格 |
| `major_wall` | number | 主要阻力/支撑墙价格 |
| `major_wall_type` | string | "call" 或 "put" |

#### 3. gamma_metrics (11个)
| 字段 | 类型 | 说明 |
|------|------|------|
| `vol_trigger` | number | Vol Trigger / Gamma Flip 价格 |
| `spot_vs_trigger` | string | "above" / "below" |
| `net_gex` | number | 净 Gamma 敞口 |
| `gap_distance_dollar` | number | Spot 到最近墙的距离 ($) |
| `nearby_peak.price` | number | 最近峰值价格 |
| `nearby_peak.abs_gex` | number | 最近峰值 GEX |
| `next_cluster_peak.price` | number | 次要峰值价格 |
| `next_cluster_peak.abs_gex` | number | 次要峰值 GEX |
| `monthly_data.*` | object | 月度数据 (可选) |
| `weekly_data.*` | object | 周度数据 (可选) |

#### 4. directional_metrics (5个)
| 字段 | 类型 | 说明 |
|------|------|------|
| `dex_same_dir_pct` | number | 方向一致性百分比 |
| `vanna_dir` | string | Vanna 方向 ("bullish"/"bearish") |
| `vanna_confidence` | string | Vanna 置信度 ("high"/"medium"/"low") |
| `iv_path` | string | IV 路径 ("rising"/"falling"/"stable") |
| `iv_path_confidence` | string | IV 路径置信度 |

#### 5. atm_iv (3个)
| 字段 | 类型 | 说明 |
|------|------|------|
| `iv_7d` | number | 7日 ATM IV |
| `iv_14d` | number | 14日 ATM IV |
| `iv_source` | string | IV 数据来源 |

#### 6. validation_metrics (4个) - 验证字段
| 字段 | 类型 | 说明 | 来源命令 |
|------|------|------|----------|
| `zero_dte_ratio` | number/null | 0DTE GEX 占比 (0-1) | `!0dte` |
| `net_volume_signal` | string/null | 净成交量方向 | `!volumen` |
| `net_vega_exposure` | string/null | Dealer Vega 敞口 | `!vexn` |
| `net_theta_exposure` | string/null | Dealer Theta 敞口 | `!tex net=True` |

**net_volume_signal 枚举值**:
- `Bullish_Call_Buy`: Call 量 > Put 量
- `Bearish_Put_Buy`: Put 量 > Call 量
- `Neutral`: 量相近
- `Divergence`: 量价背离

**net_vega_exposure 枚举值**:
- `Long_Vega`: Dealer 持有正 Vega
- `Short_Vega`: Dealer 持有负 Vega
- `Unknown`: 无法判断

**net_theta_exposure 枚举值**:
- `Long_Theta`: Dealer 持有正 Theta
- `Short_Theta`: Dealer 持有负 Theta
- `Unknown`: 无法判断

---

### 计算字段

| 字段 | 公式/说明 |
|------|----------|
| `em1_dollar` | 1日预期波动 = Spot × IV_7d / √252 |
| `t_scale` | 波动率时间缩放 = (HV20/IV30)^0.8 |
| `lambda` | 空间安全边际系数 (基于 VIX 和 Beta) |
| `gap_distance` | Spot 到最近墙的距离百分比 |
| `cluster_strength` | GEX 峰值聚集强度 |

---

## 验证指标处理流程

```
validation_metrics (Agent 3 原始输出)
         │
         ▼
┌─────────────────────────────────────┐
│ Code 3: process_validation_metrics │
├─────────────────────────────────────┤
│ 1. 噪音检测                          │
│    zero_dte_ratio > 0.5             │
│    → confidence_penalty = 30%       │
│                                     │
│ 2. 量价背离 Veto                     │
│    net_volume_signal == "Divergence"│
│    → is_vetoed = True               │
│                                     │
│ 3. 策略偏好修正                       │
│    Short_Vega → Credit_Favored      │
│    Long_Vega  → Debit_Favored       │
└─────────────────────────────────────┘
         │
         ▼
validation_flags (Code 3 输出)
{
  "is_vetoed": false,
  "veto_reason": null,
  "strategy_bias": "Credit_Favored",
  "confidence_penalty": 0.3,
  "zero_dte_ratio": 0.55,
  "theta_guidance": "高 Theta 有利于卖方"
}
         │
         ▼
┌─────────────────────────────────────┐
│ Agent 6: 验证旗标熔断                 │
├─────────────────────────────────────┤
│ • is_vetoed → 输出 WAIT 策略         │
│ • strategy_bias → 调整策略类型       │
│ • confidence_penalty → 缩减仓位      │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Code 4: 质量过滤                      │
├─────────────────────────────────────┤
│ • 0DTE 噪音 → 短期策略扣分           │
│ • 量价背离 → 方向策略归零            │
│ • 策略偏好不匹配 → 扣分              │
└─────────────────────────────────────┘
         │
         ▼
quality_filter (Code 4 输出)
{
  "filters_triggered": ["0DTE_HIGH"],
  "overall_confidence": 0.7,
  "affected_strategies": ["Bull Call Spread"]
}
```

---

## 配置说明

### env_config.yaml 关键参数

```yaml
# Gamma 相关
gamma:
  vol_trigger_buffer: 0.5     # Vol Trigger 缓冲区
  wall_proximity_threshold: 0.02  # 墙接近阈值
  cluster_strength_min: 0.3   # 最小聚集强度

# Beta 相关
beta:
  default_beta: 1.0
  sector_defaults:
    tech: 1.2
    financials: 1.1
    utilities: 0.7

# 验证指标阈值
validation:
  zero_dte_noise_threshold: 0.5   # 0DTE 噪音阈值
  confidence_penalty_rate: 0.3    # 噪音惩罚系数
```