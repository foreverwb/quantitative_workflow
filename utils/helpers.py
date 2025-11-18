"""
工具函数集
常用的辅助函数、装饰器、验证器
"""

import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


# ============================================
# 1. 股票代码处理
# ============================================

def normalize_symbol(input_str: str) -> str:
    """
    标准化股票代码
    
    示例：
        "aapl us" → "AAPL"
        "TSLA" → "TSLA"
        "qqq US" → "QQQ"
    """
    # 提取大写字母序列
    match = re.search(r'\b([A-Z]{1,5})\b', input_str.upper())
    return match.group(1) if match else "UNKNOWN"


def is_stock_symbol(text: str) -> bool:
    """判断是否为股票代码"""
    pattern = r'^[A-Z]{1,5}$'
    return bool(re.match(pattern, text.upper()))


# ============================================
# 2. 文件路径处理
# ============================================

def ensure_dir(path: str) -> Path:
    """确保目录存在，不存在则创建"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_timestamp_filename(prefix: str = "", suffix: str = ".json") -> str:
    """生成带时间戳的文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{suffix}" if prefix else f"{timestamp}{suffix}"


def save_json(data: Dict, filepath: str, indent: int = 2):
    """保存JSON文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(filepath: str) -> Dict:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================
# 3. 数据验证
# ============================================

def validate_required_fields(data: Dict, required_fields: List[str]) -> tuple[bool, List[str]]:
    """
    验证必需字段
    
    Returns:
        (is_valid, missing_fields)
    """
    missing = []
    for field in required_fields:
        if '.' in field:
            # 支持嵌套字段 "gamma_metrics.net_gex"
            keys = field.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    missing.append(field)
                    break
            else:
                # 检查最终值是否有效
                if not is_valid_value(value):
                    missing.append(field)
        else:
            if field not in data or not is_valid_value(data[field]):
                missing.append(field)
    
    return len(missing) == 0, missing


def is_valid_value(value: Any) -> bool:
    """判断值是否有效（非缺失值）"""
    if value is None:
        return False
    if value == -999:
        return False
    if value in ["N/A", "数据不足", "", "unknown"]:
        return False
    return True


# ============================================
# 4. 数值计算
# ============================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法（避免除零）"""
    return numerator / denominator if denominator != 0 else default


def percentage(value: float, total: float, decimals: int = 1) -> str:
    """计算百分比字符串"""
    pct = safe_divide(value, total, 0) * 100
    return f"{pct:.{decimals}f}%"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """将值限制在指定范围内"""
    return max(min_val, min(max_val, value))


# ============================================
# 5. 日期时间处理
# ============================================

def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> Optional[datetime]:
    """解析日期字符串"""
    try:
        return datetime.strptime(date_str, fmt)
    except ValueError:
        return None


def days_until(target_date: str, from_date: Optional[str] = None) -> int:
    """计算距离目标日期的天数"""
    target = parse_date(target_date)
    if not target:
        return 0
    
    start = parse_date(from_date) if from_date else datetime.now()
    if not start:
        return 0
    
    return (target - start).days


def format_duration(seconds: float) -> str:
    """
    格式化时长
    
    示例：
        0.5 → "500ms"
        2.3 → "2.3s"
        65 → "1m 5s"
    """
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


# ============================================
# 6. 字符串处理
# ============================================

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断长文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_whitespace(text: str) -> str:
    """清理多余空白字符"""
    return re.sub(r'\s+', ' ', text).strip()


def extract_numbers(text: str) -> List[float]:
    """从文本中提取所有数字"""
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


# ============================================
# 7. 数据转换
# ============================================

def dict_to_flat(nested_dict: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    将嵌套字典展平
    
    示例：
        {"a": {"b": 1, "c": 2}} → {"a.b": 1, "a.c": 2}
    """
    items = []
    for k, v in nested_dict.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(dict_to_flat(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def flat_to_dict(flat_dict: Dict, sep: str = '.') -> Dict:
    """
    将展平字典还原为嵌套结构
    
    示例：
        {"a.b": 1, "a.c": 2} → {"a": {"b": 1, "c": 2}}
    """
    result = {}
    for key, value in flat_dict.items():
        keys = key.split(sep)
        d = result
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
    return result


# ============================================
# 8. 装饰器
# ============================================

from functools import wraps
import time

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍增因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    
                    print(f"尝试 {attempt}/{max_attempts} 失败: {str(e)}, {current_delay:.1f}秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator


def deprecated(reason: str):
    """标记函数为已弃用"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"警告: {func.__name__} 已弃用. 原因: {reason}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================
# 9. 数据结构
# ============================================

class DotDict(dict):
    """
    支持点号访问的字典
    
    示例：
        d = DotDict({'a': {'b': 1}})
        d.a.b  # 返回 1
    """
    def __getattr__(self, key):
        try:
            value = self[key]
            if isinstance(value, dict):
                return DotDict(value)
            return value
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{key}'")
    
    def __setattr__(self, key, value):
        self[key] = value


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    # 测试股票代码处理
    print(normalize_symbol("aapl us"))  # AAPL
    print(is_stock_symbol("TSLA"))      # True
    
    # 测试数据验证
    data = {"gamma_metrics": {"net_gex": 1000}, "spot": 100}
    is_valid, missing = validate_required_fields(
        data, 
        ["gamma_metrics.net_gex", "spot", "missing_field"]
    )
    print(f"验证结果: {is_valid}, 缺失字段: {missing}")
    
    # 测试字典展平
    nested = {"a": {"b": {"c": 1}}}
    flat = dict_to_flat(nested)
    print(f"展平: {flat}")  # {'a.b.c': 1}
    
    # 测试重试装饰器
    @retry(max_attempts=3, delay=0.5)
    def unstable_function():
        import random
        if random.random() < 0.7:
            raise ValueError("随机失败")
        return "成功"
    
    # print(unstable_function())