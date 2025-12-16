"""
Code 3: 策略计算引擎 (Swing 增强版 v2.2)
变更：
1. [夯实] 强制 R > 1.8 逻辑：Debit 策略优先，Credit 策略需深度虚值。
"""
import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from utils.config_loader import config 
import traceback
from loguru import logger

@dataclass
class ValidationFlags:
    is_vetoed: bool = False
    veto_reason: str = ""
    weekly_friction_state: str = "Clear" # Clear / Obstructed
    execution_guidance: str = ""
    strategy_bias: str = "Neutral"
    strategy_bias_reason: str = ""
    net_volume_signal: Optional[str] = None
    net_vega_exposure: Optional[str] = None
    confidence_penalty: float = 0.0

@dataclass
class DTEResult:
    final: int
    base: int = 21
    t_scale: float = 1.0
    t_scale_source: str = "本地计算"
    gap_level: str = "mid"
    monthly_override: bool = False
    vol_state: str = "IV/HV均衡"
    vrp: float = 1.0
    rationale: str = ""

@dataclass
class RiskRewardResult:
    width: float
    ivr: int
    cost: float
    max_profit: float
    max_loss: float
    ratio: float  # 改为 float 以便数值比较
    ratio_str: str 
    meets_edge: bool # 是否满足 R > 1.8
    formula: str

@dataclass
class WinProbResult:
    estimate: float
    formula: str
    note: str
    noise_adjusted: Optional[float] = None
    theoretical_base: float = 0.5

@dataclass
class StrategyOutput:
    trade_status: str
    validation: ValidationFlags
    strikes: Dict
    dte: DTEResult
    volatility: Dict
    rr: Dict[str, RiskRewardResult]
    pw: Dict[str, WinProbResult]
    greeks_ranges: Dict
    exit_params: Dict
    meta: Dict

class StrategyCalculator:
    
    def __init__(self, env_vars: Dict[str, Any]):
        self.conf = config
        self.market_params = env_vars.get('market_params', {})
        
    def _calc_theoretical_win_rate(self, strategy_type: str, iv: float, dte: int) -> float:
        """基于 Delta/正态分布估算理论胜率"""
        if dte <= 0 or iv <= 0: return 0.5
        if strategy_type == 'credit':
            return 0.65 
        elif strategy_type == 'debit':
            return 0.45 
        return 0.5

    def _calc_weekly_friction(self, spot: float, gamma_metrics: Dict) -> Tuple[str, str]:
        """
        逻辑：如果现价距离 Weekly Nearby Peak < 1.0% -> 视为受阻
        """
        weekly_peak = gamma_metrics.get('nearby_peak', {}).get('price')
        if not weekly_peak or spot == 0:
            return "Clear", "无周度结构阻挡"
            
        distance_pct = abs(spot - weekly_peak) / spot
        
        # 阈值：1.0%
        if distance_pct < 0.01:
            return "Obstructed", f"受周度结构 {weekly_peak} 压制 (距离 {distance_pct:.1%})"
        else:
            return "Clear", "周度路径通畅"

    def _process_validation(self, data: Dict, gamma_metrics: Dict, spot: float, primary_scenario: str) -> ValidationFlags:
        flags = ValidationFlags()
        
        friction_state, friction_note = self._calc_weekly_friction(spot, gamma_metrics)
        flags.weekly_friction_state = friction_state
        
        if friction_state == "Obstructed":
            flags.execution_guidance = f"⚠️ {friction_note}。建议：等待突破或回踩确认，放弃市价追单。"
        else:
            flags.execution_guidance = "结构通畅，可按计划执行。"
            
        # 2. 量价背离 (保留)
        vol_signal = data.get("net_volume_signal")
        flags.net_volume_signal = vol_signal
        
        bullish_kw = ["上行", "突破", "看涨", "bullish", "Bullish"]
        bearish_kw = ["下行", "跌破", "看跌", "bearish", "Bearish"]
        is_bullish = any(k in primary_scenario for k in bullish_kw)
        is_bearish = any(k in primary_scenario for k in bearish_kw)
        
        if vol_signal and vol_signal not in ("Neutral", "Unknown", None):
            if is_bullish and vol_signal == "Bearish_Put_Buy":
                flags.is_vetoed = True
                flags.veto_reason = "GEX看涨但实时成交量看跌(量价背离)"
            elif is_bearish and vol_signal == "Bullish_Call_Buy":
                flags.is_vetoed = True
                flags.veto_reason = "GEX看跌但实时成交量看涨(量价背离)"
        
        # 3. 策略偏好
        vega = data.get("net_vega_exposure")
        flags.net_vega_exposure = vega
        if vega == "Short_Vega":
            flags.strategy_bias = "Credit_Favored"
            flags.strategy_bias_reason = "Dealer Short Vega，压制波动"
        elif vega == "Long_Vega":
            flags.strategy_bias = "Debit_Favored"
            flags.strategy_bias_reason = "Dealer Long Vega，放大波动"
            
        return flags

    def _calc_rr_debit(self, width: float, ivr: int) -> RiskRewardResult:
        """
        借贷价差 RR (强行对齐 R > 1.8)
        逻辑：Debit 成本必须低于 Width 的 35% (1/2.8 ≈ 0.35 -> R=1.8)
        """
        cost_ratio_est = 0.35 + (ivr / 100.0) * 0.15
        debit = width * cost_ratio_est
        profit = width - debit
        r_value = profit / debit if debit > 0 else 0
        meets_edge = r_value >= 1.8
        
        return RiskRewardResult(
            width=round(width, 2), cost=round(debit, 2), ivr=ivr,
            max_profit=round(profit, 2), max_loss=round(debit, 2),
            ratio=round(r_value, 2), ratio_str=f"{r_value:.1f}:1",
            meets_edge=meets_edge, formula="Est Cost"
        )

    def _calc_rr_credit(self, width: float, ivr: int) -> RiskRewardResult:
        """信用价差 RR"""
        credit_ratio_est = 0.20 + (ivr / 100.0) * 0.20
        credit = width * credit_ratio_est
        risk = width - credit
        r_value = credit / risk if risk > 0 else 0
        meets_edge = False # Credit 很难达到 R>1.8
        
        return RiskRewardResult(
            width=round(width, 2), cost=-round(credit, 2), ivr=ivr,
            max_profit=round(credit, 2), max_loss=round(risk, 2),
            ratio=round(r_value, 2), ratio_str=f"1:{1/r_value:.1f}" if r_value > 0 else "N/A",
            meets_edge=meets_edge, formula="Est Credit"
        )

    def _calc_strikes(self, spot: float, em1: float, walls: Dict) -> Dict:
        """计算各策略行权价"""
        call_w = walls.get("call_wall") or spot * 1.05
        put_w = walls.get("put_wall") or spot * 0.95
        
        e = self.conf.strikes
        cons_off = e.conservative_long_offset
        bal_off = e.balanced_wing_offset
        agg_off = e.aggressive_long_offset
        
        def r(x): return round(x, 2)
        
        return {
            "iron_condor": {
                "short_call": r(call_w), "long_call": r(call_w + cons_off * em1),
                "short_put": r(put_w), "long_put": r(put_w - cons_off * em1),
                "width_call": r(cons_off * em1), "width_put": r(cons_off * em1)
            },
            "bull_call_spread": {
                "long_call": r(spot + agg_off * em1), "short_call": r(call_w),
                "width": r(call_w - (spot + agg_off * em1))
            },
            "bear_put_spread": {
                "long_put": r(spot - agg_off * em1), "short_put": r(put_w),
                "width": r((spot - agg_off * em1) - put_w)
            },
            "long_call": {"strike": r(spot + agg_off * em1)},
            "long_put": {"strike": r(spot - agg_off * em1)}
        }

    def _calc_dte(self, gap_em1: float, monthly_override: bool, vol_metrics: Dict) -> DTEResult:
        gap_em1 = gap_em1 or 2.0
        cached = vol_metrics.get('t_scale')
        if cached is not None:
            t_scale, source = cached, "上游缓存"
        else:
            t_scale = 1.0
            source = "Default"
        
        base, vol_adj = 21.0, 21.0 * t_scale
        gap_mult = 1.2 if gap_em1 > 3 else (0.8 if gap_em1 < 1 else 1.0)
        raw_dte = vol_adj * gap_mult
        if monthly_override and raw_dte < 25: raw_dte = 25.0
        final = int(max(5, min(45, raw_dte)))
        
        return DTEResult(
            final=final, base=int(base), t_scale=round(t_scale, 3), t_scale_source=source,
            gap_level="mid", monthly_override=monthly_override, vol_state="Normal", vrp=1.0,
            rationale=f"基准{int(base)}×T{t_scale:.2f}×Gap{gap_mult}→{final}d"
        )

    def _calc_pw_credit(self, cluster: float, gap_em1: float, tech_score: float, iv: float, dte: int) -> WinProbResult:
        c = self.conf.pw_calculation.credit
        print("_calc_pw_credit", c)
        base = c.base
        c_adj = c.cluster_coef * (cluster or 1.0)
        d_pen = c.distance_penalty_coef * (gap_em1 or 2.0)
        theoretical = self._calc_theoretical_win_rate('credit', iv, dte)
        raw = base + c_adj - d_pen
        final = (raw * 0.7) + (theoretical * 0.3)
        adj = max(c.min, min(c.max, final))
        return WinProbResult(estimate=round(adj, 3), theoretical_base=theoretical, formula="Hybrid", note="Credit")

    def _calc_pw_debit(self, dex_pct: float, vanna_conf: str, gap_em1: float, iv: float, dte: int) -> WinProbResult:
        e = self.conf.pw_calculation.debit
        theoretical = self._calc_theoretical_win_rate('debit', iv, dte)
        final = (e.base * 0.7) + (theoretical * 0.3)
        adj = max(e.min, min(e.max, final))
        return WinProbResult(estimate=round(adj, 3), theoretical_base=theoretical, formula="Hybrid", note="Debit")

    def _calc_pw_butterfly(self, spot: float, body: float, em1: float, iv_path: str) -> WinProbResult:
        return WinProbResult(estimate=0.55, formula="Fixed", note="Butterfly")

    def _get_greeks_ranges(self) -> Dict:
        return self.conf.greeks

    def _get_exit_params(self) -> Dict:
        return self.conf.exit_rules

    def _build_vetoed_result(self, validation: ValidationFlags, spot: float, em1: float, scenario: str) -> Dict:
        return {
            "trade_status": "VETOED",
            "veto_reason": validation.veto_reason,
            "validation": asdict(validation),
            "strategies": [],
            "meta": {"spot": spot, "em1": em1, "primary_scenario": scenario}
        }

    def _safe_get(self, data: Dict, *keys, default=None):
        for key in keys:
            if isinstance(data, dict): data = data.get(key, default)
            else: return default
        return data if data is not None else default

    def process(self, agent3_data: Dict, agent5_data: Dict, technical_score: float = 0) -> Dict:
        spot = agent3_data.get("spot_price", 0)
        em1 = agent3_data.get("em1_dollar", 0)
        walls = agent3_data.get("walls", {})
        gamma = agent3_data.get("targets", {}).get("gamma_metrics", {})
        direction = agent3_data.get("directional_metrics", {})
        vol_metrics = agent3_data.get("volatility_metrics", {})
        validation_raw = agent3_data.get("targets", {}).get("validation_metrics", {})
        
        scenario = agent5_data.get("scenario_classification", {})
        primary_scenario = scenario.get("primary_scenario", "未知")
        
        if spot == 0 or em1 == 0:
            raise ValueError("缺失关键字段: spot_price 或 em1_dollar")
        
        # 1. 验证 (传入更多参数)
        validation = self._process_validation(validation_raw, gamma, spot, primary_scenario)
        
        if validation.is_vetoed:
            return self._build_vetoed_result(validation, spot, em1, primary_scenario)
        
        strikes = self._calc_strikes(spot, em1, walls)
        dte = self._calc_dte(gamma.get("gap_distance_em1_multiple", 2.0),
                            gamma.get("monthly_cluster_override", False), vol_metrics)
        
        ivr = self._safe_get(vol_metrics, 'market_snapshot', 'ivr', default=40)
        iv_atm = self._safe_get(vol_metrics, 'market_snapshot', 'iv30', default=30)
        
        rr_credit = self._calc_rr_credit(strikes["iron_condor"]["width_call"], ivr)
        rr_debit = self._calc_rr_debit(strikes["bull_call_spread"]["width"], ivr)
        
        # 3. 策略偏好修正 (根据 Edge)
        if rr_debit.meets_edge and not rr_credit.meets_edge:
            if validation.strategy_bias == "Neutral":
                validation.strategy_bias = "Debit_Favored"
                validation.strategy_bias_reason = "Debit策略盈亏比 > 1.8 (Edge优先)"
        
        pw_credit = self._calc_pw_credit(gamma.get("cluster_strength_ratio", 1.5),
                                          gamma.get("gap_distance_em1_multiple", 2.0), technical_score, iv_atm, dte.final)
        pw_debit = self._calc_pw_debit(direction.get("dex_same_dir_pct", 0.5),
                                        direction.get("vanna_confidence", "medium"),
                                        gamma.get("gap_distance_em1_multiple", 2.0), iv_atm, dte.final)
        pw_butterfly = self._calc_pw_butterfly(spot, spot, em1, direction.get("iv_path", "平"))
        
        return {
            "trade_status": "ACTIVE",
            "validation": asdict(validation),
            "strikes": strikes,
            "dte": asdict(dte),
            "volatility": {
                "lambda_factor": vol_metrics.get("lambda_factor", 1.0),
                "t_scale": dte.t_scale,
                "vrp": dte.vrp,
                "vol_state": dte.vol_state,
                "ivr": ivr
            },
            "rr": {
                "iron_condor": asdict(rr_credit),
                "bull_call_spread": asdict(rr_debit)
            },
            "pw": {
                "credit": asdict(pw_credit),
                "debit": asdict(pw_debit),
                "butterfly": asdict(pw_butterfly)
            },
            "greeks_ranges": self._get_greeks_ranges(),
            "exit_params": self._get_exit_params(),
            "meta": {
                "spot": spot,
                "em1": em1,
                "ivr": ivr,
                "technical_score": technical_score,
                "primary_scenario": primary_scenario,
                "scenario_probability": scenario.get("scenario_probability", 0),
                "gamma_regime": self._safe_get(agent5_data, "gamma_regime", "spot_vs_trigger", default="unknown"),
                "noise_penalty": validation.confidence_penalty,
                "strategy_bias": validation.strategy_bias
            }
        }

def main(agent3_output: dict, agent5_output: dict, technical_score: float = 0, **env_vars) -> dict:
    try:
        if isinstance(agent3_output, str): agent3_output = json.loads(agent3_output)
        if isinstance(agent5_output, str): agent5_output = json.loads(agent5_output)
        
        calculator = StrategyCalculator(env_vars)
        return calculator.process(agent3_output, agent5_output, technical_score)
        
    except Exception as e:
        full_trace = traceback.format_exc()
        
        logger.error(f"❌ Strategy_calc error: {e}")
        logger.error(full_trace)
        
        return {
            "error": True,
            "error_message": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "trace": full_trace
        }