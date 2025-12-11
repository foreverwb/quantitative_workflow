"""
Drift Engine - 结构漂移分析引擎
职责：对比 T_n 与 T_n-1 数据，执行多维度风控检查，生成操作建议
"""

from typing import Dict, Any, List, Tuple

class DriftEngine:
    """
    核心差异分析引擎
    """
    
    # 定义严格的风控阈值
    THRESHOLDS = {
        "WALL_SHIFT_PCT": 0.01,       # 墙位移动 1%
        "FRICTION_DANGER": 0.005,     # 距离阻力 < 0.5%
        "DEX_DIVERGENCE": -0.05,      # DEX 缩水 5% 即视为背离警示
        "IV_INVERSION_RATIO": 1.05,   # 7D_IV / 30D_IV > 1.05 视为倒挂
        "IV_SPIKE_PCT": 0.10,         # IV 单日跳升 10%
        "WALL_DECAY_PCT": -0.20,      # 墙体强度衰减 20%
        "SPOT_DIVERGENCE": 0.02,      # 价格-结构乖离 2%
        "TERM_FLATTENING": 0.5        # 期限斜率平坦化阈值
    }

    def analyze(self, last_data: Dict, current_data: Dict) -> Dict:
        """
        执行全维度监控分析
        """
        # 提取标准化 Targets
        last = self._extract_targets(last_data)
        curr = self._extract_targets(current_data)
        
        report = {"changes": [], "alerts": [], "actions": [], "summary": ""}
        
        spot = curr.get("spot_price", 0)
        if spot == 0: 
            report["summary"] = "数据无效 (Spot=0)"
            return report

        # 1. 墙位漂移 (Wall Shift)
        self._check_wall_shift(last, curr, report)
        
        # 2. 零Gamma / Regime (Zero Gamma)
        self._check_gamma_regime(last, curr, spot, report)
        
        # 3. DEX 同向性 (Momentum)
        self._check_dex_momentum(last, curr, spot, report)
        
        # 4. Vanna & IV (Fuel)
        self._check_iv_flow(last, curr, report)
        
        # 5. Term 结构 (Macro)
        self._check_term_structure(curr, report)
        
        # 6. 墙体强度监控 (Wall Strength)
        self._check_wall_strength(last, curr, report)
        
        # 7. 价格-结构乖离 (Structure Divergence)
        self._check_structure_divergence(last, curr, spot, report)
        
        # 8. Term 斜率平坦化 (Slope Flattening)
        self._check_term_slope(curr, report)

        # 生成总结
        if not report["changes"] and not report["alerts"]:
            report["summary"] = "结构稳定，建议持有"
        else:
            act_cnt = len(report["actions"])
            report["summary"] = f"监控触发: {len(report['changes'])}变化, {len(report['alerts'])}警示 -> 生成{act_cnt}条建议"
            
        return report

    def _extract_targets(self, data: Dict) -> Dict:
        """安全提取 targets"""
        if "targets" in data: return data["targets"]
        if "snapshot" in data: return data["snapshot"].get("targets", {})
        return data

    # ================= 具体的监控逻辑实现 =================

    def _check_wall_shift(self, last: Dict, curr: Dict, report: Dict):
        """监控墙位移动"""
        l_call = last.get("walls", {}).get("call_wall", 0)
        c_call = curr.get("walls", {}).get("call_wall", 0)
        l_put = last.get("walls", {}).get("put_wall", 0)
        c_put = curr.get("walls", {}).get("put_wall", 0)
        
        if l_call and c_call and l_call != c_call:
            diff_pct = (c_call - l_call) / l_call
            if abs(diff_pct) > self.THRESHOLDS["WALL_SHIFT_PCT"]:
                dr = "上移" if diff_pct > 0 else "下压"
                report["changes"].append(f"Call Wall {dr}: {l_call}->{c_call}")
                if diff_pct < 0:
                    report["actions"].append({"type": "take_profit", "side": "long", "reason": f"天花板下压 ({diff_pct:.1%})"})
                else:
                    report["actions"].append({"type": "hold", "side": "long", "reason": "阻力位上移，趋势延续"})

        if l_put and c_put and l_put != c_put:
            diff_pct = (c_put - l_put) / l_put
            if abs(diff_pct) > self.THRESHOLDS["WALL_SHIFT_PCT"]:
                dr = "上抬" if diff_pct > 0 else "破位"
                report["changes"].append(f"Put Wall {dr}: {l_put}->{c_put}")
                if diff_pct < 0:
                    report["actions"].append({"type": "stop_loss", "side": "long", "reason": f"防线溃退 ({diff_pct:.1%})"})

    def _check_gamma_regime(self, last: Dict, curr: Dict, spot: float, report: Dict):
        """监控 Gamma Flip"""
        l_trig = last.get("gamma_metrics", {}).get("vol_trigger", 0)
        c_trig = curr.get("gamma_metrics", {}).get("vol_trigger", 0)
        
        if c_trig > 0:
            is_below = spot < c_trig
            was_below = last.get("spot_price", 0) < l_trig if l_trig > 0 else False
            
            if is_below and not was_below:
                report["alerts"].append(f"🔥 跌破 Vol Trigger ({c_trig})，进入负Gamma区")
                report["actions"].append({"type": "reduce_risk", "side": "all", "reason": "Regime Change (高波警报)"})
            elif not is_below and was_below:
                report["changes"].append("收复 Vol Trigger，回归正Gamma区")

    def _check_dex_momentum(self, last: Dict, curr: Dict, spot: float, report: Dict):
        """监控 DEX 动能背离"""
        l_dex = last.get("directional_metrics", {}).get("dex_same_dir_pct", 0)
        c_dex = curr.get("directional_metrics", {}).get("dex_same_dir_pct", 0)
        price_chg = (spot - last.get("spot_price", spot)) / spot
        
        # 价格涨 但 DEX 跌 -> 背离
        if price_chg > 0.005 and (c_dex - l_dex) < self.THRESHOLDS["DEX_DIVERGENCE"]:
            report["alerts"].append(f"📉 DEX 动能背离 (价涨量缩)")
            report["actions"].append({"type": "tighten_stop", "side": "long", "reason": "上涨缺乏Dealer库存支持"})

    def _check_iv_flow(self, last: Dict, curr: Dict, report: Dict):
        """监控 IV 异常跳升"""
        l_iv = last.get("atm_iv", {}).get("iv_30d", 0) or last.get("atm_iv", {}).get("iv_14d", 0)
        c_iv = curr.get("atm_iv", {}).get("iv_30d", 0) or curr.get("atm_iv", {}).get("iv_14d", 0)
        
        if l_iv > 0 and c_iv > 0:
            iv_chg = (c_iv - l_iv) / l_iv
            if iv_chg > self.THRESHOLDS["IV_SPIKE_PCT"]:
                report["alerts"].append(f"⚠️ IV 异常飙升 ({iv_chg:+.1%})")
                report["actions"].append({"type": "exit", "side": "vanna_long", "reason": "IV飙升破坏Vanna助涨逻辑"})

    def _check_term_structure(self, curr: Dict, report: Dict):
        """监控期限结构倒挂"""
        iv_7d = curr.get("atm_iv", {}).get("iv_7d", 0)
        iv_30d = curr.get("atm_iv", {}).get("iv_30d", 0) or curr.get("atm_iv", {}).get("iv_14d", 0)
        
        if iv_7d > 0 and iv_30d > 0:
            ratio = iv_7d / iv_30d
            if ratio > self.THRESHOLDS["IV_INVERSION_RATIO"]:
                report["alerts"].append(f"⛔ 期限结构倒挂 (Ratio: {ratio:.2f})")
                report["actions"].append({"type": "clear_position", "side": "all", "reason": "宏观恐慌 (Term Inversion)"})

    def _check_wall_strength(self, last: Dict, curr: Dict, report: Dict):
        """监控墙体强度衰减"""
        l_put_gex = last.get("gamma_metrics", {}).get("monthly_data", {}).get("cluster_strength", {}).get("abs_gex", 0)
        c_put_gex = curr.get("gamma_metrics", {}).get("monthly_data", {}).get("cluster_strength", {}).get("abs_gex", 0)
        
        if l_put_gex > 0:
            gex_decay = (c_put_gex - l_put_gex) / l_put_gex
            if gex_decay < self.THRESHOLDS["WALL_DECAY_PCT"]:
                report["alerts"].append(f"⚠️ Put Wall 强度衰减 {gex_decay:.1%} (支撑虚化)")
                report["actions"].append({"type": "tighten_stop", "side": "long", "reason": "主力防守资金撤退"})

    def _check_structure_divergence(self, last: Dict, curr: Dict, spot: float, report: Dict):
        """监控价格-结构乖离"""
        w_peak_price = curr.get("gamma_metrics", {}).get("weekly_data", {}).get("cluster_strength", {}).get("price", 0)
        
        if spot > 0 and w_peak_price > 0:
            divergence = (spot - w_peak_price) / spot
            if divergence > self.THRESHOLDS["SPOT_DIVERGENCE"]:
                report["changes"].append(f"价格乖离: 领先结构 {divergence:.1%}")
                
                l_w_peak = last.get("gamma_metrics", {}).get("weekly_data", {}).get("cluster_strength", {}).get("price", 0)
                if w_peak_price == l_w_peak: 
                    report["alerts"].append("📉 上涨空心化 (价格涨但GEX结构未跟进)")
                    report["actions"].append({"type": "take_profit", "side": "long", "reason": "结构滞后，防范均值回归"})

    def _check_term_slope(self, curr: Dict, report: Dict):
        """监控期限斜率平坦化"""
        iv_7d = curr.get("atm_iv", {}).get("iv_7d", 0)
        iv_30d = curr.get("atm_iv", {}).get("iv_30d", 0) or curr.get("atm_iv", {}).get("iv_14d", 0)
        
        if iv_7d > 0 and iv_30d > 0:
            slope = iv_30d - iv_7d
            if 0 < slope < self.THRESHOLDS["TERM_FLATTENING"]:
                report["alerts"].append(f"⚠️ Term结构平坦化 (Slope: {slope:.1f})")
                report["actions"].append({"type": "reduce_risk", "side": "all", "reason": "短期避险情绪升温"})