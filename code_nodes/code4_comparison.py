"""
Code 4: 策略对比引擎 (重构版)
变更:
1. 移除 0DTE 惩罚
2. 新增 WEEKLY_RESISTANCE 惩罚
"""
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from utils.config_loader import config
import json
import traceback

@dataclass
class StrategyMetrics:
    rank: int = 0
    strategy_type: str = ""
    ev: float = 0.0
    rar: float = 0.0
    composite_score: float = 0.0
    quality_adjustment: float = 0.0
    quality_notes: List[str] = field(default_factory=list)
    # ... 其他字段省略，保持原有

@dataclass
class QualityFilter:
    filters_triggered: List[str] = field(default_factory=list)
    total_penalty: float = 0.0
    overall_confidence: float = 1.0
    weekly_friction_state: str = "Clear" # 新增
    is_vetoed: bool = False
    strategy_bias: str = "Neutral"

@dataclass 
class ComparisonOutput:
    symbol: str
    quality_filter: QualityFilter
    ranking: List[dict]
    # ... 其他

class ComparisonEngine:
    def __init__(self, env_vars: Dict):
        self.scoring_conf = config.scoring
        self.cfg = {
            'WEEKLY_RESISTANCE_PENALTY': 20, # 摩擦惩罚
            'BIAS_MISMATCH_PENALTY': 15,
            'VETO_DIRECTIONAL_ZERO': True,
            # EV/RAR 阈值保持不变
            'EV_HIGH_THRESHOLD': 0.5, 'EV_MID_THRESHOLD': 0.2, 'EV_HIGH_SCORE': 40, 'EV_MID_SCORE': 30, 'EV_LOW_SCORE': 20,
            'RAR_HIGH_THRESHOLD': 0.3, 'RAR_MID_THRESHOLD': 0.15, 'RAR_LOW_THRESHOLD': 0.05, 'RAR_HIGH_SCORE': 30, 'RAR_MID_SCORE': 25, 'RAR_LOW_SCORE': 15,
            'SCENARIO_HIGH_SCORE': 20, 'SCENARIO_MID_SCORE': 10, 'LIQUIDITY_PASS_SCORE': 10,
            'MAX_LEGS': 4, 'MAX_STRIKE_DISTANCE_EM1': 3.0
        }
    
    def process(self, strategies_output: dict, scenario_output: dict, agent3_output: dict) -> dict:
        strategies = strategies_output.get("strategies", [])
        spot = agent3_output.get("meta", {}).get("spot", 0)
        em1 = agent3_output.get("meta", {}).get("em1", 0)
        symbol = agent3_output.get("symbol", "")
        
        scenario_class = scenario_output.get("scenario_classification", {})
        primary_scenario = scenario_class.get("primary_scenario", "")
        scenario_prob = scenario_class.get("scenario_probability", 0)
        
        validation = agent3_output.get("validation", {})
        quality_filter = self._process_quality_filter(validation)
        
        ranked = self._rank_strategies(
            strategies, primary_scenario, scenario_prob, 
            spot, em1, quality_filter, validation
        )
        
        top3 = ranked[:3] # 简化
        
        return {
            "symbol": symbol,
            "quality_filter": asdict(quality_filter),
            "ranking": ranked,
            "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_strategies": len(strategies),
            "positive_ev_count": sum(1 for r in ranked if r.get("ev", 0) > 0),
            "top3": top3
        }
    
    def _process_quality_filter(self, validation: Dict) -> QualityFilter:
        qf = QualityFilter()
        
        # 1. 周度摩擦
        friction = validation.get("weekly_friction_state", "Clear")
        qf.weekly_friction_state = friction
        if friction == "Obstructed":
            qf.filters_triggered.append("WEEKLY_RESISTANCE")
            qf.total_penalty += self.cfg['WEEKLY_RESISTANCE_PENALTY']
            
        # 2. 量价背离
        if validation.get("is_vetoed"):
            qf.filters_triggered.append("VOLUME_DIVERGENCE")
            qf.is_vetoed = True
            
        qf.strategy_bias = validation.get("strategy_bias", "Neutral")
        qf.overall_confidence = 1.0 # 简化
        
        return qf
    
    def _rank_strategies(self, strategies: List[dict], primary_scenario: str,
                         scenario_prob: int, spot: float, em1: float,
                         quality_filter: QualityFilter, validation: Dict) -> List[dict]:
        ranked = []
        for strategy in strategies:
            metrics = self._calc_base_metrics(strategy, primary_scenario, scenario_prob, spot, em1)
            quality_adj, quality_notes = self._apply_quality_filter(strategy, quality_filter, metrics)
            metrics["quality_adjustment"] = quality_adj
            metrics["quality_notes"] = quality_notes
            metrics["composite_score"] += quality_adj
            metrics["composite_score"] = max(0, metrics["composite_score"])
            ranked.append(metrics)
        
        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        for i, item in enumerate(ranked):
            item["rank"] = i + 1
        return ranked

    def _calc_base_metrics(self, strategy: dict, primary_scenario: str, scenario_prob: int, spot: float, em1: float) -> dict:
        # ... (EV, RAR 计算逻辑保持不变)
        # 为节省篇幅，此处省略具体计算，请保留原有逻辑
        return {"ev": 0, "rar": 0, "composite_score": 50} # 占位

    def _apply_quality_filter(self, strategy: dict, qf: QualityFilter, metrics: dict) -> Tuple[float, List[str]]:
        cfg = self.cfg
        adjustment = 0.0
        notes = []
        
        # 1. 量价背离
        strategy_type = strategy.get("strategy_type", "")
        is_directional = "bull" in strategy_type.lower() or "bear" in strategy_type.lower()
        if qf.is_vetoed and is_directional and cfg['VETO_DIRECTIONAL_ZERO']:
            adjustment = -metrics["composite_score"]
            notes.append("⛔ 量价背离，方向策略禁用")
            
        # 2. 周度摩擦
        if "WEEKLY_RESISTANCE" in qf.filters_triggered and is_directional:
            adjustment -= cfg['WEEKLY_RESISTANCE_PENALTY']
            notes.append("⚠️ 周度阻力位压制，方向策略降权")
            
        # 3. 偏好不匹配
        is_credit = "credit" in strategy_type.lower() or "condor" in strategy_type.lower()
        is_debit = "debit" in strategy_type.lower() or "spread" in strategy_type.lower()
        
        if qf.strategy_bias == "Credit_Favored" and is_debit:
            adjustment -= cfg['BIAS_MISMATCH_PENALTY']
            notes.append("偏好Credit但选择Debit")
        elif qf.strategy_bias == "Debit_Favored" and is_credit:
            adjustment -= cfg['BIAS_MISMATCH_PENALTY']
            notes.append("偏好Debit但选择Credit")
            
        return adjustment, notes

def main(strategies_output: dict, scenario_output: dict, agent3_output: dict, **env_vars) -> dict:
    try:
        # 解析逻辑保持不变
        if isinstance(strategies_output, str): strategies_output = json.loads(strategies_output)
        if isinstance(scenario_output, str): scenario_output = json.loads(scenario_output)
        if isinstance(agent3_output, str): agent3_output = json.loads(agent3_output)
        
        engine = ComparisonEngine(env_vars)
        return engine.process(strategies_output, scenario_output, agent3_output)
    except Exception as e:
        
        return {
        "result": json.dumps({
            "error": True,
            "message": str(e),
            "trace": traceback.format_exc()
        }, ensure_ascii=False, indent=2)
    }