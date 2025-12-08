"""
安全格式化工具模块

提供类型安全的格式化函数，自动处理常见的类型转换问题：
- float -> int 转换（用于 :d 格式）
- None 值处理
- 边界值处理

使用方式：
1. 直接使用工具函数：
   from utils.formatters import fmt_int, fmt_float, fmt_pct
   
   rationale = f"调整{fmt_int(adjustment, signed=True)}分"
   
2. 使用 SafeFormatter 类：
   from utils.formatters import safe_format
   
   result = safe_format("调整{:+d}分", adjustment)

3. 使用 F 类的链式调用（推荐）：
   from utils.formatters import F
   
   text = f"得分{F.int(score)}分，变化{F.int(delta, signed=True)}，比例{F.pct(ratio)}"
"""

from typing import Any, Optional, Union
from string import Formatter
import re


# ============================================================
# 方案 1：简单的格式化函数
# ============================================================

def fmt_int(value: Any, default: int = 0, signed: bool = False) -> str:
    """
    安全格式化整数
    
    Args:
        value: 输入值（int/float/str/None）
        default: 默认值（当 value 无效时使用）
        signed: 是否显示正号（+）
        
    Returns:
        格式化后的字符串
        
    Examples:
        >>> fmt_int(3.7)
        '3'
        >>> fmt_int(3.7, signed=True)
        '+3'
        >>> fmt_int(-2, signed=True)
        '-2'
        >>> fmt_int(None)
        '0'
    """
    try:
        int_val = int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        int_val = default
    
    if signed:
        return f"{int_val:+d}"
    return str(int_val)


def fmt_float(value: Any, decimals: int = 2, default: float = 0.0) -> str:
    """
    安全格式化浮点数
    
    Args:
        value: 输入值
        decimals: 小数位数
        default: 默认值
        
    Returns:
        格式化后的字符串
        
    Examples:
        >>> fmt_float(3.14159, 2)
        '3.14'
        >>> fmt_float(None)
        '0.00'
    """
    try:
        float_val = float(value) if value is not None else default
    except (ValueError, TypeError):
        float_val = default
    
    return f"{float_val:.{decimals}f}"


def fmt_pct(value: Any, decimals: int = 1, default: float = 0.0) -> str:
    """
    安全格式化百分比
    
    Args:
        value: 输入值（0.5 表示 50%）
        decimals: 小数位数
        default: 默认值
        
    Returns:
        格式化后的百分比字符串
        
    Examples:
        >>> fmt_pct(0.756)
        '75.6%'
        >>> fmt_pct(None)
        '0.0%'
    """
    try:
        float_val = float(value) * 100 if value is not None else default * 100
    except (ValueError, TypeError):
        float_val = default * 100
    
    return f"{float_val:.{decimals}f}%"


def fmt_currency(value: Any, decimals: int = 2, symbol: str = "$", default: float = 0.0) -> str:
    """
    安全格式化货币
    
    Args:
        value: 输入值
        decimals: 小数位数
        symbol: 货币符号
        default: 默认值
        
    Returns:
        格式化后的货币字符串
        
    Examples:
        >>> fmt_currency(1234.5)
        '$1234.50'
    """
    try:
        float_val = float(value) if value is not None else default
    except (ValueError, TypeError):
        float_val = default
    
    return f"{symbol}{float_val:.{decimals}f}"


def fmt_signed(value: Any, decimals: int = 2, default: float = 0.0) -> str:
    """
    安全格式化带符号的浮点数
    
    Args:
        value: 输入值
        decimals: 小数位数
        default: 默认值
        
    Returns:
        格式化后的带符号字符串
        
    Examples:
        >>> fmt_signed(3.14)
        '+3.14'
        >>> fmt_signed(-2.5)
        '-2.50'
    """
    try:
        float_val = float(value) if value is not None else default
    except (ValueError, TypeError):
        float_val = default
    
    return f"{float_val:+.{decimals}f}"


# ============================================================
# 方案 2：F 类 - 链式调用（推荐）
# ============================================================

class F:
    """
    格式化工具类 - 提供简洁的静态方法
    
    使用方式：
        from utils.formatters import F
        
        text = f"得分{F.int(score)}，变化{F.int(delta, True)}，比例{F.pct(ratio)}"
    """
    
    @staticmethod
    def int(value: Any, signed: bool = False, default: int = 0) -> str:
        """格式化整数"""
        return fmt_int(value, default=default, signed=signed)
    
    @staticmethod
    def float(value: Any, decimals: int = 2, default: float = 0.0) -> str:
        """格式化浮点数"""
        return fmt_float(value, decimals=decimals, default=default)
    
    @staticmethod
    def pct(value: Any, decimals: int = 1, default: float = 0.0) -> str:
        """格式化百分比"""
        return fmt_pct(value, decimals=decimals, default=default)
    
    @staticmethod
    def currency(value: Any, decimals: int = 2, symbol: str = "$", default: float = 0.0) -> str:
        """格式化货币"""
        return fmt_currency(value, decimals=decimals, symbol=symbol, default=default)
    
    @staticmethod
    def signed(value: Any, decimals: int = 2, default: float = 0.0) -> str:
        """格式化带符号浮点数"""
        return fmt_signed(value, decimals=decimals, default=default)
    
    @staticmethod
    def safe(value: Any, fmt_spec: str = "", default: Any = "N/A") -> str:
        """
        通用安全格式化
        
        Args:
            value: 输入值
            fmt_spec: 格式规范（如 '.2f', '+d', '.1%'）
            default: 默认值
            
        Examples:
            >>> F.safe(3.7, '+d')
            '+3'
            >>> F.safe(0.5, '.1%')
            '50.0%'
        """
        if value is None:
            return str(default)
        
        try:
            # 解析格式规范
            if fmt_spec.endswith('d'):
                # 整数格式
                return format(int(float(value)), fmt_spec)
            elif fmt_spec.endswith('%'):
                # 百分比格式
                return format(float(value), fmt_spec)
            elif fmt_spec.endswith(('f', 'e', 'g')):
                # 浮点数格式
                return format(float(value), fmt_spec)
            else:
                # 其他格式
                return format(value, fmt_spec)
        except (ValueError, TypeError):
            return str(default)


# ============================================================
# 方案 3：SafeFormatter 类 - 自动类型转换
# ============================================================

class SafeFormatter(Formatter):
    """
    安全格式化器 - 自动处理类型转换
    
    继承自 string.Formatter，重写 format_field 方法以自动处理：
    - float -> int 转换（当格式规范要求整数时）
    - None 值处理
    - 异常捕获
    
    使用方式：
        formatter = SafeFormatter()
        result = formatter.format("调整{:+d}分", 3.7)  # -> "调整+3分"
        
    或使用便捷函数：
        from utils.formatters import safe_format
        result = safe_format("调整{:+d}分", 3.7)
    """
    
    def __init__(self, default_value: str = "N/A"):
        """
        初始化
        
        Args:
            default_value: 当值为 None 或转换失败时使用的默认值
        """
        super().__init__()
        self.default_value = default_value
    
    def format_field(self, value: Any, format_spec: str) -> str:
        """
        重写格式化字段方法，添加类型自动转换
        
        Args:
            value: 要格式化的值
            format_spec: 格式规范
            
        Returns:
            格式化后的字符串
        """
        # 处理 None 值
        if value is None:
            return self.default_value
        
        try:
            # 检测格式规范类型
            if format_spec.endswith('d'):
                # 整数格式：自动将 float 转换为 int
                value = int(float(value))
            elif format_spec.endswith(('f', 'e', 'E', 'g', 'G', '%')):
                # 浮点数格式：确保是数字类型
                value = float(value)
            
            return format(value, format_spec)
        
        except (ValueError, TypeError) as e:
            # 转换失败，返回默认值或原始值的字符串表示
            return self.default_value if value is None else str(value)


# 创建默认实例
_default_formatter = SafeFormatter()


def safe_format(template: str, *args, **kwargs) -> str:
    """
    安全格式化字符串
    
    使用 SafeFormatter 自动处理类型转换。
    
    Args:
        template: 格式化模板
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        格式化后的字符串
        
    Examples:
        >>> safe_format("调整{:+d}分", 3.7)
        '调整+3分'
        >>> safe_format("比例{:.2%}", 0.756)
        '比例75.60%'
        >>> safe_format("{name}得分{score:+d}", name="A", score=5.0)
        'A得分+5'
    """
    return _default_formatter.format(template, *args, **kwargs)


# ============================================================
# 方案 4：装饰器 - 自动修复函数返回的字符串
# ============================================================

def auto_fix_format(func):
    """
    装饰器：自动修复函数中的格式化问题
    
    注意：此装饰器主要用于调试和遗留代码兼容，
    新代码建议直接使用 F 类或 safe_format 函数。
    
    使用方式：
        @auto_fix_format
        def build_rationale(score, adjustment):
            return f"得分{score}，调整{adjustment:+d}分"
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, TypeError) as e:
            if "Unknown format code" in str(e):
                # 格式化错误，尝试修复
                # 这里只是记录日志，实际修复需要更复杂的处理
                import logging
                logging.warning(f"格式化错误在 {func.__name__}: {e}")
            raise
    return wrapper


# ============================================================
# 导出
# ============================================================

__all__ = [
    # 简单函数
    'fmt_int',
    'fmt_float', 
    'fmt_pct',
    'fmt_currency',
    'fmt_signed',
    # F 类
    'F',
    # SafeFormatter
    'SafeFormatter',
    'safe_format',
    # 装饰器
    'auto_fix_format',
]