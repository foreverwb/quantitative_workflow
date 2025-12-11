"""
Agent 2: 命令清单生成
用途：构建"战术(Weekly)"与"战略(Monthly)"双轨数据矩阵
pre_calc: MarketStateCalculator 计算的参数字典
"""


def get_system_prompt(symbol: str, pre_calc: dict) -> str:
    # 提取参数
    strikes = pre_calc["dyn_strikes"]
    dte_short = pre_calc["dyn_dte_short"]
    dte_mid = pre_calc["dyn_dte_mid"]
    dte_long = pre_calc["dyn_dte_long_backup"]
    window = pre_calc["dyn_window"]
    
    return f"""你是 Hedgie-Data-Puller。
**任务**: 为股票代码 {symbol} 执行以下命令序列，命令之间用换行分隔。

**核心逻辑**: 
我们将数据分为 [战术层-Weekly] 和 [战略层-Monthly]，利用 expiration_filter (w/m) 进行降噪。

---

#### 1. 核心结构 (Walls & Clusters) - 双轨制
# [战术视图] 捕捉近端摩擦与周度博弈 (Weekly Friction)
# 作用: 替代 0DTE，识别本周内的 Gamma 阻力与爆发点
!gexr {symbol} {strikes} {dte_short} w

# [战略视图] 锁定机构核心仓位与磁力目标 (Monthly Structure)
# 作用: 剔除周度噪音，暴露真实的 Major Walls (趋势终点)
!gexr {symbol} {strikes} {dte_mid} m

#### 2. 供需流向 (Flows) - 结构性提纯
# 净Gamma与触发线 (全周期，因为Flip通常看整体)
!gexn {symbol} {window} 98
!trigger {symbol} {window}

# Vanna Exposure (使用 m 过滤)
# 作用: 聚焦 Dealer 针对长期持仓的对冲压力，忽略短期赌注
!vanna {symbol} ntm {window} m

# Delta Exposure (与中期结构对齐)
!dexn {symbol} {strikes} {dte_mid}

#### 3. 波动率锚点 (Volatility Anchors)
# [物理锚点] 用于计算 Raw_EM1$ (Weekly 反应快)
!skew {symbol} ivmid atm 7
!skew {symbol} ivmid atm 14

# [定价基准] 用于观察 Skew 偏离度 (Monthly 反应公允价值)
!skew {symbol} ivmid atm 30 m
!term {symbol} 60

#### 4. IV Path & Validation
# 确认 IV 趋势
v_path: {symbol} 7D ATM-IV 对比 3 日 skew 数据

# [真实意图] 确认今日资金流向 (唯一保留的微观指标，用于证伪)
!volumen {symbol} {strikes} {dte_short}

# [波动率底牌] Dealer Vega 敞口
!vexn {symbol} {strikes} {dte_mid}

#### 5. 扩展命令（条件触发）
# 如果 dyn_dte_mid 已经是月度(m)，这里作为备份
!gexr {symbol} {strikes} {dte_long} 

#### 6. 指数背景（必需）
!gexn SPX {window} 98
!skew SPX ivmid atm 7
!skew SPX ivmid atm 14

** Big Tech **
!gexn QQQ {window} 98
!skew QQQ ivmid atm 7
!skew QQQ ivmid atm 14

---
**输出要求**:
1. 严格按照上述命令序列输出，纯文本格式：
- 命令说明
- 执行命令
2. 确保参数替换正确
"""

def get_user_prompt(symbol: str, market_params: dict = None) -> str:
    """
    获取用户提示词
    """
    # 使用用户实际输入的参数
    if market_params:
        vix = market_params.get('vix', 18.5)
        ivr = market_params.get('ivr', 50)
        iv30 = market_params.get('iv30', 30)
        hv20 = market_params.get('hv20', 25)
    else:
        vix, ivr, iv30, hv20 = 18.5, 50, 30, 25
    
    return f"""请立即开始为 {symbol} 生成双轨制命令清单。

完成后，请提示用户下一步操作：
"根据上述命令抓取数据后，请使用以下命令执行完整分析：

python app.py analyze -s {symbol} -f <数据文件夹路径> --vix {vix} --ivr {ivr} --iv30 {iv30} --hv20 {hv20}

"
"""