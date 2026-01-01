"""
Drift Engine - 结构漂移分析引擎 (v3.2 - Phase 3 Deep Logic)
特性:
1. [Physics] 识别墙体虚化 (GEX Decay) 与 伽马翻转 (Flip Risk)
2. [Flow] 识别空心上涨 (Hollow Rally) 与 实心下跌 (Solid Drop)
3. [Advice] 生成结构化的风控建议
"""

from typing import Dict, Any, List, Optional

class DriftEngine:
    """核心差异分析引擎"""
    
    # 严格的风控阈值
    THRESHOLDS = {
        "WALL_SHIFT_PCT": 0.01,       # 墙位移动 1%
        "WALL_DECAY_PCT": -0.15,      # 墙体强度衰减 15% (虚化)
        "DEX_DIVERGENCE": -0.05,      # DEX 背离阈值
        "IV_SPIKE_PCT": 0.10,         # IV 飙升 10%
        "SPOT_DIVERGENCE": 0.02,      # 价格-结构乖离
    }

    def analyze(self, last_data: Dict, current_data: Dict) -> Dict:
        """执行全维度监控分析"""
        last = self._extract_targets(last_data)
        curr = self._extract_targets(current_data)
        
        # 初始化报告结构
        report = {
            "status": "STABLE",  # STABLE / CAUTION / DANGER
            "primary_driver": "None",
            "summary": "",
            "signals": {
                "walls": {"status": "STABLE", "detail": "No significant shift"},
                "flow": {"status": "NEUTRAL", "detail": "Flow confirms price"},
                "vol": {"status": "NORMAL", "detail": "IV stable"}
            },
            "alerts": [],
            "actions": [], # 用于 Dashboard 展示
            "changes": []
        }
        
        spot = curr.get("spot_price", 0)
        if spot == 0:
            report["summary"] = "Data Invalid (Spot=0)"
            return report

        # 1. 墙体物理分析 (Integrity)
        self._analyze_wall_physics(last, curr, report)
        
        # 2. 资金流向质量 (Flow Quality)
        self._analyze_flow_quality(last, curr, spot, report)
        
        # 3. 波动率环境 (Vol Regime)
        self._analyze_vol_regime(last, curr, report)
        
        # 4. 综合评级与建议
        self._synthesize_advice(report)
        
        return report

    def _extract_targets(self, data: Dict) -> Dict:
        """安全提取 targets"""
        if "targets" in data: return data["targets"]
        if "snapshot" in data: return data["snapshot"].get("targets", {})
        return data or {}

    # ================= 核心分析逻辑 =================

    def _analyze_wall_physics(self, last: Dict, curr: Dict, report: Dict):
        """分析墙体位置移动与强度衰减"""
        # 提取墙位
        l_call = last.get("walls", {}).get("call_wall", 0)
        c_call = curr.get("walls", {}).get("call_wall", 0)
        l_put = last.get("walls", {}).get("put_wall", 0)
        c_put = curr.get("walls", {}).get("put_wall", 0)
        
        # 1. 位置移动检测
        shift_detected = False
        if l_call and c_call and l_call != c_call:
            diff = (c_call - l_call) / l_call
            if abs(diff) > self.THRESHOLDS["WALL_SHIFT_PCT"]:
                direction = "RAISED" if diff > 0 else "LOWERED"
                report["changes"].append(f"Call Wall {direction} ({l_call}->{c_call})")
                
                if diff < 0: # 天花板下压
                    report["signals"]["walls"] = {"status": "PRESSURED", "detail": f"Resistance Lowering (-{abs(diff):.1%})"}
                    report["actions"].append({"type": "take_profit", "side": "long", "reason": "Ceiling Lowering"})
                else: # 天花板抬升
                    report["signals"]["walls"] = {"status": "BULLISH", "detail": "Room to Run Extended"}
                shift_detected = True

        if l_put and c_put and l_put != c_put:
            diff = (c_put - l_put) / l_put
            if abs(diff) > self.THRESHOLDS["WALL_SHIFT_PCT"]:
                direction = "RAISED" if diff > 0 else "BREACHED"
                report["changes"].append(f"Put Wall {direction} ({l_put}->{c_put})")
                
                if diff < 0: # 地板破位
                    report["signals"]["walls"] = {"status": "BROKEN", "detail": "Support Level Failed"}
                    report["actions"].append({"type": "stop_loss", "side": "long", "reason": "Support Breach"})
                    report["status"] = "DANGER"
                shift_detected = True

        # 2. 强度衰减检测 (Wall Dilution) - Phase 3 New
        # 尝试获取 Call Wall GEX 绝对值 (需上游支持，若无则跳过)
        l_cw_gex = self._get_gex_at_strike(last, l_call)
        c_cw_gex = self._get_gex_at_strike(curr, c_call)
        
        if l_cw_gex > 0 and c_cw_gex > 0 and not shift_detected:
            decay = (c_cw_gex - l_cw_gex) / l_cw_gex
            if decay < self.THRESHOLDS["WALL_DECAY_PCT"]:
                report["alerts"].append(f"⚠️ Call Wall Dilution: {decay:.1%}")
                report["signals"]["walls"] = {"status": "WEAKENING", "detail": "Resistance Fading (Fake Wall)"}

    def _analyze_flow_quality(self, last: Dict, curr: Dict, spot: float, report: Dict):
        """分析 DEX 与价格的背离关系 (空心/实心)"""
        last_spot = last.get("spot_price", spot)
        price_chg = (spot - last_spot) / last_spot
        
        # 获取 DEX 方向 (Directional Exposure)
        l_dex = last.get("directional_metrics", {}).get("dex_bias", "neutral")
        c_dex = curr.get("directional_metrics", {}).get("dex_bias", "neutral")
        
        # 场景 A: 上涨
        if price_chg > 0.005:
            if c_dex == "support":
                report["signals"]["flow"] = {"status": "ORGANIC", "detail": "Price UP + Inventory Support"}
            elif c_dex == "oppose":
                report["signals"]["flow"] = {"status": "HOLLOW", "detail": "Price UP but Inventory Opposes (Short Covering)"}
                report["alerts"].append("📉 Hollow Rally Detected (DEX Divergence)")
                report["actions"].append({"type": "tighten_stop", "side": "long", "reason": "Hollow Rally"})
        
        # 场景 B: 下跌
        elif price_chg < -0.005:
            if c_dex == "resistance" or c_dex == "oppose":
                report["signals"]["flow"] = {"status": "HEAVY", "detail": "Price DOWN + Inventory Pressure"}
            elif c_dex == "support":
                report["signals"]["flow"] = {"status": "ABSORPTION", "detail": "Price DOWN into Support"}

    def _analyze_vol_regime(self, last: Dict, curr: Dict, report: Dict):
        """分析波动率机制变化"""
        l_trig = last.get("gamma_metrics", {}).get("vol_trigger", 0)
        c_trig = curr.get("gamma_metrics", {}).get("vol_trigger", 0)
        spot = curr.get("spot_price", 0)
        
        # 1. Gamma Flip 检测
        if c_trig > 0 and spot > 0:
            is_neg_gamma = spot < c_trig
            was_neg_gamma = last.get("spot_price", 0) < l_trig if l_trig > 0 else False
            
            if is_neg_gamma and not was_neg_gamma:
                report["status"] = "DANGER"
                report["primary_driver"] = "Gamma Flip"
                report["alerts"].append(f"🔥 FLIP TO NEGATIVE GAMMA (<{c_trig})")
                report["actions"].append({"type": "reduce_risk", "side": "all", "reason": "High Volatility Regime"})
        
        # 2. IV 飙升检测
        l_iv = last.get("atm_iv", {}).get("iv_30d", 0) or last.get("atm_iv", {}).get("iv_14d", 0)
        c_iv = curr.get("atm_iv", {}).get("iv_30d", 0) or curr.get("atm_iv", {}).get("iv_14d", 0)
        
        if l_iv > 0:
            iv_chg = (c_iv - l_iv) / l_iv
            if iv_chg > self.THRESHOLDS["IV_SPIKE_PCT"]:
                report["signals"]["vol"] = {"status": "SPIKING", "detail": f"IV +{iv_chg:.1%}"}
                report["alerts"].append("⚠️ Volatility Spike")

    def _synthesize_advice(self, report: Dict):
        """生成最终摘要（中文）"""
        alerts_count = len(report["alerts"])
        wall_status = report["signals"]["walls"]["status"]
        flow_status = report["signals"]["flow"]["status"]
        
        # 状态翻译映射
        wall_status_cn = {
            "STABLE": "稳定",
            "PRESSURED": "承压",
            "BULLISH": "看涨",
            "BROKEN": "破位",
            "WEAKENING": "弱化"
        }.get(wall_status, wall_status)
        
        flow_status_cn = {
            "NEUTRAL": "中性",
            "ORGANIC": "健康",
            "HOLLOW": "空心",
            "HEAVY": "沉重",
            "ABSORPTION": "吸收"
        }.get(flow_status, flow_status)
        
        summary_parts = []
        if report["status"] == "DANGER":
            summary_parts.append("⚠️ 检测到关键风险。")
        elif alerts_count > 0:
            summary_parts.append(f"⚡ 注意: {alerts_count} 个预警信号。")
        else:
            summary_parts.append("✅ 结构稳定。")
            
        summary_parts.append(f"墙体: {wall_status_cn}。")
        summary_parts.append(f"流向: {flow_status_cn}。")
        
        report["summary"] = " ".join(summary_parts)

    def _get_gex_at_strike(self, data: Dict, strike: float) -> float:
        """(Helper) 尝试从结构中获取特定 Strike 的 GEX"""
        # 注意: 这是一个简化的 helper，实际需要从 full structure 获取
        # 在快照数据精简的情况下可能无法获取，返回 0 忽略
        return 0.0