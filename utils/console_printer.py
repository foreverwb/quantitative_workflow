"""
控制台美化输出工具
提供统一的、美观的控制台输出格式
"""

import json
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os

class ConsolePrinter:
    """控制台美化打印器"""
    
    # 颜色代码
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'underline': '\033[4m',
        
        # 前景色
        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        
        # 亮色
        'bright_black': '\033[90m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
    }
    
    # 图标
    ICONS = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'debug': '🔍',
        'rocket': '🚀',
        'gear': '⚙️',
        'chart': '📊',
        'document': '📄',
        'folder': '📁',
        'light': '💡',
        'target': '🎯',
        'fire': '🔥',
        'star': '⭐',
        'arrow_right': '→',
        'check': '✓',
        'cross': '✗',
        'bullet': '•',
    }
    
    def __init__(self, use_color: bool = True):
        """
        初始化打印器
        
        Args:
            use_color: 是否使用颜色（Windows CMD 可能不支持）
        """
        self.use_color = use_color and sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """给文本添加颜色"""
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
    
    def _print_separator(self, char: str = '=', length: int = 80, color: str = 'cyan'):
        """打印分隔线"""
        line = char * length
        print(self._colorize(line, color))
    
    def _print_box(self, title: str, content: str = '', color: str = 'cyan'):
        """打印带边框的内容"""
        self._print_separator('=', 80, color)
        if title:
            print(self._colorize(f"  {title}", 'bold'))
            if content:
                self._print_separator('-', 80, 'dim')
        if content:
            print(content)
        self._print_separator('=', 80, color)
    
    def _truncate(self, text: str, max_length: int = 500) -> str:
        """截断过长的文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + self._colorize(f"\n... (截断，共 {len(text)} 字符)", 'dim')
    
    def _format_json(self, data: Any, indent: int = 2, max_depth: int = 3, current_depth: int = 0) -> str:
        """
        格式化 JSON 数据（支持深度限制）
        
        Args:
            data: 要格式化的数据
            indent: 缩进空格数
            max_depth: 最大深度
            current_depth: 当前深度
        """
        if current_depth >= max_depth:
            if isinstance(data, dict):
                return f"{{{len(data)} items}}"
            elif isinstance(data, list):
                return f"[{len(data)} items]"
            else:
                return str(data)
        
        try:
            if isinstance(data, dict):
                if not data:
                    return "{}"
                
                lines = ["{"]
                items = list(data.items())
                for i, (key, value) in enumerate(items):
                    is_last = i == len(items) - 1
                    
                    if isinstance(value, (dict, list)) and value:
                        formatted_value = self._format_json(value, indent, max_depth, current_depth + 1)
                        lines.append(f"  {' ' * (indent * current_depth)}\"{key}\": {formatted_value}{',' if not is_last else ''}")
                    else:
                        formatted_value = json.dumps(value, ensure_ascii=False)
                        lines.append(f"  {' ' * (indent * current_depth)}\"{key}\": {formatted_value}{',' if not is_last else ''}")
                
                lines.append(f"{' ' * (indent * current_depth)}}}")
                return "\n".join(lines)
            
            elif isinstance(data, list):
                if not data:
                    return "[]"
                
                if len(data) > 3:
                    # 只显示前3个元素
                    preview = [self._format_json(item, indent, max_depth, current_depth + 1) for item in data[:3]]
                    return f"[{', '.join(preview)}, ... +{len(data) - 3} more]"
                else:
                    items = [self._format_json(item, indent, max_depth, current_depth + 1) for item in data]
                    return f"[{', '.join(items)}]"
            
            else:
                return json.dumps(data, ensure_ascii=False)
        
        except Exception as e:
            return f"<格式化失败: {str(e)}>"
    
    # ============================================
    # 公共打印方法
    # ============================================
    
    def print_header(self, title: str, subtitle: str = ''):
        """打印大标题"""
        print("\n")
        self._print_separator('═', 80, 'bright_cyan')
        print(self._colorize(f"  {self.ICONS['rocket']} {title}", 'bold'))
        if subtitle:
            print(self._colorize(f"  {subtitle}", 'dim'))
        self._print_separator('═', 80, 'bright_cyan')
        print()
    
    def print_step(self, step_num: int, total_steps: int, step_name: str):
        """打印步骤标题"""
        print()
        progress = f"[{step_num}/{total_steps}]"
        print(self._colorize(f"{self.ICONS['target']} {progress} {step_name}", 'bright_yellow'))
        self._print_separator('-', 80, 'dim')
    
    def print_success(self, message: str):
        """打印成功消息"""
        print(self._colorize(f"{self.ICONS['success']} {message}", 'green'))
    
    def print_error(self, message: str, details: str = ''):
        """打印错误消息"""
        print(self._colorize(f"{self.ICONS['error']} {message}", 'red'))
        if details:
            print(self._colorize(f"   详情: {details}", 'bright_red'))
    
    def print_warning(self, message: str):
        """打印警告消息"""
        print(self._colorize(f"{self.ICONS['warning']} {message}", 'yellow'))
    
    def print_info(self, message: str):
        """打印信息消息"""
        print(self._colorize(f"{self.ICONS['info']} {message}", 'cyan'))
    
    def print_debug(self, message: str):
        """打印调试消息"""
        print(self._colorize(f"{self.ICONS['debug']} {message}", 'bright_black'))
    
    # ============================================
    # 节点输出方法
    # ============================================
    
    def print_agent_start(self, agent_name: str, description: str = ''):
        """打印 Agent 开始执行"""
        print()
        self._print_separator('─', 80, 'cyan')
        print(self._colorize(f"{self.ICONS['gear']} [{agent_name}] 开始执行", 'bold'))
        if description:
            print(self._colorize(f"   {description}", 'dim'))
        print()
    
    def print_agent_result(self, agent_name: str, result: Dict[str, Any], 
                          show_full: bool = False, max_content_length: int = 1000):
        """
        打印 Agent 结果
        
        Args:
            agent_name: Agent 名称
            result: 结果字典
            show_full: 是否显示完整内容
            max_content_length: 内容最大长度
        """
        print()
        self._print_box(
            f"{self.ICONS['chart']} [{agent_name}] 执行结果",
            color='green'
        )
        
        # 1. 基本信息
        if 'model' in result:
            print(self._colorize(f"  模型: {result['model']}", 'cyan'))
        
        if 'usage' in result:
            usage = result['usage']
            print(self._colorize(
                f"  Token: 输入={usage.get('input_tokens', 0)}, 输出={usage.get('output_tokens', 0)}",
                'cyan'
            ))
        
        # 2. 内容预览
        content = result.get('content', {})
        
        if isinstance(content, dict):
            print(self._colorize(f"\n  📋 内容类型: dict (共 {len(content)} 个字段)", 'yellow'))
            
            # 显示关键字段
            key_fields = self._extract_key_fields(content)
            if key_fields:
                print(self._colorize(f"\n  🔑 关键字段:", 'yellow'))
                for key, value in key_fields.items():
                    print(f"     {self.ICONS['bullet']} {key}: {value}")
            
            # 显示完整内容（可折叠）
            if show_full:
                print(self._colorize(f"\n  📄 完整内容:", 'yellow'))
                json_str = self._format_json(content, max_depth=3)
                print(self._truncate(json_str, max_content_length))
            else:
                print(self._colorize(f"\n  💡 提示: 使用 show_full=True 查看完整内容", 'dim'))
        
        elif isinstance(content, str):
            print(self._colorize(f"\n  📋 内容类型: str (共 {len(content)} 字符)", 'yellow'))
            print(self._truncate(content, max_content_length))
        
        print()
    
    def print_code_node_start(self, node_name: str, description: str = ''):
        """打印 Code Node 开始执行"""
        print()
        self._print_separator('┈', 80, 'magenta')
        print(self._colorize(f"{self.ICONS['gear']} [CODE: {node_name}] 开始执行", 'bold'))
        if description:
            print(self._colorize(f"   {description}", 'dim'))
        print()
    
    def print_code_node_result(self, node_name: str, result: Dict[str, Any],
                               show_full: bool = False, max_content_length: int = 1000):
        """
        打印 Code Node 结果
        
        Args:
            node_name: 节点名称
            result: 结果字典
            show_full: 是否显示完整内容
            max_content_length: 内容最大长度
        """
        print()
        
        # 检查是否有错误
        if 'error' in result or (isinstance(result.get('result'), str) and '"error": true' in result['result']):
            self._print_box(
                f"{self.ICONS['error']} [CODE: {node_name}] 执行失败",
                color='red'
            )
            
            # 解析错误信息
            error_msg = result.get('error_message', '未知错误')
            if isinstance(result.get('result'), str):
                try:
                    parsed = json.loads(result['result'])
                    error_msg = parsed.get('error_message', error_msg)
                except:
                    pass
            
            print(self._colorize(f"  {self.ICONS['cross']} 错误: {error_msg}", 'red'))
            print()
            return
        
        # 成功
        self._print_box(
            f"{self.ICONS['check']} [CODE: {node_name}] 执行成功",
            color='green'
        )
        
        # 解析结果
        result_data = result.get('result', {})
        
        if isinstance(result_data, str):
            try:
                parsed = json.loads(result_data)
                result_data = parsed
            except:
                pass
        
        if isinstance(result_data, dict):
            print(self._colorize(f"  📋 结果类型: dict (共 {len(result_data)} 个字段)", 'yellow'))
            
            # 显示状态信息
            if 'status' in result_data:
                status = result_data['status']
                status_icon = self.ICONS['success'] if status == 'complete' else self.ICONS['warning']
                print(f"  {status_icon} 状态: {status}")
            
            if 'data_status' in result_data:
                print(f"     数据状态: {result_data['data_status']}")
            
            # 显示验证信息
            if 'validation' in result_data:
                validation = result_data['validation']
                completion_rate = validation.get('completion_rate', 0)
                provided = validation.get('provided', 0)
                total = validation.get('total_required', 0)
                
                print(self._colorize(f"\n  📊 数据完整性:", 'yellow'))
                print(f"     完成度: {completion_rate}% ({provided}/{total})")
                
                missing = validation.get('missing_fields', [])
                if missing:
                    print(f"     缺失字段: {len(missing)} 个")
                    if len(missing) <= 5:
                        for field in missing:
                            path = field.get('path', field.get('field', ''))
                            print(f"        {self.ICONS['bullet']} {path}")
                    else:
                        for field in missing[:5]:
                            path = field.get('path', field.get('field', ''))
                            print(f"        {self.ICONS['bullet']} {path}")
                        print(f"        ... 还有 {len(missing) - 5} 个")
            
            # 显示关键指标
            key_metrics = self._extract_key_metrics(result_data)
            if key_metrics:
                print(self._colorize(f"\n  🔑 关键指标:", 'yellow'))
                for key, value in key_metrics.items():
                    print(f"     {self.ICONS['bullet']} {key}: {value}")
            
            # 显示完整内容
            if show_full:
                print(self._colorize(f"\n  📄 完整内容:", 'yellow'))
                json_str = self._format_json(result_data, max_depth=2)
                print(self._truncate(json_str, max_content_length))
        
        print()
    
    def print_summary(self, title: str, items: List[str]):
        """打印汇总信息"""
        print()
        self._print_box(
            f"{self.ICONS['document']} {title}",
            color='bright_cyan'
        )
        
        for item in items:
            print(f"  {self.ICONS['check']} {item}")
        
        print()
    
    # ============================================
    # 辅助方法
    # ============================================
    
    def _extract_key_fields(self, data: Dict) -> Dict[str, str]:
        """提取关键字段"""
        key_fields = {}
        
        # 优先级字段列表
        priority_fields = [
            'symbol', 'status', 'total_score', 'spot_price', 'em1_dollar',
            'primary_scenario', 'scenario_probability', 'entry_threshold_check',
            'risk_level', 'event_count', 'missing_count', 'completion_rate'
        ]
        
        for field in priority_fields:
            if field in data:
                value = data[field]
                if isinstance(value, (int, float)):
                    key_fields[field] = f"{value:.2f}" if isinstance(value, float) else str(value)
                else:
                    key_fields[field] = str(value)[:50]
        
        return key_fields
    
    def _extract_key_metrics(self, data: Dict) -> Dict[str, str]:
        """提取关键指标"""
        metrics = {}
        
        # 提取嵌套字段
        if 'targets' in data:
            targets = data['targets']
            if isinstance(targets, dict):
                if 'spot_price' in targets:
                    metrics['现价'] = f"${targets['spot_price']}"
                if 'em1_dollar' in targets:
                    metrics['EM1$'] = f"${targets['em1_dollar']}"
                
                gamma_metrics = targets.get('gamma_metrics', {})
                if 'vol_trigger' in gamma_metrics:
                    metrics['VOL_TRIGGER'] = f"${gamma_metrics['vol_trigger']}"
                if 'spot_vs_trigger' in gamma_metrics:
                    metrics['Gamma状态'] = gamma_metrics['spot_vs_trigger']
        
        # 提取评分
        if 'scoring' in data:
            scoring = data['scoring']
            if 'total_score' in scoring:
                metrics['总评分'] = f"{scoring['total_score']:.1f}"
        
        return metrics


# ============================================
# 全局实例
# ============================================
printer = ConsolePrinter()


# ============================================
# 快捷函数
# ============================================

def print_header(title: str, subtitle: str = ''):
    """快捷打印标题"""
    printer.print_header(title, subtitle)


def print_step(step_num: int, total_steps: int, step_name: str):
    """快捷打印步骤"""
    printer.print_step(step_num, total_steps, step_name)


def print_agent_start(agent_name: str, description: str = ''):
    """快捷打印 Agent 开始"""
    printer.print_agent_start(agent_name, description)


def print_agent_result(agent_name: str, result: Dict[str, Any], show_full: bool = False):
    """快捷打印 Agent 结果"""
    printer.print_agent_result(agent_name, result, show_full)


def print_code_node_start(node_name: str, description: str = ''):
    """快捷打印 Code Node 开始"""
    printer.print_code_node_start(node_name, description)


def print_code_node_result(node_name: str, result: Dict[str, Any], show_full: bool = False):
    """快捷打印 Code Node 结果"""
    printer.print_code_node_result(node_name, result, show_full)


def print_success(message: str):
    """快捷打印成功"""
    printer.print_success(message)


def print_error(message: str, details: str = ''):
    """快捷打印错误"""
    printer.print_error(message, details)


def print_warning(message: str):
    """快捷打印警告"""
    printer.print_warning(message)


def print_info(message: str):
    """快捷打印信息"""
    printer.print_info(message)
    
def print_error_summary(error_report: Dict):
    """打印错误摘要"""
    
    summary = error_report.get("error_summary", {})
    suggestions = error_report.get("suggestions", [])
    completed = error_report.get("completed_steps", [])
    
    print()
    printer._print_box(
        f"{printer.ICONS['error']} 流程执行失败",
        color='red'
    )
    
    # 基本信息
    print(printer._colorize(f"  严重程度: {summary.get('severity', 'unknown').upper()}", 'red'))
    print(printer._colorize(f"  错误类别: {summary.get('category', 'unknown')}", 'red'))
    print(printer._colorize(f"  失败节点: {summary.get('node', 'unknown')}", 'red'))
    print(printer._colorize(f"  错误消息: {summary.get('message', '')}", 'red'))
    print(printer._colorize(f"  发生时间: {summary.get('timestamp', '')}", 'dim'))
    
    # 已完成步骤
    if completed:
        print(printer._colorize(f"\n  ✅ 已完成步骤 ({len(completed)}):", 'green'))
        for step_info in completed[-5:]:  # 只显示最后5个
            step_name = step_info if isinstance(step_info, str) else step_info.get('step', '')
            print(f"     {printer.ICONS['check']} {step_name}")
    
    # 修复建议
    if suggestions:
        print(printer._colorize(f"\n  💡 修复建议:", 'yellow'))
        for i, suggestion in enumerate(suggestions, 1):
            print(f"     {i}. {suggestion}")
    
    print()

def print_report_link(html_path: str, symbol: str = ""):
    """
    打印可点击的报告链接
    
    Args:
        html_path: HTML 文件路径
        symbol: 股票代码
    """
    
    # 转换为绝对路径
    abs_path = Path(html_path).resolve()
    
    # 生成 file:// URL
    if os.name == 'nt':  # Windows
        file_url = f"file:///{str(abs_path).replace(os.sep, '/')}"
    else:  # macOS / Linux
        file_url = f"file://{abs_path}"
    
    # 生成可点击的终端链接 (使用 OSC 8 超链接转义序列)
    # 格式: \033]8;;URL\033\\显示文本\033]8;;\033\\
    clickable_link = f"\033]8;;{file_url}\033\\{file_url}\033]8;;\033\\"
    
    # 打印分隔线和链接
    print()
    printer._print_separator('═', 80, 'bright_green')
    print(printer._colorize(f"  {printer.ICONS['success']} 报告生成完成！", 'bold'))
    printer._print_separator('─', 80, 'dim')
    print()
    print(printer._colorize(f"  📊 {symbol} 策略分析报告", 'bright_cyan'))
    print()
    print(f" Link : {clickable_link}")
    print()
    printer._print_separator('═', 80, 'bright_green')
    print()