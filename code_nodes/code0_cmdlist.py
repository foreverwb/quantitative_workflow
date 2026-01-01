"""
Code Node 0: 命令清单生成器 (v3.6 - Phase 3 Logic Fix)
修复:
1. [Critical] 修正 !vexn 参数顺序 (!vexn symbol strikes exp dte)
2. [Critical] 修正 !volumen 和 !smile 的参数模板，防止位置参数错位
3. [Logic] 移除硬编码的 'w'/'m'，改为从动态参数中解析 expiration_filter
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class CommandGroup(Enum):
    """命令分组枚举"""
    CORE_STRUCTURE = "核心结构"
    FLOWS = "供需流向"
    VOLATILITY = "波动率锚点"
    IV_PATH = "IV Path & Validation"
    EXTENDED = "扩展命令"
    INDEX_BACKGROUND = "指数背景"

@dataclass
class CommandTemplate:
    """命令模板数据类"""
    group: CommandGroup
    description: str
    template: str
    order: int = 0
    enabled: bool = True
    condition: Optional[str] = None
    # 参数映射模式: 'short' (战术), 'mid' (战略), 'long' (宏观), 'window' (通用)
    param_mode: str = "window" 

# ============================================================
# 核心配置：命令模板列表 (严格对齐 cmd.md)
# ============================================================

COMMAND_TEMPLATES: List[CommandTemplate] = [
    # ========== 1. 核心结构 (Walls & Clusters) ==========
    CommandTemplate(
        group=CommandGroup.CORE_STRUCTURE,
        description="[战术视图] 捕捉近端摩擦与周度博弈 (Tactical Structure)",
        template="!gexr {symbol} {strikes} {dte} {exp}",
        order=1,
        param_mode="short"
    ),
    CommandTemplate(
        group=CommandGroup.CORE_STRUCTURE,
        description="[战略视图] 锁定机构核心仓位与磁力目标 (Strategic Structure)",
        template="!gexr {symbol} {strikes} {dte} {exp}",
        order=2,
        param_mode="mid"
    ),
    CommandTemplate(
        group=CommandGroup.CORE_STRUCTURE,
        description="[结构修正] Skew Adjusted GEX (真实对冲墙)",
        template="!gexs {symbol} {strikes} {dte}",
        order=3,
        param_mode="short"
    ),
    
    # ========== 2. 供需流向 (Flows) ==========
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="净Gamma与触发线 (全周期)",
        template="!gexn {symbol} {window} 98",
        order=10,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="Trigger Line",
        template="!trigger {symbol} {window}",
        order=11,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="[情绪锚点] Max Pain (震荡/低波场景参考)",
        template="!max {symbol}",
        order=12,
        condition="scenario in ['Grind', 'Range', 'Low Vol']",
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="Vanna Exposure (聚焦长期持仓对冲压力)",
        template="!vanna {symbol} ntm {window} {exp}",
        order=13,
        param_mode="mid"
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="Delta Exposure (与中期结构对齐)",
        template="!dexn {symbol} {strikes} {dte}",
        order=14,
        param_mode="mid"
    ),
    
    # ========== 3. 波动率锚点 (Volatility Anchors) ==========
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[物理锚点] 7日 Skew (用于 Raw_EM1$)",
        template="!skew {symbol} ivmid atm 7",
        order=20,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[物理锚点] 14日 Skew",
        template="!skew {symbol} ivmid atm 14",
        order=21,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[定价基准] 30日 Skew (Monthly 公允价值)",
        template="!skew {symbol} ivmid atm 30 m",
        order=22,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="Term Structure",
        template="!term {symbol} 60",
        order=23,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[定价分析] Vol Smile (指导 Ratio/Spread 定价)",
        # 修正: 补全中间参数 !smile symbol vol contract_filter dte expiration_filter
        template="!smile {symbol} ivmid ntm {dte} {exp}",
        order=24,
        param_mode="mid"
    ),
    
    # ========== 4. IV Path & Validation ==========
    CommandTemplate(
        group=CommandGroup.IV_PATH,
        description="确认 IV 趋势",
        template="v_path: {symbol} 7D ATM-IV 对比 3 日 skew 数据",
        order=30,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.IV_PATH,
        description="[真实意图] 确认今日资金流向 (用于证伪)",
        # 修正: 增加 {exp} 以匹配 param_mode="short" 的战术意图
        template="!volumen {symbol} {strikes} {dte} {exp}",
        order=31,
        param_mode="short"
    ),
    CommandTemplate(
        group=CommandGroup.IV_PATH,
        description="[波动率底牌] Dealer Vega 敞口",
        # 修正: 调整参数顺序 !vexn symbol strikes exp dte
        template="!vexn {symbol} {strikes} {exp} {dte}",
        order=32,
        param_mode="mid"
    ),
    
    # ========== 5. 扩展命令（条件触发）==========
    CommandTemplate(
        group=CommandGroup.EXTENDED,
        description="长期备份 (如果 dyn_dte_mid 已是月度)",
        template="!gexr {symbol} {strikes} {dte}",
        order=40,
        param_mode="long"
    ),
    
    # ========== 6. 指数背景（必需）==========
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="SPX 净Gamma",
        template="!gexn SPX {window} 98",
        order=50,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="SPX 7日 Skew",
        template="!skew SPX ivmid atm 7",
        order=51,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="QQQ 净Gamma (Big Tech)",
        template="!gexn QQQ {window} 98",
        order=53,
        param_mode="window"
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="QQQ 7日 Skew",
        template="!skew QQQ ivmid atm 7",
        order=54,
        param_mode="window"
    ),
]

class CommandListGenerator:
    """命令清单生成器"""
    
    def __init__(self, templates: List[CommandTemplate] = None):
        self.templates = templates or COMMAND_TEMPLATES.copy()
    
    def generate(
        self,
        symbol: str,
        pre_calc: Dict[str, Any],
        market_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成命令清单"""
        
        # 1. 解析基础参数
        base_params = {
            "symbol": symbol.upper(),
            "strikes": str(pre_calc.get("dyn_strikes", 30)),
            "window": str(pre_calc.get("dyn_window", 60)),
        }
        
        # 2. 解析 DTE 组合 (short/mid/long)
        # 格式示例: "14 w", "30 m"
        dte_params = {
            "short": self._parse_dte_str(pre_calc.get("dyn_dte_short", "14 w")),
            "mid":   self._parse_dte_str(pre_calc.get("dyn_dte_mid", "30 m")),
            "long":  self._parse_dte_str(pre_calc.get("dyn_dte_long_backup", "60 m"))
        }
        
        # 3. 过滤并渲染模板
        active_templates = self._filter_templates(pre_calc)
        commands = []
        
        for tpl in active_templates:
            # 根据 param_mode 组装参数
            mode = tpl.param_mode
            render_params = base_params.copy()
            
            if mode in dte_params:
                # 注入对应的 dte 和 exp
                render_params["dte"] = dte_params[mode]["dte"]
                render_params["exp"] = dte_params[mode]["exp"]
            else:
                # 默认使用 mid 的参数作为兜底
                render_params["dte"] = dte_params["mid"]["dte"]
                render_params["exp"] = dte_params["mid"]["exp"]
            
            # 渲染
            try:
                cmd_str = tpl.template.format(**render_params)
                commands.append({
                    "group": tpl.group.value,
                    "description": tpl.description,
                    "command": cmd_str,
                    "order": tpl.order
                })
            except KeyError as e:
                commands.append({
                    "group": "ERROR",
                    "description": f"Template Error: Missing {e}",
                    "command": tpl.template,
                    "order": 999
                })

        # 4. 格式化输出
        content = self._format_output(commands, symbol, pre_calc)
        
        return {
            "status": "success",
            "content": content,
            "commands": commands,
            "summary": {
                "total_commands": len(commands),
                "scenario": pre_calc.get("scenario", "N/A")
            }
        }
    
    def _parse_dte_str(self, dte_str: Any) -> Dict[str, str]:
        """
        解析 DTE 字符串
        Input: "14 w" -> {"dte": "14", "exp": "w"}
        Input: "30"   -> {"dte": "30", "exp": "*"}
        """
        if not dte_str:
            return {"dte": "30", "exp": "*"}
            
        s = str(dte_str).strip()
        
        # 提取数字
        digits = "".join(filter(str.isdigit, s))
        if not digits: digits = "30"
        
        # 提取 w/m/q
        exp = "*"
        if "w" in s.lower(): exp = "w"
        elif "m" in s.lower(): exp = "m"
        elif "q" in s.lower(): exp = "q"
        
        return {"dte": digits, "exp": exp}
    
    def _filter_templates(self, pre_calc: Dict) -> List[CommandTemplate]:
        active = []
        for tpl in self.templates:
            if not tpl.enabled: continue
            if tpl.condition:
                if not self._evaluate_condition(tpl.condition, pre_calc): continue
            active.append(tpl)
        return sorted(active, key=lambda x: x.order)
    
    def _evaluate_condition(self, condition: str, pre_calc: Dict) -> bool:
        try:
            env = {
                "scenario": pre_calc.get("scenario", ""),
                "vrp": pre_calc.get("vrp", 1.0),
                "strikes": pre_calc.get("dyn_strikes", 30)
            }
            return eval(condition, {"__builtins__": {}}, env)
        except Exception:
            return True 
    
    def _format_output(self, commands: List[Dict], symbol: str, pre_calc: Dict) -> str:
        lines = []
        lines.append(f"# {symbol.upper()} 双轨制数据抓取命令清单 (v3.6 Fixed)")
        lines.append(f"# 市场场景: {pre_calc.get('scenario', 'N/A')}")
        lines.append("")
        
        current_group = None
        group_num = 0
        for cmd in commands:
            group = cmd["group"]
            if group != current_group:
                current_group = group
                group_num += 1
                lines.append(f"#### {group_num}. {group}")
            lines.append(f"# {cmd['description']}")
            lines.append(cmd["command"])
            lines.append("")
        
        return "\n".join(lines)

# ============================================================
# 主函数
# ============================================================

def main(symbol: str, pre_calc: Dict[str, Any], market_params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    generator = CommandListGenerator()
    return generator.generate(symbol, pre_calc, market_params)

def generate_command_list(symbol: str, pre_calc: Dict[str, Any], market_params: Optional[Dict[str, Any]] = None) -> str:
    result = main(symbol, pre_calc, market_params)
    return result.get("content", "")