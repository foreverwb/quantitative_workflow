"""
Code Node 2: 命令清单生成器
用途：基于配置生成"战术(Weekly)"与"战略(Monthly)"双轨数据抓取命令
重构自 Agent2，无需调用模型，使用代码直接生成

设计原则：
1. 配置驱动 - 命令模板可从 YAML 配置文件或代码中定义
2. 灵活扩展 - 新增/删除命令只需修改配置
3. 分组管理 - 命令按功能分组，结构清晰
4. 条件执行 - 支持可选命令和条件触发
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml


class CommandGroup(Enum):
    """命令分组枚举"""
    CORE_STRUCTURE = "核心结构"
    FLOWS = "供需流向"
    VOLATILITY = "波动率锚点"
    IV_PATH = "IV Path & Validation"
    EXTENDED = "扩展命令"
    INDEX_BACKGROUND = "指数背景"


# 组名映射（用于 YAML 配置文件）
GROUP_NAME_MAP = {
    "core_structure": CommandGroup.CORE_STRUCTURE,
    "flows": CommandGroup.FLOWS,
    "volatility": CommandGroup.VOLATILITY,
    "iv_path": CommandGroup.IV_PATH,
    "extended": CommandGroup.EXTENDED,
    "index_background": CommandGroup.INDEX_BACKGROUND,
}


@dataclass
class CommandTemplate:
    """命令模板数据类"""
    group: CommandGroup
    description: str
    template: str
    order: int = 0
    enabled: bool = True
    condition: Optional[str] = None  # 条件表达式，如 "scenario == 'Squeeze'"


# ============================================================
# 核心配置：命令模板列表
# 修改此处即可调整生成的命令
# ============================================================

COMMAND_TEMPLATES: List[CommandTemplate] = [
    # ========== 1. 核心结构 (Walls & Clusters) ==========
    CommandTemplate(
        group=CommandGroup.CORE_STRUCTURE,
        description="[战术视图] 捕捉近端摩擦与周度博弈 (Weekly Friction)",
        template="!gexr {symbol} {strikes} {dte_short} w",
        order=1
    ),
    CommandTemplate(
        group=CommandGroup.CORE_STRUCTURE,
        description="[战略视图] 锁定机构核心仓位与磁力目标 (Monthly Structure)",
        template="!gexr {symbol} {strikes} {dte_mid} m",
        order=2
    ),
    
    # ========== 2. 供需流向 (Flows) ==========
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="净Gamma与触发线 (全周期)",
        template="!gexn {symbol} {window} 98",
        order=10
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="Trigger Line",
        template="!trigger {symbol} {window}",
        order=11
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="Vanna Exposure (使用 m 过滤，聚焦长期持仓对冲压力)",
        template="!vanna {symbol} ntm {window} m",
        order=12
    ),
    CommandTemplate(
        group=CommandGroup.FLOWS,
        description="Delta Exposure (与中期结构对齐)",
        template="!dexn {symbol} {strikes} {dte_mid}",
        order=13
    ),
    
    # ========== 3. 波动率锚点 (Volatility Anchors) ==========
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[物理锚点] 7日 Skew (用于 Raw_EM1$)",
        template="!skew {symbol} ivmid atm 7",
        order=20
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[物理锚点] 14日 Skew",
        template="!skew {symbol} ivmid atm 14",
        order=21
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="[定价基准] 30日 Skew (Monthly 公允价值)",
        template="!skew {symbol} ivmid atm 30 m",
        order=22
    ),
    CommandTemplate(
        group=CommandGroup.VOLATILITY,
        description="Term Structure",
        template="!term {symbol} 60",
        order=23
    ),
    
    # ========== 4. IV Path & Validation ==========
    CommandTemplate(
        group=CommandGroup.IV_PATH,
        description="确认 IV 趋势",
        template="v_path: {symbol} 7D ATM-IV 对比 3 日 skew 数据",
        order=30
    ),
    CommandTemplate(
        group=CommandGroup.IV_PATH,
        description="[真实意图] 确认今日资金流向 (用于证伪)",
        template="!volumen {symbol} {strikes} {dte_short}",
        order=31
    ),
    CommandTemplate(
        group=CommandGroup.IV_PATH,
        description="[波动率底牌] Dealer Vega 敞口",
        template="!vexn {symbol} {strikes} {dte_mid}",
        order=32
    ),
    
    # ========== 5. 扩展命令（条件触发）==========
    CommandTemplate(
        group=CommandGroup.EXTENDED,
        description="长期备份 (如果 dyn_dte_mid 已是月度)",
        template="!gexr {symbol} {strikes} {dte_long}",
        order=40
    ),
    
    # ========== 6. 指数背景（必需）==========
    # SPX
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="SPX 净Gamma",
        template="!gexn SPX {window} 98",
        order=50
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="SPX 7日 Skew",
        template="!skew SPX ivmid atm 7",
        order=51
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="SPX 14日 Skew",
        template="!skew SPX ivmid atm 14",
        order=52
    ),
    # QQQ (Big Tech)
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="QQQ 净Gamma (Big Tech)",
        template="!gexn QQQ {window} 98",
        order=53
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="QQQ 7日 Skew",
        template="!skew QQQ ivmid atm 7",
        order=54
    ),
    CommandTemplate(
        group=CommandGroup.INDEX_BACKGROUND,
        description="QQQ 14日 Skew",
        template="!skew QQQ ivmid atm 14",
        order=55
    ),
]


class CommandListGenerator:
    """
    命令清单生成器
    
    使用配置驱动的方式生成数据抓取命令，完全替代 Agent2 的 LLM 调用
    
    支持两种配置方式：
    1. 从代码中定义的 COMMAND_TEMPLATES 加载（默认）
    2. 从 YAML 配置文件加载（推荐，更灵活）
    """
    
    # 默认配置文件路径（相对于项目根目录）
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "cmdlist_config.yaml"
    
    def __init__(
        self, 
        templates: List[CommandTemplate] = None,
        config_path: Optional[str] = None
    ):
        """
        初始化生成器
        
        Args:
            templates: 命令模板列表，默认使用 COMMAND_TEMPLATES
            config_path: YAML 配置文件路径（如果指定，优先使用配置文件）
        """
        if config_path:
            # 从指定的配置文件加载
            self.templates = self._load_from_yaml(config_path)
        elif self.DEFAULT_CONFIG_PATH.exists():
            # 从默认配置文件加载
            self.templates = self._load_from_yaml(str(self.DEFAULT_CONFIG_PATH))
        elif templates:
            # 使用传入的模板
            self.templates = templates
        else:
            # 使用代码中定义的默认模板
            self.templates = COMMAND_TEMPLATES.copy()
    
    def _load_from_yaml(self, config_path: str) -> List[CommandTemplate]:
        """
        从 YAML 配置文件加载命令模板
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            命令模板列表
        """
        templates = []
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            commands = config.get('commands', [])
            
            for cmd in commands:
                # 解析组名
                group_name = cmd.get('group', 'extended')
                group = GROUP_NAME_MAP.get(group_name, CommandGroup.EXTENDED)
                
                # 创建模板对象
                tpl = CommandTemplate(
                    group=group,
                    description=cmd.get('description', ''),
                    template=cmd.get('template', ''),
                    order=cmd.get('order', 100),
                    enabled=cmd.get('enabled', True),
                    condition=cmd.get('condition')
                )
                
                templates.append(tpl)
                
        except Exception as e:
            # 加载失败时使用默认模板
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("Using default templates.")
            return COMMAND_TEMPLATES.copy()
        
        return templates
    
    def generate(
        self,
        symbol: str,
        pre_calc: Dict[str, Any],
        market_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成命令清单
        
        Args:
            symbol: 股票代码 (如 "NVDA")
            pre_calc: MarketStateCalculator 计算的动态参数
                - dyn_strikes: int
                - dyn_dte_short: str (如 "14 w")
                - dyn_dte_mid: str (如 "30 w")
                - dyn_dte_long_backup: str (如 "60 m")
                - dyn_window: int
                - scenario: str
                - vrp: float
            market_params: 市场参数 (可选，用于生成后续命令提示)
                - vix, ivr, iv30, hv20
        
        Returns:
            {
                "status": "success",
                "content": str,  # 格式化的命令清单文本
                "commands": List[Dict],  # 结构化的命令列表
                "summary": Dict  # 统计摘要
            }
        """
        # 提取参数
        params = self._extract_params(symbol, pre_calc)
        
        # 过滤并排序模板
        active_templates = self._filter_templates(pre_calc)
        
        # 生成命令
        commands = []
        for tpl in active_templates:
            cmd = self._render_template(tpl, params)
            commands.append(cmd)
        
        # 格式化输出
        content = self._format_output(commands, symbol, pre_calc, market_params)
        
        return {
            "status": "success",
            "content": content,
            "commands": commands,
            "summary": {
                "total_commands": len(commands),
                "groups": self._count_by_group(commands),
                "scenario": pre_calc.get("scenario", "N/A")
            }
        }
    
    def _extract_params(self, symbol: str, pre_calc: Dict) -> Dict[str, str]:
        """提取模板参数"""
        # 处理 DTE 格式（移除空格便于命令行使用）
        dte_short = pre_calc.get("dyn_dte_short", "14 w").replace(" ", "")
        dte_mid = pre_calc.get("dyn_dte_mid", "30 w").replace(" ", "")
        dte_long = pre_calc.get("dyn_dte_long_backup", "60 m").replace(" ", "")
        
        return {
            "symbol": symbol.upper(),
            "strikes": str(pre_calc.get("dyn_strikes", 30)),
            "dte_short": dte_short,
            "dte_mid": dte_mid,
            "dte_long": dte_long,
            "window": str(pre_calc.get("dyn_window", 60)),
        }
    
    def _filter_templates(self, pre_calc: Dict) -> List[CommandTemplate]:
        """过滤并排序模板"""
        active = []
        
        for tpl in self.templates:
            # 检查是否启用
            if not tpl.enabled:
                continue
            
            # 检查条件（如果有）
            if tpl.condition:
                if not self._evaluate_condition(tpl.condition, pre_calc):
                    continue
            
            active.append(tpl)
        
        # 按 order 排序
        return sorted(active, key=lambda x: x.order)
    
    def _evaluate_condition(self, condition: str, pre_calc: Dict) -> bool:
        """
        评估条件表达式
        
        支持简单的条件如:
        - "scenario == 'Squeeze'"
        - "vrp > 1.15"
        """
        try:
            # 创建安全的评估环境
            env = {
                "scenario": pre_calc.get("scenario", ""),
                "vrp": pre_calc.get("vrp", 1.0),
                "strikes": pre_calc.get("dyn_strikes", 30),
                "window": pre_calc.get("dyn_window", 60),
            }
            return eval(condition, {"__builtins__": {}}, env)
        except Exception:
            return True  # 条件评估失败时默认启用
    
    def _render_template(self, tpl: CommandTemplate, params: Dict[str, str]) -> Dict:
        """渲染单个模板"""
        # 替换参数
        command = tpl.template.format(**params)
        
        return {
            "group": tpl.group.value,
            "description": tpl.description,
            "command": command,
            "order": tpl.order
        }
    
    def _format_output(
        self,
        commands: List[Dict],
        symbol: str,
        pre_calc: Dict,
        market_params: Optional[Dict]
    ) -> str:
        """格式化输出文本"""
        lines = []
        
        # 标题
        scenario = pre_calc.get("scenario", "N/A")
        lines.append(f"# {symbol.upper()} 双轨制数据抓取命令清单")
        lines.append(f"# 市场场景: {scenario}")
        lines.append(f"# 动态参数: Strikes={pre_calc.get('dyn_strikes')} | "
                    f"DTE_Mid={pre_calc.get('dyn_dte_mid')} | "
                    f"Window={pre_calc.get('dyn_window')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 按组输出命令
        current_group = None
        group_num = 0
        
        for cmd in commands:
            group = cmd["group"]
            
            # 新组标题
            if group != current_group:
                current_group = group
                group_num += 1
                lines.append(f"#### {group_num}. {group}")
                lines.append("")
            
            # 命令描述和内容
            lines.append(f"# {cmd['description']}")
            lines.append(cmd["command"])
            lines.append("")
        
        # 分隔线
        lines.append("---")
        lines.append("")
        
        # 后续提示
        lines.append("**后续操作提示**:")
        lines.append("")
        lines.append("根据上述命令抓取数据后，请使用以下命令执行完整分析：")
        lines.append("")
        
        if market_params:
            vix = market_params.get('vix', 18.5)
            ivr = market_params.get('ivr', 50)
            iv30 = market_params.get('iv30', 30)
            hv20 = market_params.get('hv20', 25)
            lines.append(f"```bash")
            lines.append(f"python app.py analyze {symbol.upper()} -f <数据文件夹路径> "
                        f"--vix {vix} --ivr {ivr} --iv30 {iv30} --hv20 {hv20}")
            lines.append(f"```")
        else:
            lines.append(f"```bash")
            lines.append(f"python app.py analyze {symbol.upper()} -f <数据文件夹路径> --cache <缓存文件>")
            lines.append(f"```")
        
        return "\n".join(lines)
    
    def _count_by_group(self, commands: List[Dict]) -> Dict[str, int]:
        """按组统计命令数量"""
        counts = {}
        for cmd in commands:
            group = cmd["group"]
            counts[group] = counts.get(group, 0) + 1
        return counts
    
    # ============================================================
    # 扩展方法：支持动态修改模板
    # ============================================================
    
    def add_command(
        self,
        group: CommandGroup,
        description: str,
        template: str,
        order: int = 100,
        condition: str = None
    ) -> None:
        """
        动态添加命令模板
        
        Args:
            group: 命令分组
            description: 命令描述
            template: 命令模板 (使用 {symbol}, {strikes} 等占位符)
            order: 排序权重
            condition: 条件表达式 (可选)
        """
        new_tpl = CommandTemplate(
            group=group,
            description=description,
            template=template,
            order=order,
            condition=condition
        )
        self.templates.append(new_tpl)
    
    def remove_command_by_template(self, template: str) -> bool:
        """
        根据模板内容删除命令
        
        Args:
            template: 要删除的模板字符串
            
        Returns:
            是否成功删除
        """
        original_len = len(self.templates)
        self.templates = [t for t in self.templates if t.template != template]
        return len(self.templates) < original_len
    
    def disable_group(self, group: CommandGroup) -> int:
        """
        禁用整个命令组
        
        Args:
            group: 要禁用的组
            
        Returns:
            禁用的命令数量
        """
        count = 0
        for tpl in self.templates:
            if tpl.group == group and tpl.enabled:
                tpl.enabled = False
                count += 1
        return count
    
    def enable_group(self, group: CommandGroup) -> int:
        """
        启用整个命令组
        
        Args:
            group: 要启用的组
            
        Returns:
            启用的命令数量
        """
        count = 0
        for tpl in self.templates:
            if tpl.group == group and not tpl.enabled:
                tpl.enabled = True
                count += 1
        return count
    
    def list_templates(self) -> List[Dict]:
        """
        列出所有模板（用于调试和管理）
        
        Returns:
            模板信息列表
        """
        return [
            {
                "group": t.group.value,
                "description": t.description,
                "template": t.template,
                "order": t.order,
                "enabled": t.enabled,
                "condition": t.condition
            }
            for t in sorted(self.templates, key=lambda x: x.order)
        ]
    
    def reload_from_config(self, config_path: str = None) -> int:
        """
        重新从配置文件加载模板
        
        Args:
            config_path: 配置文件路径（默认使用 DEFAULT_CONFIG_PATH）
            
        Returns:
            加载的模板数量
        """
        path = config_path or str(self.DEFAULT_CONFIG_PATH)
        self.templates = self._load_from_yaml(path)
        return len(self.templates)
    
    def save_to_yaml(self, output_path: str) -> bool:
        """
        将当前模板保存到 YAML 配置文件
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否保存成功
        """
        # 反向组名映射
        reverse_group_map = {v: k for k, v in GROUP_NAME_MAP.items()}
        
        commands = []
        for tpl in sorted(self.templates, key=lambda x: x.order):
            cmd = {
                "group": reverse_group_map.get(tpl.group, "extended"),
                "description": tpl.description,
                "template": tpl.template,
                "order": tpl.order,
                "enabled": tpl.enabled
            }
            if tpl.condition:
                cmd["condition"] = tpl.condition
            commands.append(cmd)
        
        config = {
            "version": "1.0",
            "commands": commands
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False


# ============================================================
# 主函数：兼容 code_nodes 调用约定
# ============================================================

def main(
    symbol: str,
    pre_calc: Dict[str, Any],
    market_params: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    命令清单生成主函数
    
    兼容 code_nodes 的调用约定，可被 agent_executor.execute_code_node() 调用
    
    Args:
        symbol: 股票代码
        pre_calc: 动态参数字典
        market_params: 市场参数 (可选)
        **kwargs: 其他参数 (忽略)
    
    Returns:
        生成结果字典
    """
    generator = CommandListGenerator()
    return generator.generate(symbol, pre_calc, market_params)


# ============================================================
# 便捷函数：直接获取命令文本
# ============================================================

def generate_command_list(
    symbol: str,
    pre_calc: Dict[str, Any],
    market_params: Optional[Dict[str, Any]] = None
) -> str:
    """
    便捷函数：直接返回命令清单文本
    
    Args:
        symbol: 股票代码
        pre_calc: 动态参数
        market_params: 市场参数 (可选)
    
    Returns:
        格式化的命令清单字符串
    """
    result = main(symbol, pre_calc, market_params)
    return result.get("content", "")


if __name__ == "__main__":
    # 测试代码
    test_pre_calc = {
        "dyn_strikes": 30,
        "dyn_dte_short": "14 w",
        "dyn_dte_mid": "30 w",
        "dyn_dte_long_backup": "60 m",
        "dyn_window": 60,
        "scenario": "Normal/Trend",
        "vrp": 1.12
    }
    
    test_market_params = {
        "vix": 18.5,
        "ivr": 65,
        "iv30": 42.8,
        "hv20": 38.2
    }
    
    result = main("NVDA", test_pre_calc, test_market_params)
    print(result["content"])
    print("\n--- Summary ---")
    print(f"Total commands: {result['summary']['total_commands']}")
    print(f"Groups: {result['summary']['groups']}")
