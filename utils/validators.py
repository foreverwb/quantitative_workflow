"""
数据验证工具
"""

import re
from typing import Tuple


def validate_symbol(symbol: str) -> Tuple[bool, str]:
    """
    验证股票代码
    
    Args:
        symbol: 股票代码
        
    Returns:
        (是否有效, 标准化后的代码或错误消息)
    """
    if not symbol:
        return False, "股票代码不能为空"
    
    symbol = symbol.strip().upper()
    
    # 检查是否为保留关键字
    reserved_keywords = ["UNKNOWN", "TEST", "N/A", "NULL", "NONE", "ERROR"]
    if symbol in reserved_keywords:
        return False, f"'{symbol}' 是保留关键字，不能作为股票代码"
    
    # 检查长度（1-10个字符）
    if len(symbol) < 1 or len(symbol) > 10:
        return False, f"股票代码长度必须在 1-10 之间，当前: {len(symbol)}"
    
    # 检查字符（仅允许字母、数字、点号、短横线）
    if not re.match(r'^[A-Z0-9\.\-]+$', symbol):
        return False, f"股票代码只能包含字母、数字、点号和短横线"
    
    # 检查是否以数字开头（通常无效）
    if symbol[0].isdigit():
        return False, f"股票代码不能以数字开头"
    
    return True, symbol


def normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码（无验证版本，用于内部快速处理）
    
    Args:
        symbol: 股票代码
        
    Returns:
        标准化后的代码
    """
    if not symbol:
        return "UNKNOWN"
    
    return symbol.strip().upper()