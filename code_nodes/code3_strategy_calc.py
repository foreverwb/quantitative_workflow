import json
from typing import Dict, Any, Optional


def main(agent3_output: dict, agent5_output: dict, technical_score: float = 0, **env_vars) -> dict:
    """
    Agent 6 策略计算辅助函数
    
    Args:
        agent3_output: Agent 3 的数据校验结果 JSON
        agent5_output: Agent 5 的剧本分析结果 JSON
        technical_score: 技术面评分(0-2)
        **env_vars: 环境变量字典
        
    Returns:
        {"result": 策略计算辅助结果 JSON 字符串}
    """
    try:
        agent3_data = agent3_output
        agent5_data = agent5_output
        
        calculator = StrategyCalculator(env_vars)
        result = calculator.process(agent3_data, agent5_data, technical_score)
        
        return {
            "result": json.dumps(result, ensure_ascii=False, indent=2)
        }
        
    except Exception as e:
        return {
            "result": json.dumps({
                "error": True,
                "error_message": str(e)
            }, ensure_ascii=False, indent=2)
        }


class StrategyCalculator:
    """策略计算引擎"""
    
    def __init__(self, env_vars: Dict[str, Any]):
        """初始化环境变量"""
        self.env = self._parse_env_vars(env_vars)
    
    def _parse_env_vars(self, env_vars: Dict[str, Any]) -> Dict[str, float]:
        """解析环境变量并设置默认值"""
        defaults = {
            # Greeks 目标范围
            'CONSERVATIVE_DELTA_MIN': -0.1,
            'CONSERVATIVE_DELTA_MAX': 0.1,
            'CONSERVATIVE_THETA_MIN': 5.0,
            'CONSERVATIVE_VEGA_MAX': -10.0,
            'BALANCED_DELTA_RANGE': 0.2,
            'BALANCED_THETA_MIN': 8.0,
            'AGGRESSIVE_DELTA_MIN': 0.3,
            'AGGRESSIVE_DELTA_MAX': 0.6,
            'AGGRESSIVE_VEGA_MIN': 10.0,
            
            # DTE 选择
            'DTE_GAP_HIGH_THRESHOLD': 3.0,
            'DTE_GAP_MID_THRESHOLD': 2.0,
            'DTE_MONTHLY_ADJUSTMENT': 7,
            
            # 行权价偏移
            'STRIKE_CONSERVATIVE_LONG_OFFSET': 1.5,
            'STRIKE_BALANCED_WING_OFFSET': 1.0,
            'STRIKE_RATIO_SHORT_OFFSET': 0.5,
            'STRIKE_RATIO_LONG_OFFSET': 1.5,
            'STRIKE_AGGRESSIVE_LONG_OFFSET': 0.2,
            
            # 价差宽度
            'WIDTH_CREDIT_MIN': 0.8,
            'WIDTH_CREDIT_MAX': 1.0,
            'WIDTH_DEBIT_MIN': 1.0,
            'WIDTH_DEBIT_MAX': 1.2,
            
            # RR 计算 - 信用 IVR 映射
            'CREDIT_IVR_0_25': 0.20,
            'CREDIT_IVR_25_50': 0.30,
            'CREDIT_IVR_50_75': 0.40,
            'CREDIT_IVR_75_100': 0.50,
            
            # RR 计算 - 借贷 IVR 映射
            'DEBIT_IVR_0_40': 0.30,
            'DEBIT_IVR_40_70': 0.40,
            'DEBIT_IVR_70_100': 0.50,
            
            # Pw 计算 - 信用
            'PW_CREDIT_BASE': 0.5,
            'PW_CREDIT_CLUSTER_COEF': 0.1,
            'PW_CREDIT_DISTANCE_PENALTY_COEF': 0.05,
            'PW_CREDIT_MIN': 0.4,
            'PW_CREDIT_MAX': 0.85,
            
            # Pw 计算 - 借贷
            'PW_DEBIT_BASE': 0.3,
            'PW_DEBIT_DEX_COEF': 0.1,
            'PW_DEBIT_VANNA_COEF': 0.2,
            'PW_DEBIT_VANNA_WEIGHT_HIGH': 1.0,
            'PW_DEBIT_VANNA_WEIGHT_MEDIUM': 0.6,
            'PW_DEBIT_VANNA_WEIGHT_LOW': 0.3,
            'PW_DEBIT_MIN': 0.25,
            'PW_DEBIT_MAX': 0.75,
            
            # Pw 计算 - 蝶式
            'PW_BUTTERFLY_BODY_INSIDE': 0.65,
            'PW_BUTTERFLY_BODY_OFFSET_1EM': 0.45,
            
            # 止盈止损
            'PROFIT_TARGET_CREDIT_PCT': 30,
            'PROFIT_TARGET_DEBIT_PCT': 60,
            'STOP_LOSS_DEBIT_PCT': 50,
            'STOP_LOSS_CREDIT_PCT': 150,
            'TIME_DECAY_EXIT_DAYS': 3,
            
            # 风险管理
            'MAX_SINGLE_RISK_PCT': 2,
        }
        
        parsed = {}
        for key, default_value in defaults.items():
            value = env_vars.get(key, default_value)
            try:
                parsed[key] = float(value)
            except (ValueError, TypeError):
                parsed[key] = default_value
        
        return parsed
    
    # ============= 1. 行权价计算 =============
    
    def calculate_strikes(self, spot: float, em1: float, walls: Dict) -> Dict:
        """
        计算各策略的行权价
        
        Args:
            spot: 现价
            em1: EM1$ 预期单日波幅
            walls: 墙位信息 {call_wall, put_wall, major_wall}
        
        Returns:
            各策略的行权价字典
        """
        call_wall = walls.get("call_wall", spot * 1.05)
        put_wall = walls.get("put_wall", spot * 0.95)
        
        return {
            "iron_condor": {
                "short_call": round(call_wall, 2),
                "long_call": round(call_wall + self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2),
                "short_put": round(put_wall, 2),
                "long_put": round(put_wall - self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2),
                "width_call": round(self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2),
                "width_put": round(self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2)
            },
            "iron_butterfly": {
                "body": round(spot, 2),
                "call_wing": round(spot + self.env['STRIKE_BALANCED_WING_OFFSET'] * em1, 2),
                "put_wing": round(spot - self.env['STRIKE_BALANCED_WING_OFFSET'] * em1, 2),
                "wing_width": round(self.env['STRIKE_BALANCED_WING_OFFSET'] * em1, 2)
            },
            "bull_call_spread": {
                "long_call": round(spot + self.env['STRIKE_AGGRESSIVE_LONG_OFFSET'] * em1, 2),
                "short_call": round(call_wall, 2),
                "width": round(call_wall - (spot + self.env['STRIKE_AGGRESSIVE_LONG_OFFSET'] * em1), 2)
            },
            "bear_put_spread": {
                "long_put": round(spot - self.env['STRIKE_AGGRESSIVE_LONG_OFFSET'] * em1, 2),
                "short_put": round(put_wall, 2),
                "width": round((spot - self.env['STRIKE_AGGRESSIVE_LONG_OFFSET'] * em1) - put_wall, 2)
            },
            "bull_put_spread": {
                "long_put": round(put_wall - self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2),
                "short_put": round(put_wall, 2),
                "width": round(self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2)
            },
            "bear_call_spread": {
                "long_call": round(call_wall + self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2),
                "short_call": round(call_wall, 2),
                "width": round(self.env['STRIKE_CONSERVATIVE_LONG_OFFSET'] * em1, 2)
            },
            "call_ratio_spread": {
                "long_call": round(spot + self.env['STRIKE_RATIO_SHORT_OFFSET'] * em1, 2),
                "short_call": round(spot + self.env['STRIKE_RATIO_LONG_OFFSET'] * em1, 2),
                "ratio": "1:2"
            },
            "put_ratio_spread": {
                "long_put": round(spot - self.env['STRIKE_RATIO_SHORT_OFFSET'] * em1, 2),
                "short_put": round(spot - self.env['STRIKE_RATIO_LONG_OFFSET'] * em1, 2),
                "ratio": "1:2"
            },
            "long_call": {
                "strike": round(spot + self.env['STRIKE_AGGRESSIVE_LONG_OFFSET'] * em1, 2)
            },
            "long_put": {
                "strike": round(spot - self.env['STRIKE_AGGRESSIVE_LONG_OFFSET'] * em1, 2)
            }
        }
    
    # ============= 2. DTE 计算 =============
    
    def calculate_dte(self, gap_distance_em1: float, monthly_override: bool) -> Dict:
        """
        动态 DTE 计算
        
        Args:
            gap_distance_em1: gap 距离（EM1$ 倍数）
            monthly_override: 是否月度叠加
        
        Returns:
            DTE 信息字典
        """
        # 基础规则
        if gap_distance_em1 > self.env['DTE_GAP_HIGH_THRESHOLD']:
            base_dte = 14
            gap_level = "high"
        elif gap_distance_em1 >= self.env['DTE_GAP_MID_THRESHOLD']:
            base_dte = 10
            gap_level = "mid"
        else:
            base_dte = 7
            gap_level = "low"
        
        # 月度调整
        if monthly_override:
            adjustment = int(self.env['DTE_MONTHLY_ADJUSTMENT'])
            final_dte = base_dte + adjustment
            rationale = f"gap_distance_em1={gap_distance_em1:.2f}>{self.env['DTE_GAP_HIGH_THRESHOLD']if gap_level=='high' else f'在{self.env['DTE_GAP_MID_THRESHOLD']}-{self.env['DTE_GAP_HIGH_THRESHOLD']}' if gap_level=='mid' else f'<{self.env['DTE_GAP_MID_THRESHOLD']}'}选择{base_dte}日DTE，月度叠加+{adjustment}日={final_dte}日"
        else:
            final_dte = base_dte
            rationale = f"gap_distance_em1={gap_distance_em1:.2f}选择{final_dte}日DTE，无月度叠加"
        
        return {
            "base_dte": base_dte,
            "final_dte": final_dte,
            "gap_level": gap_level,
            "monthly_override": monthly_override,
            "rationale": rationale
        }
    
    # ============= 3. RR 盈亏比计算 =============
    
    def calculate_rr_credit(self, width: float, ivr: float = 40) -> Dict:
        """
        信用价差 RR 计算
        
        Args:
            width: 价差宽度
            ivr: 隐含波动率百分位（0-100）
        
        Returns:
            RR 计算结果
        """
        # IVR 映射
        if ivr <= 25:
            credit_ratio = self.env['CREDIT_IVR_0_25']
            ivr_range = "0-25%"
        elif ivr <= 50:
            credit_ratio = self.env['CREDIT_IVR_25_50']
            ivr_range = "25-50%"
        elif ivr <= 75:
            credit_ratio = self.env['CREDIT_IVR_50_75']
            ivr_range = "50-75%"
        else:
            credit_ratio = self.env['CREDIT_IVR_75_100']
            ivr_range = "75-100%"
        
        credit = width * credit_ratio
        max_loss = width - credit
        
        # 格式化 RR 比率
        if credit > 0:
            rr_simplified = f"1:{max_loss/credit:.1f}"
        else:
            rr_simplified = "N/A"
        
        formula = f"Width={width:.2f}, IVR={ivr}%在{ivr_range}→credit_ratio={credit_ratio}, Credit={credit:.2f}, MaxLoss={max_loss:.2f}, RR={credit:.2f}:{max_loss:.2f}"
        
        return {
            "width": round(width, 2),
            "ivr": ivr,
            "ivr_range": ivr_range,
            "credit_ratio": credit_ratio,
            "credit": round(credit, 2),
            "max_profit": round(credit, 2),
            "max_loss": round(max_loss, 2),
            "rr_ratio": rr_simplified,
            "formula": formula
        }
    
    def calculate_rr_debit(self, width: float, ivr: float = 40) -> Dict:
        """
        借贷价差 RR 计算
        
        Args:
            width: 价差宽度
            ivr: 隐含波动率百分位（0-100）
        
        Returns:
            RR 计算结果
        """
        # IVR 映射
        if ivr <= 40:
            debit_ratio = self.env['DEBIT_IVR_0_40']
            ivr_range = "0-40%"
        elif ivr <= 70:
            debit_ratio = self.env['DEBIT_IVR_40_70']
            ivr_range = "40-70%"
        else:
            debit_ratio = self.env['DEBIT_IVR_70_100']
            ivr_range = "70-100%"
        
        debit = width * debit_ratio
        max_profit = width - debit
        
        # 格式化 RR 比率
        if debit > 0:
            rr_simplified = f"{max_profit/debit:.1f}:1"
        else:
            rr_simplified = "N/A"
        
        formula = f"Width={width:.2f}, IVR={ivr}%在{ivr_range}→debit_ratio={debit_ratio}, Debit={debit:.2f}, MaxProfit={max_profit:.2f}, RR={max_profit:.2f}:{debit:.2f}"
        
        return {
            "width": round(width, 2),
            "ivr": ivr,
            "ivr_range": ivr_range,
            "debit_ratio": debit_ratio,
            "debit": round(debit, 2),
            "max_profit": round(max_profit, 2),
            "max_loss": round(debit, 2),
            "rr_ratio": rr_simplified,
            "formula": formula
        }
    
    # ============= 4. Pw 胜率计算 =============
    
    def calculate_pw_credit(self, cluster_strength: float, gap_distance_em1: float, 
                           technical_score: float = 0) -> Dict:
        """
        信用价差胜率计算
        
        Args:
            cluster_strength: 簇强度比率
            gap_distance_em1: gap 距离（EM1$ 倍数）
            technical_score: 技术面评分（0-2）
        
        Returns:
            Pw 计算结果
        """
        base = self.env['PW_CREDIT_BASE']
        cluster_adj = self.env['PW_CREDIT_CLUSTER_COEF'] * cluster_strength
        distance_penalty = self.env['PW_CREDIT_DISTANCE_PENALTY_COEF'] * gap_distance_em1
        
        pw_raw = base + cluster_adj - distance_penalty
        
        # 技术面提升
        technical_boost = 0.05 * technical_score if technical_score > 0 else 0
        
        # 限制范围
        pw_adjusted = max(self.env['PW_CREDIT_MIN'], 
                          min(self.env['PW_CREDIT_MAX'], 
                              pw_raw + technical_boost))
        
        formula = f"base {base} + cluster {cluster_adj:.3f} - distance {distance_penalty:.3f} + technical {technical_boost:.2f} = {pw_adjusted:.2f}"
        
        return {
            "base": base,
            "cluster_strength": cluster_strength,
            "cluster_adj": round(cluster_adj, 3),
            "gap_distance_em1": gap_distance_em1,
            "distance_penalty": round(distance_penalty, 3),
            "technical_score": technical_score,
            "technical_boost": round(technical_boost, 2),
            "pw_raw": round(pw_raw, 3),
            "pw_adjusted": round(pw_adjusted, 2),
            "pw_estimate": f"{int(pw_adjusted * 100)}%",
            "formula": formula
        }
    
    def calculate_pw_debit(self, dex_same_dir_pct: float, vanna_confidence: str, 
                          gap_distance_em1: float) -> Dict:
        """
        借贷价差胜率计算
        
        Args:
            dex_same_dir_pct: DEX 同向百分比（0-100）
            vanna_confidence: Vanna 置信度（high/medium/low）
            gap_distance_em1: gap 距离（EM1$ 倍数）
        
        Returns:
            Pw 计算结果
        """
        # Vanna 权重
        vanna_weight_map = {
            'high': self.env['PW_DEBIT_VANNA_WEIGHT_HIGH'],
            'medium': self.env['PW_DEBIT_VANNA_WEIGHT_MEDIUM'],
            'low': self.env['PW_DEBIT_VANNA_WEIGHT_LOW']
        }
        vanna_weight = vanna_weight_map.get(vanna_confidence, self.env['PW_DEBIT_VANNA_WEIGHT_LOW'])
        
        # 基础计算
        base = self.env['PW_DEBIT_BASE']
        dex_adj = self.env['PW_DEBIT_DEX_COEF'] * (dex_same_dir_pct / 100)
        vanna_adj = vanna_weight * self.env['PW_DEBIT_VANNA_COEF']
        
        pw_raw = base + dex_adj + vanna_adj
        
        # gap 距离惩罚
        if gap_distance_em1 > 3:
            gap_penalty = -0.05
        elif gap_distance_em1 > 2:
            gap_penalty = -0.03
        else:
            gap_penalty = 0
        
        # 限制范围
        pw_adjusted = max(self.env['PW_DEBIT_MIN'], 
                          min(self.env['PW_DEBIT_MAX'], 
                              pw_raw + gap_penalty))
        
        formula = f"base {base} + dex {dex_adj:.3f} + vanna {vanna_adj:.2f} + gap_penalty {gap_penalty:.2f} = {pw_adjusted:.2f}"
        
        return {
            "base": base,
            "dex_same_dir_pct": dex_same_dir_pct,
            "dex_adj": round(dex_adj, 3),
            "vanna_confidence": vanna_confidence,
            "vanna_weight": vanna_weight,
            "vanna_adj": round(vanna_adj, 2),
            "gap_distance_em1": gap_distance_em1,
            "gap_penalty": gap_penalty,
            "pw_raw": round(pw_raw, 3),
            "pw_adjusted": round(pw_adjusted, 2),
            "pw_estimate": f"{int(pw_adjusted * 100)}%",
            "formula": formula
        }
    
    def calculate_pw_butterfly(self, spot: float, body: float, em1: float, 
                               iv_path: str = "平") -> Dict:
        """
        蝶式策略胜率计算
        
        Args:
            spot: 现价
            body: 蝶式中心价格
            em1: EM1$
            iv_path: IV 路径（升/降/平）
        
        Returns:
            Pw 计算结果
        """
        distance_em1 = abs(spot - body) / em1 if em1 > 0 else 0
        
        # 基础胜率
        if distance_em1 < 0.3:
            pw_base = self.env['PW_BUTTERFLY_BODY_INSIDE']
            distance_desc = "spot在body内"
        elif distance_em1 < 1.0:
            pw_base = 0.55
            distance_desc = "轻微偏离"
        else:
            pw_base = self.env['PW_BUTTERFLY_BODY_OFFSET_1EM']
            distance_desc = "偏离1EM1$"
        
        # IV 调整
        if iv_path == "升":
            iv_adj = -0.05
            iv_note = "IV扩张不利蝶式"
        elif iv_path == "降":
            iv_adj = 0.05
            iv_note = "IV压缩有利蝶式"
        else:
            iv_adj = 0
            iv_note = "IV稳定"
        
        pw_adjusted = max(0.3, min(0.75, pw_base + iv_adj))
        
        formula = f"距离body {distance_em1:.2f}×EM1$({distance_desc})→base {pw_base}, IV路径{iv_path}调整{iv_adj:+.2f} = {pw_adjusted:.2f}"
        
        return {
            "spot": spot,
            "body": body,
            "distance_em1": round(distance_em1, 2),
            "distance_desc": distance_desc,
            "iv_path": iv_path,
            "iv_adj": iv_adj,
            "iv_note": iv_note,
            "pw_base": pw_base,
            "pw_adjusted": round(pw_adjusted, 2),
            "pw_estimate": f"{int(pw_adjusted * 100)}%",
            "formula": formula
        }
    
    # ============= 5. Greeks 范围 =============
    
    def get_greeks_ranges(self) -> Dict:
        """
        获取各策略类型的 Greeks 目标范围
        
        Returns:
            Greeks 范围字典
        """
        return {
            "conservative": {
                "delta_min": self.env['CONSERVATIVE_DELTA_MIN'],
                "delta_max": self.env['CONSERVATIVE_DELTA_MAX'],
                "theta_min": self.env['CONSERVATIVE_THETA_MIN'],
                "vega_max": self.env['CONSERVATIVE_VEGA_MAX'],
                "description": "保守策略：接近中性Delta，正Theta收益，负Vega做空波动率"
            },
            "balanced": {
                "delta_range": self.env['BALANCED_DELTA_RANGE'],
                "theta_min": self.env['BALANCED_THETA_MIN'],
                "vega_range": [-5, 5],
                "description": "均衡策略：轻微方向敞口±Delta_range，正Theta，Vega中性"
            },
            "aggressive": {
                "delta_min": self.env['AGGRESSIVE_DELTA_MIN'],
                "delta_max": self.env['AGGRESSIVE_DELTA_MAX'],
                "vega_min": self.env['AGGRESSIVE_VEGA_MIN'],
                "description": "进取策略：明确方向Delta 0.3-0.6，Theta可为负，正Vega做多波动率"
            }
        }
    
    # ============= 6. 止盈止损参数 =============
    
    def get_exit_parameters(self) -> Dict:
        """
        获取止盈止损参数
        
        Returns:
            止盈止损参数字典
        """
        return {
            "credit_strategies": {
                "profit_target_pct": int(self.env['PROFIT_TARGET_CREDIT_PCT']),
                "stop_loss_pct": int(self.env['STOP_LOSS_CREDIT_PCT']),
                "time_decay_exit_days": int(self.env['TIME_DECAY_EXIT_DAYS']),
                "description": f"信用策略：权利金衰减至{int(self.env['PROFIT_TARGET_CREDIT_PCT'])}%止盈，浮亏{int(self.env['STOP_LOSS_CREDIT_PCT'])}%止损"
            },
            "debit_strategies": {
                "profit_target_pct": int(self.env['PROFIT_TARGET_DEBIT_PCT']),
                "stop_loss_pct": int(self.env['STOP_LOSS_DEBIT_PCT']),
                "time_decay_exit_days": int(self.env['TIME_DECAY_EXIT_DAYS']),
                "description": f"借贷策略：浮盈{int(self.env['PROFIT_TARGET_DEBIT_PCT'])}%止盈，亏损{int(self.env['STOP_LOSS_DEBIT_PCT'])}%止损"
            },
            "time_management": {
                "exit_days_before_expiry": int(self.env['TIME_DECAY_EXIT_DAYS']),
                "description": f"时间管理：到期前{int(self.env['TIME_DECAY_EXIT_DAYS'])}日平仓避免Pin Risk"
            }
        }
    
    # ============= 主处理函数 =============
    
    def process(self, agent3_data: Dict, agent5_data: Dict, technical_score: float = 0) -> Dict:
        """
        主处理流程
        
        Args:
            agent3_data: Agent 3 数据
            agent5_data: Agent 5 数据
            technical_score: 技术面评分
        
        Returns:
            完整计算结果
        """
        
        # 直接从根节点获取数据（不再处理 targets 数组）
        spot = agent3_data.get("spot_price", 0)
        em1 = agent3_data.get("em1_dollar", 0)
        walls = agent3_data.get("walls", {})
        gamma_metrics = agent3_data.get("gamma_metrics", {})
        directional_metrics = agent3_data.get("directional_metrics", {})
        
        # 校验必需字段
        if spot == 0 or em1 == 0:
            raise ValueError("Agent 3 数据缺失关键字段：spot_price 或 em1_dollar")
        
        # Agent 5 数据
        scenario = agent5_data.get("scenario_classification", {})
        
        # 执行计算
        strikes = self.calculate_strikes(spot, em1, walls)
        dte_info = self.calculate_dte(
            gamma_metrics.get("gap_distance_em1_multiple", 2.0),
            gamma_metrics.get("monthly_cluster_override", False)
        )
        
        # 估算 IVR（简化处理，实际应从市场数据获取）
        ivr_estimate = 40  # 默认中等 IVR
        
        # RR 计算（使用实际宽度）
        rr_credit_ic = self.calculate_rr_credit(
            strikes["iron_condor"]["width_call"],
            ivr_estimate
        )
        
        rr_debit_bull = self.calculate_rr_debit(
            strikes["bull_call_spread"]["width"],
            ivr_estimate
        )
        
        # Pw 计算
        pw_credit = self.calculate_pw_credit(
            gamma_metrics.get("cluster_strength_ratio", 1.5),
            gamma_metrics.get("gap_distance_em1_multiple", 2.0),
            technical_score
        )
        
        pw_debit = self.calculate_pw_debit(
            directional_metrics.get("dex_same_dir_pct", 50),
            directional_metrics.get("vanna_confidence", "medium"),
            gamma_metrics.get("gap_distance_em1_multiple", 2.0)
        )
        
        pw_butterfly = self.calculate_pw_butterfly(
            spot,
            spot,  # body 在现价
            em1,
            directional_metrics.get("iv_path", "平")
        )
        
        # Greeks 范围
        greeks_ranges = self.get_greeks_ranges()
        
        # 止盈止损参数
        exit_params = self.get_exit_parameters()
        
        # 组装结果
        result = {
            # 行权价（保留结构，供 Agent 6 选择）
            "strikes": strikes,
            
            # DTE（扁平化）
            "dte_final": dte_info["final_dte"],
            "dte_rationale": dte_info["rationale"],
            "dte_base": dte_info["base_dte"],
            "dte_gap_level": dte_info["gap_level"],
            "dte_monthly_override": dte_info["monthly_override"],
            
            # RR - Iron Condor（扁平化）
            "rr_ic_credit": rr_credit_ic["credit"],
            "rr_ic_max_profit": rr_credit_ic["max_profit"],
            "rr_ic_max_loss": rr_credit_ic["max_loss"],
            "rr_ic_ratio": rr_credit_ic["rr_ratio"],
            "rr_ic_formula": rr_credit_ic["formula"],
            "rr_ic_width": rr_credit_ic["width"],
            "rr_ic_ivr": rr_credit_ic["ivr"],
            
            # RR - Bull Call Spread（扁平化）
            "rr_bull_debit": rr_debit_bull["debit"],
            "rr_bull_max_profit": rr_debit_bull["max_profit"],
            "rr_bull_max_loss": rr_debit_bull["max_loss"],
            "rr_bull_ratio": rr_debit_bull["rr_ratio"],
            "rr_bull_formula": rr_debit_bull["formula"],
            "rr_bull_width": rr_debit_bull["width"],
            
            # Pw - Credit（扁平化）
            "pw_credit_estimate": pw_credit["pw_estimate"],
            "pw_credit_formula": pw_credit["formula"],
            "pw_credit_note": pw_credit["pw_note"],
            "pw_credit_base": pw_credit["base"],
            "pw_credit_cluster_adj": pw_credit["cluster_adj"],
            "pw_credit_distance_penalty": pw_credit["distance_penalty"],
            "pw_credit_technical_boost": pw_credit["technical_boost"],
            "pw_credit_adjusted": pw_credit["pw_adjusted"],
            
            # Pw - Debit（扁平化）
            "pw_debit_estimate": pw_debit["pw_estimate"],
            "pw_debit_formula": pw_debit["formula"],
            "pw_debit_note": pw_debit["pw_note"],
            "pw_debit_base": pw_debit["base"],
            "pw_debit_dex_adj": pw_debit["dex_adj"],
            "pw_debit_vanna_adj": pw_debit["vanna_adj"],
            "pw_debit_gap_penalty": pw_debit["gap_penalty"],
            "pw_debit_adjusted": pw_debit["pw_adjusted"],
            
            # Pw - Butterfly（扁平化）
            "pw_butterfly_estimate": pw_butterfly["pw_estimate"],
            "pw_butterfly_formula": pw_butterfly["formula"],
            "pw_butterfly_note": pw_butterfly["pw_note"],
            "pw_butterfly_distance_em1": pw_butterfly["distance_em1"],
            
            # Greeks - Conservative（扁平化）
            "greeks_conservative_delta_min": greeks_ranges["conservative"]["delta_min"],
            "greeks_conservative_delta_max": greeks_ranges["conservative"]["delta_max"],
            "greeks_conservative_theta_min": greeks_ranges["conservative"]["theta_min"],
            "greeks_conservative_vega_max": greeks_ranges["conservative"]["vega_max"],
            "greeks_conservative_desc": greeks_ranges["conservative"]["description"],
            
            # Greeks - Balanced（扁平化）
            "greeks_balanced_delta_range": greeks_ranges["balanced"]["delta_range"],
            "greeks_balanced_theta_min": greeks_ranges["balanced"]["theta_min"],
            "greeks_balanced_desc": greeks_ranges["balanced"]["description"],
            
            # Greeks - Aggressive（扁平化）
            "greeks_aggressive_delta_min": greeks_ranges["aggressive"]["delta_min"],
            "greeks_aggressive_delta_max": greeks_ranges["aggressive"]["delta_max"],
            "greeks_aggressive_vega_min": greeks_ranges["aggressive"]["vega_min"],
            "greeks_aggressive_desc": greeks_ranges["aggressive"]["description"],
            
            # Exit Parameters - Credit（扁平化）
            "exit_credit_profit_pct": exit_params["credit_strategies"]["profit_target_pct"],
            "exit_credit_stop_pct": exit_params["credit_strategies"]["stop_loss_pct"],
            "exit_credit_time_days": exit_params["credit_strategies"]["time_decay_exit_days"],
            "exit_credit_desc": exit_params["credit_strategies"]["description"],
            
            # Exit Parameters - Debit（扁平化）
            "exit_debit_profit_pct": exit_params["debit_strategies"]["profit_target_pct"],
            "exit_debit_stop_pct": exit_params["debit_strategies"]["stop_loss_pct"],
            "exit_debit_time_days": exit_params["debit_strategies"]["time_decay_exit_days"],
            "exit_debit_desc": exit_params["debit_strategies"]["description"],
            
            # Exit Parameters - Time（扁平化）
            "exit_time_days": exit_params["time_management"]["exit_days_before_expiry"],
            "exit_time_desc": exit_params["time_management"]["description"],
            
            # Metadata（扁平化）
            "meta_spot": spot,
            "meta_em1": em1,
            "meta_ivr": ivr_estimate,
            "meta_technical_score": technical_score,
            "meta_primary_scenario": scenario.get("primary_scenario", "未知"),
            "meta_scenario_probability": scenario.get("scenario_probability", 0),
            "meta_gamma_regime": agent5_data.get("gamma_regime", {}).get("spot_vs_trigger", "unknown")
        }
        
        return result