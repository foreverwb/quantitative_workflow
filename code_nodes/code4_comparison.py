"""
Code 4: 策略对比引擎 (重构版)

变更:
1. 使用 @dataclass 定义输出结构
2. 配置常量集中管理
3. 嵌套输出替代扁平化
4. 集成 validation_flags 质量过滤
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ============= 数据类定义 =============

@dataclass
class StrategyMetrics:
    """单个策略的评估指标"""
    rank: int = 0
    strategy_type: str = ""
    structure: str = ""
    ev: float = 0.0
    rar: float = 0.0
    pw: float = 0.5
    scenario_match: str = "低"
    match_reason: str = ""
    liquidity_pass: bool = True
    liquidity_note: str = ""
    composite_score: float = 0.0
    quality_adjustment: float = 0.0  # 质量过滤调整分
    quality_notes: List[str] = field(default_factory=list)


@dataclass
class QualityFilter:
    """质量过滤结果"""
    filters_triggered: List[str] = field(default_factory=list)
    total_penalty: float = 0.0
    overall_confidence: float = 1.0
    zero_dte_ratio: Optional[float] = None
    is_vetoed: bool = False
    strategy_bias: str = "Neutral"


@dataclass 
class ComparisonOutput:
    """对比引擎完整输出"""
    symbol: str
    total_strategies: int
    positive_ev_count: int
    analysis_timestamp: str
    quality_filter: QualityFilter
    top3: List[StrategyMetrics]
    ranking: List[dict]


# ============= 配置常量 =============

DEFAULT_CONFIG = {
    # 评分权重 (总计 100)
    'WEIGHT_EV': 40,
    'WEIGHT_RAR': 30,
    'WEIGHT_SCENARIO': 20,
    'WEIGHT_LIQUIDITY': 10,
    
    # EV 阈值与得分
    'EV_HIGH_THRESHOLD': 0.5,
    'EV_MID_THRESHOLD': 0.2,
    'EV_HIGH_SCORE': 40,
    'EV_MID_SCORE': 30,
    'EV_LOW_SCORE': 20,
    
    # RAR 阈值与得分
    'RAR_HIGH_THRESHOLD': 0.3,
    'RAR_MID_THRESHOLD': 0.15,
    'RAR_LOW_THRESHOLD': 0.05,
    'RAR_HIGH_SCORE': 30,
    'RAR_MID_SCORE': 25,
    'RAR_LOW_SCORE': 15,
    
    # 剧本匹配得分
    'SCENARIO_HIGH_SCORE': 20,
    'SCENARIO_MID_SCORE': 10,
    
    # 流动性得分
    'LIQUIDITY_PASS_SCORE': 10,
    
    # 流动性检查
    'MAX_LEGS': 4,
    'MAX_STRIKE_DISTANCE_EM1': 3.0,
    
    # 质量过滤惩罚
    'ZERO_DTE_HIGH_PENALTY': 20,      # 0DTE > 50%
    'ZERO_DTE_MID_PENALTY': 10,       # 0DTE > 30%
    'BIAS_MISMATCH_PENALTY': 15,      # 策略偏好不匹配
    'VETO_DIRECTIONAL_ZERO': True,    # 量价背离时方向策略归零
}


# ============= 主入口函数 =============

def main(strategies_output: dict, scenario_output: dict, 
         agent3_output: dict, **env_vars) -> dict:
    """
    Code 4 主入口
    
    Args:
        strategies_output: Agent 6 策略列表
        scenario_output: Agent 5 场景分析 (或 Code 3 输出)
        agent3_output: Agent 3 / Code 3 数据
        
    Returns:
        dict - 策略对比结果
    """
    try:
        engine = ComparisonEngine(env_vars)
        return engine.process(strategies_output, scenario_output, agent3_output)
    except Exception as e:
        import traceback
        return {
            "error": True,
            "message": str(e),
            "traceback": traceback.format_exc()
        }


# ============= 对比引擎 =============

class ComparisonEngine:
    """策略对比引擎 (重构版)"""
    
    def __init__(self, env_vars: Dict):
        self.cfg = self._merge_config(env_vars)
    
    def _merge_config(self, env_vars: Dict) -> Dict:
        """合并配置"""
        merged = {}
        for key, default in DEFAULT_CONFIG.items():
            val = env_vars.get(key, default)
            merged[key] = val if val is not None else default
        return merged
    
    # ------------- 主处理流程 -------------
    
    def process(self, strategies_output: dict, scenario_output: dict, 
                agent3_output: dict) -> dict:
        """主处理流程"""
        # 提取输入
        strategies = strategies_output.get("strategies", [])
        spot = agent3_output.get("spot_price", 0) or agent3_output.get("meta", {}).get("spot", 0)
        em1 = agent3_output.get("em1_dollar", 0) or agent3_output.get("meta", {}).get("em1", 0)
        symbol = agent3_output.get("symbol", "")
        
        # 场景信息 (兼容 agent5 和 code3 格式)
        scenario_class = scenario_output.get("scenario_classification", {})
        if not scenario_class:
            scenario_class = {
                "primary_scenario": scenario_output.get("meta", {}).get("primary_scenario", ""),
                "scenario_probability": scenario_output.get("meta", {}).get("scenario_probability", 0)
            }
        primary_scenario = scenario_class.get("primary_scenario", "")
        scenario_prob = scenario_class.get("scenario_probability", 0)
        
        # 提取 validation_flags (来自 code3)
        validation = agent3_output.get("validation", {})
        quality_filter = self._process_quality_filter(validation)
        
        # 排序策略
        ranked = self._rank_strategies(
            strategies, primary_scenario, scenario_prob, 
            spot, em1, quality_filter, validation
        )
        
        # 提取 Top 3
        top3 = [self._extract_metrics(r, i+1) for i, r in enumerate(ranked[:3])]
        
        # 组装输出
        return {
            "symbol": symbol,
            "total_strategies": len(strategies),
            "positive_ev_count": sum(1 for r in ranked if r.get("ev", 0) > 0),
            "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quality_filter": asdict(quality_filter),
            "top3": [asdict(m) for m in top3],
            "ranking": ranked
        }
    
    # ------------- 质量过滤 -------------
    
    def _process_quality_filter(self, validation: Dict) -> QualityFilter:
        """处理质量过滤"""
        qf = QualityFilter()
        
        zero_dte = validation.get("zero_dte_ratio")
        is_vetoed = validation.get("is_vetoed", False)
        strategy_bias = validation.get("strategy_bias", "Neutral")
        
        qf.zero_dte_ratio = zero_dte
        qf.is_vetoed = is_vetoed
        qf.strategy_bias = strategy_bias
        
        # 0DTE 噪音
        if zero_dte is not None:
            if zero_dte > 0.5:
                qf.filters_triggered.append("0DTE_HIGH")
                qf.total_penalty += self.cfg['ZERO_DTE_HIGH_PENALTY']
            elif zero_dte > 0.3:
                qf.filters_triggered.append("0DTE_MID")
                qf.total_penalty += self.cfg['ZERO_DTE_MID_PENALTY']
        
        # 量价背离
        if is_vetoed:
            qf.filters_triggered.append("VOLUME_DIVERGENCE")
        
        # 计算整体置信度
        confidence_penalty = validation.get("confidence_penalty", 0)
        qf.overall_confidence = 1.0 - confidence_penalty
        
        return qf
    
    # ------------- 策略排序 -------------
    
    def _rank_strategies(self, strategies: List[dict], primary_scenario: str,
                         scenario_prob: int, spot: float, em1: float,
                         quality_filter: QualityFilter, validation: Dict) -> List[dict]:
        """策略排序"""
        ranked = []
        
        for strategy in strategies:
            # 基础指标计算
            metrics = self._calc_base_metrics(strategy, primary_scenario, scenario_prob, spot, em1)
            
            # 应用质量过滤
            quality_adj, quality_notes = self._apply_quality_filter(
                strategy, quality_filter, validation, metrics
            )
            metrics["quality_adjustment"] = quality_adj
            metrics["quality_notes"] = quality_notes
            metrics["composite_score"] += quality_adj
            
            # 确保分数不为负
            metrics["composite_score"] = max(0, metrics["composite_score"])
            
            ranked.append(metrics)
        
        # 排序
        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        for i, item in enumerate(ranked):
            item["rank"] = i + 1
        
        return ranked
    
    def _calc_base_metrics(self, strategy: dict, primary_scenario: str,
                           scenario_prob: int, spot: float, em1: float) -> dict:
        """计算基础指标"""
        cfg = self.cfg
        
        # 提取 RR 和 Pw
        rr = strategy.get("rr_calculation", {})
        pw_calc = strategy.get("pw_calculation", {})
        
        max_profit = rr.get("max_profit", 0)
        max_loss = rr.get("max_loss", 0)
        pw = self._parse_pw(pw_calc.get("pw_estimate", "50%"))
        
        # EV 和 RAR
        ev = pw * max_profit - (1 - pw) * max_loss
        rar = ev / max_loss if max_loss > 0 else 0
        
        # 剧本匹配
        strategy_type = strategy.get("strategy_type", "")
        scenario_match, match_reason = self._calc_scenario_match(
            strategy_type, primary_scenario, scenario_prob
        )
        
        # 流动性
        liquidity_pass, liquidity_note = self._check_liquidity(strategy, spot, em1)
        
        # 计算得分
        score = 0
        
        # EV 得分
        if ev > cfg['EV_HIGH_THRESHOLD']:
            score += cfg['EV_HIGH_SCORE']
        elif ev > cfg['EV_MID_THRESHOLD']:
            score += cfg['EV_MID_SCORE']
        elif ev > 0:
            score += cfg['EV_LOW_SCORE']
        
        # RAR 得分
        if rar > cfg['RAR_HIGH_THRESHOLD']:
            score += cfg['RAR_HIGH_SCORE']
        elif rar > cfg['RAR_MID_THRESHOLD']:
            score += cfg['RAR_MID_SCORE']
        elif rar > cfg['RAR_LOW_THRESHOLD']:
            score += cfg['RAR_LOW_SCORE']
        
        # 剧本匹配得分
        if scenario_match == "高":
            score += cfg['SCENARIO_HIGH_SCORE']
        elif scenario_match == "中":
            score += cfg['SCENARIO_MID_SCORE']
        
        # 流动性得分
        if liquidity_pass:
            score += cfg['LIQUIDITY_PASS_SCORE']
        
        return {
            "strategy": strategy,
            "ev": round(ev, 2),
            "rar": round(rar, 3),
            "pw": pw,
            "scenario_match": scenario_match,
            "match_reason": match_reason,
            "liquidity_pass": liquidity_pass,
            "liquidity_note": liquidity_note,
            "composite_score": score
        }
    
    def _apply_quality_filter(self, strategy: dict, qf: QualityFilter,
                               validation: Dict, metrics: dict) -> Tuple[float, List[str]]:
        """应用质量过滤，返回调整分和说明"""
        cfg = self.cfg
        adjustment = 0.0
        notes = []
        
        strategy_type = strategy.get("strategy_type", "")
        is_directional = any(kw in strategy_type.lower() for kw in 
                            ["call", "put", "bull", "bear", "long", "short"])
        is_credit = any(kw in strategy_type.lower() for kw in 
                       ["iron", "condor", "butterfly", "credit"])
        is_debit = any(kw in strategy_type.lower() for kw in 
                      ["debit", "straddle", "strangle"])
        
        # 1. 量价背离 - 方向策略归零
        if qf.is_vetoed and is_directional and cfg['VETO_DIRECTIONAL_ZERO']:
            adjustment = -metrics["composite_score"]  # 归零
            notes.append("⛔ 量价背离，方向策略禁用")
        
        # 2. 0DTE 噪音 - 短期策略扣分
        dte = strategy.get("dte", 0) or strategy.get("expiry_dte", 0)
        if "0DTE_HIGH" in qf.filters_triggered and dte and dte < 3:
            adjustment -= cfg['ZERO_DTE_HIGH_PENALTY']
            notes.append(f"⚠️ 0DTE噪音高，DTE={dte}短期策略风险大")
        elif "0DTE_MID" in qf.filters_triggered and dte and dte < 3:
            adjustment -= cfg['ZERO_DTE_MID_PENALTY']
            notes.append(f"⚠️ 0DTE中度噪音，DTE={dte}")
        
        # 3. 策略偏好不匹配
        bias = qf.strategy_bias
        if bias == "Credit_Favored" and is_debit:
            adjustment -= cfg['BIAS_MISMATCH_PENALTY']
            notes.append("策略偏好Credit，但选择了Debit策略")
        elif bias == "Debit_Favored" and is_credit:
            adjustment -= cfg['BIAS_MISMATCH_PENALTY']
            notes.append("策略偏好Debit，但选择了Credit策略")
        
        return adjustment, notes
    
    # ------------- 辅助方法 -------------
    
    def _parse_pw(self, pw_str: str) -> float:
        """解析胜率字符串"""
        if not pw_str:
            return 0.5
        try:
            # 处理 "约50%" 格式
            if "约" in pw_str:
                return 0.4
            # 处理 "50-60%" 范围格式
            if "-" in pw_str:
                parts = pw_str.replace("%", "").split("-")
                return (float(parts[0]) + float(parts[1])) / 200
            # 处理 "50%" 或 "0.5" 格式
            cleaned = pw_str.rstrip("%").strip()
            val = float(cleaned)
            return val / 100 if val > 1 else val
        except:
            return 0.5
    
    def _calc_scenario_match(self, strategy_type: str, primary_scenario: str,
                              scenario_prob: int) -> Tuple[str, str]:
        """计算剧本匹配度"""
        st = strategy_type.lower() if strategy_type else ""
        
        # 保守策略 (Iron Condor, Butterfly)
        if any(kw in st for kw in ["保守", "condor", "butterfly", "iron"]):
            if "区间" in primary_scenario and scenario_prob >= 60:
                return "高", f"区间剧本{scenario_prob}%，信用策略完美匹配"
            elif "区间" in primary_scenario:
                return "中", f"区间剧本{scenario_prob}%略低，但仍适配"
            else:
                return "低", f"趋势剧本{primary_scenario}，区间策略不适配"
        
        # 均衡策略 (Spread)
        if any(kw in st for kw in ["均衡", "spread", "vertical"]):
            if "趋势" in primary_scenario and scenario_prob >= 55:
                return "高", f"趋势剧本{scenario_prob}%，价差策略适配"
            elif "区间" in primary_scenario:
                return "中", "区间剧本下可获取部分方向收益"
            else:
                return "低", "剧本不明确，方向策略风险大"
        
        # 进取策略 (Long Call/Put, Straddle)
        if any(kw in st for kw in ["进取", "long call", "long put", "straddle"]):
            if "强趋势" in primary_scenario or scenario_prob >= 65:
                return "高", f"强确信场景{scenario_prob}%，单腿可最大化收益"
            elif "趋势" in primary_scenario:
                return "中", "趋势初期，单腿风险较大"
            else:
                return "低", "非趋势场景，单腿时间价值流失快"
        
        return "中", "通用策略"
    
    def _check_liquidity(self, strategy: dict, spot: float, em1: float) -> Tuple[bool, str]:
        """流动性检查"""
        cfg = self.cfg
        legs = strategy.get("legs", [])
        
        # 腿数检查
        if len(legs) > cfg['MAX_LEGS']:
            return False, f"腿部数量{len(legs)}过多，流动性风险高"
        
        # 行权价距离检查
        if em1 <= 0:
            return True, "EM1$数据缺失，跳过距离检查"
        
        for leg in legs:
            strike = leg.get("strike")
            if not isinstance(strike, (int, float)):
                continue
            
            distance = abs(strike - spot) / em1
            if distance > cfg['MAX_STRIKE_DISTANCE_EM1']:
                leg_type = leg.get("type", leg.get("option_type", ""))
                return False, f"{leg_type}@{strike} 距现价{distance:.1f}×EM1$，流动性不足"
        
        return True, "流动性达标"
    
    def _extract_metrics(self, ranked_item: dict, rank: int) -> StrategyMetrics:
        """从排序结果提取指标"""
        strategy = ranked_item.get("strategy", {})
        return StrategyMetrics(
            rank=rank,
            strategy_type=strategy.get("strategy_type", ""),
            structure=strategy.get("structure", ""),
            ev=ranked_item.get("ev", 0),
            rar=ranked_item.get("rar", 0),
            pw=ranked_item.get("pw", 0.5),
            scenario_match=ranked_item.get("scenario_match", ""),
            match_reason=ranked_item.get("match_reason", ""),
            liquidity_pass=ranked_item.get("liquidity_pass", True),
            liquidity_note=ranked_item.get("liquidity_note", ""),
            composite_score=ranked_item.get("composite_score", 0),
            quality_adjustment=ranked_item.get("quality_adjustment", 0),
            quality_notes=ranked_item.get("quality_notes", [])
        )