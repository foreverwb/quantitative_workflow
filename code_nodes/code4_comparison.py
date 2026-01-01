"""
Code 4: 策略对比引擎 (v3.8 - Logic Aligned)
特性:
1. [Alignment] 对齐 Agent 6 的 'setup_quality' 评价体系
2. [Scoring] 引入 Flow-Based 加分机制
3. [Filtering] 对 'Low' 质量策略实施降权打击
"""
import json
import traceback
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from loguru import logger
from utils.config_loader import config

# ==========================================
# 数据结构定义
# ==========================================

@dataclass
class QualityFilter:
    filters_triggered: List[str] = field(default_factory=list)
    total_penalty: float = 0.0
    overall_confidence: float = 1.0
    weekly_friction_state: str = "Clear"
    is_vetoed: bool = False
    strategy_bias: str = "Neutral"

# ==========================================
# 核心逻辑引擎
# ==========================================

class ComparisonEngine:
    def __init__(self, env_vars: Dict):
        scoring_conf = getattr(config, 'scoring', {})
        self.cfg = {
            'WEEKLY_RESISTANCE_PENALTY': 20, 
            'BIAS_MISMATCH_PENALTY': 15,
            'VETO_DIRECTIONAL_ZERO': True,
            
            # [新增] 质量加分权重
            'SCORE_QUALITY_HIGH': 15.0,
            'SCORE_QUALITY_MEDIUM': 5.0,
            'SCORE_FLOW_ALIGNED': 10.0,
            'PENALTY_QUALITY_LOW': -30.0
        }
        if isinstance(scoring_conf, dict):
            self.cfg.update(scoring_conf)
    
    def process(self, strategies_data: Any, scenario_data: Any, agent3_data: Any) -> Dict:
        """核心处理流程"""
        strategies = self._extract_strategies_list(strategies_data)
        
        if not strategies:
            logger.warning("[Code 4] 未检测到有效策略，跳过评分步骤")
            return {
                "ranking": [],
                "quality_filter": asdict(QualityFilter()),
                "message": "No strategies provided by upstream",
                "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        agent3_data = agent3_data or {}
        scenario_data = scenario_data or {}
        
        meta = agent3_data.get("meta", {})
        spot = meta.get("spot", 0) or agent3_data.get("targets", {}).get("spot_price", 0)
        em1 = meta.get("em1", 0)
        
        scenario_class = scenario_data.get("scenario_classification", {})
        primary_scenario = scenario_class.get("primary_scenario", "Unknown")
        scenario_prob = scenario_class.get("scenario_probability", 0)
        
        validation = agent3_data.get("validation", {})
        
        quality_filter = self._process_quality_filter(validation)
        ranked = self._rank_strategies(
            strategies, primary_scenario, scenario_prob, 
            spot, em1, quality_filter
        )
        
        return {
            "symbol": agent3_data.get("symbol", "UNKNOWN"),
            "quality_filter": asdict(quality_filter),
            "ranking": ranked,
            "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_strategies": len(strategies),
            "top1_score": ranked[0]["composite_score"] if ranked else 0
        }

    def _extract_strategies_list(self, data: Any) -> List[Dict]:
        """智能提取策略列表"""
        if not data: return []
        if isinstance(data, list): return data
        if isinstance(data, dict):
            if "strategies" in data and isinstance(data["strategies"], list):
                return data["strategies"]
            if "raw" in data and isinstance(data["raw"], str):
                try:
                    raw_str = data["raw"].strip()
                    if raw_str.startswith("```"):
                        lines = raw_str.split('\n')
                        if lines[0].startswith("```"): lines = lines[1:]
                        if lines[-1].startswith("```"): lines = lines[:-1]
                        raw_str = "\n".join(lines)
                    parsed = json.loads(raw_str)
                    if isinstance(parsed, dict) and "strategies" in parsed:
                        return parsed["strategies"]
                except Exception: pass
        return []

    def _process_quality_filter(self, validation: Dict) -> QualityFilter:
        qf = QualityFilter()
        if not validation: return qf
        
        friction = validation.get("weekly_friction_state", "Clear")
        qf.weekly_friction_state = friction
        
        if friction == "Obstructed":
            qf.filters_triggered.append("WEEKLY_RESISTANCE")
            qf.total_penalty += self.cfg['WEEKLY_RESISTANCE_PENALTY']
            
        if validation.get("is_vetoed"):
            qf.filters_triggered.append("VOLUME_DIVERGENCE")
            qf.is_vetoed = True
            
        qf.strategy_bias = validation.get("strategy_bias", "Neutral")
        return qf

    def _rank_strategies(self, strategies: List[dict], primary_scenario: str,
                         scenario_prob: int, spot: float, em1: float,
                         quality_filter: QualityFilter) -> List[dict]:
        ranked = []
        for strat in strategies:
            try:
                # 1. 基础计算
                metrics = self._calc_base_metrics(strat)
                
                # 2. 质量过滤 (Penalty)
                adj, notes = self._apply_quality_filter(strat, quality_filter, metrics)
                
                # 3. [新增] 智能加分 (Bonus)
                bonus, quality_notes = self._apply_intelligence_bonus(strat)
                
                metrics["quality_adjustment"] = adj + bonus
                metrics["quality_notes"] = notes + quality_notes
                metrics["composite_score"] = max(0, metrics["composite_score"] + adj + bonus)
                
                metrics["strategy_detail"] = strat
                ranked.append(metrics)
            except Exception as e:
                logger.error(f"策略评分出错: {e}")
                continue
        
        ranked.sort(key=lambda x: x["composite_score"], reverse=True)
        for i, item in enumerate(ranked):
            item["rank"] = i + 1
            
        return ranked

    def _calc_base_metrics(self, strategy: dict) -> dict:
        """计算基础得分 (R/R, WinRate, EV)"""
        metrics = {
            "strategy_name": strategy.get("name") or strategy.get("strategy_name", "Unknown"),
            "strategy_type": strategy.get("structure_type", ""),
            "ev": 0.0,
            "rar": 0.0,
            "composite_score": 50.0, # 基础分
            "quality_adjustment": 0.0,
            "quality_notes": []
        }
        
        quant = strategy.get("quant_metrics", {})
        if not quant: return metrics
        
        # 1. 盈亏比
        try:
            rr_val = 0.0
            rr_raw = quant.get("rr_ratio", 0)
            if isinstance(rr_raw, (int, float)):
                rr_val = float(rr_raw)
            metrics["rar"] = rr_val
            if rr_val > 0:
                metrics["composite_score"] += min(rr_val * 10, 30)
        except: pass
        
        # 2. 胜率
        try:
            pw_val = 50.0
            pw_raw = quant.get("pw_estimate", "50%")
            if isinstance(pw_raw, (int, float)):
                pw_val = float(pw_raw) * 100 if float(pw_raw) < 1 else float(pw_raw)
            if pw_val > 50:
                metrics["composite_score"] += (pw_val - 50) * 0.5
        except: pass
        
        return metrics

    def _apply_quality_filter(self, strategy: dict, qf: QualityFilter, metrics: dict):
        adj = 0.0
        notes = []
        if qf.is_vetoed:
            adj -= 50
            notes.append("🚫 触发一票否决 (Vetoed)")
        return adj, notes

    def _apply_intelligence_bonus(self, strategy: dict):
        """[新增] 应用 Agent 6 的智能评分"""
        bonus = 0.0
        notes = []
        
        # 1. Setup Quality
        quality = strategy.get("setup_quality", "Medium")
        if quality == "High":
            bonus += self.cfg['SCORE_QUALITY_HIGH']
            notes.append("⭐ High Quality Setup")
        elif quality == "Low":
            bonus += self.cfg['PENALTY_QUALITY_LOW']
            notes.append("⚠️ Low Quality Setup")
            
        # 2. Flow Alignment
        aligned = strategy.get("flow_aligned", False)
        if aligned:
            bonus += self.cfg['SCORE_FLOW_ALIGNED']
            notes.append("🌊 Flow Aligned")
            
        # 3. Blueprint Bonus
        src = strategy.get("source_blueprint", "")
        if src and "MANUAL" not in src.upper():
            bonus += 5.0
            notes.append("📜 Blueprint Executed")
            
        return bonus, notes

# ==========================================
# 主入口
# ==========================================

def main(**kwargs) -> Dict:
    try:
        strategies_in = kwargs.get("strategies_output") or kwargs.get("agent6_output") or kwargs.get("strategies_result")
        scenario_in = kwargs.get("scenario_output") or kwargs.get("agent5_output") or kwargs.get("scenario_result")
        agent3_in = kwargs.get("agent3_output") or kwargs.get("calculated_data")
        
        def _ensure_dict(d):
            if isinstance(d, str):
                try: return json.loads(d)
                except: return {}
            return d if isinstance(d, dict) else {}

        strategies_in = _ensure_dict(strategies_in)
        scenario_in = _ensure_dict(scenario_in)
        agent3_in = _ensure_dict(agent3_in)

        engine = ComparisonEngine(kwargs)
        result = engine.process(strategies_in, scenario_in, agent3_in)
        
        return result

    except Exception as e:
        error_msg = f"Code 4 Critical Error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {"ranking": [], "error": True, "message": error_msg}