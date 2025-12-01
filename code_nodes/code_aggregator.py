"""
CODE_AGGREGATOR - 数据聚合节点（重构版）
职责：仅负责多次上传数据的增量合并
验证和计算由 Calculator 节点负责
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Any
from pathlib import Path


def check_data_completeness(target: dict) -> dict:
    """
    检查原始数据完整性（与 JSON Schema 保持一致）
    
    检查字段：
    1. targets.symbol
    2. targets.spot_price
    3. targets.walls (4个字段)
    4. targets.gamma_metrics (11个字段)
    5. targets.directional_metrics (5个字段)
    6. targets.atm_iv (3个字段)
    
    总计：23个原始字段（不包括计算字段）
    
    Args:
        target: targets 字典
        
    Returns:
        {
            "is_complete": bool,
            "missing_fields": [],
            "total_required": 23,
            "provided": int
        }
    """
    missing_fields = []
    
    # 1. 顶层字段
    if not is_valid_value(target.get("symbol")):
        missing_fields.append("symbol")
    if not is_valid_value(target.get("spot_price")):
        missing_fields.append("spot_price")
    
    # 2. walls (4个字段)
    walls = target.get("walls", {})
    for field in ["call_wall", "put_wall", "major_wall", "major_wall_type"]:
        if not is_valid_value(walls.get(field)):
            missing_fields.append(f"walls.{field}")
    
    # 3. gamma_metrics (11个字段)
    gamma = target.get("gamma_metrics", {})
    for field in ["vol_trigger", "spot_vs_trigger", "net_gex", 
                  "gap_distance_dollar"]:
        if not is_valid_value(gamma.get(field)):
            missing_fields.append(f"gamma_metrics.{field}")
    
    # 检查 nearby_peak
    nearby_peak = gamma.get("nearby_peak", {})
    if not isinstance(nearby_peak, dict):
        missing_fields.append("gamma_metrics.nearby_peak")
    else:
        for field in ["price", "abs_gex"]:
            if not is_valid_value(nearby_peak.get(field)):
                missing_fields.append(f"gamma_metrics.nearby_peak.{field}")
    
    # 检查 next_cluster_peak
    next_cluster = gamma.get("next_cluster_peak", {})
    if not isinstance(next_cluster, dict):
        missing_fields.append("gamma_metrics.next_cluster_peak")
    else:
        for field in ["price", "abs_gex"]:
            if not is_valid_value(next_cluster.get(field)):
                missing_fields.append(f"gamma_metrics.next_cluster_peak.{field}")
    
    # 检查 monthly_data（可选，但如果存在需要验证结构）
    monthly_data = gamma.get("monthly_data", {})
    if monthly_data and isinstance(monthly_data, dict):
        monthly_cluster_strength = monthly_data.get("cluster_strength", {})
        if isinstance(monthly_cluster_strength, dict):
            # monthly_data 存在且结构正确，算作有效
            pass
    
    # 检查 weekl_data（可选，但如果存在需要验证结构）
    weekly_data = gamma.get("weekly_data", {})
    if weekly_data and isinstance(weekly_data, dict):
        weekly_cluster_strength = weekly_data.get("cluster_strength", {})
        if isinstance(weekly_cluster_strength, dict):
            # weekly_data 存在且结构正确，算作有效
            pass
    
    # 4. directional_metrics (5个字段)
    directional = target.get("directional_metrics", {})
    for field in ["dex_same_dir_pct", "vanna_dir", "vanna_confidence", 
                  "iv_path", "iv_path_confidence"]:
        if not is_valid_value(directional.get(field)):
            missing_fields.append(f"directional_metrics.{field}")
    
    # 5. atm_iv (3个字段)
    atm_iv = target.get("atm_iv", {})
    for field in ["iv_7d", "iv_14d", "iv_source"]:
        if not is_valid_value(atm_iv.get(field)):
            missing_fields.append(f"atm_iv.{field}")
    
    total_required = 23  # 23个原始字段
    provided = total_required - len(missing_fields)
    
    return {
        "is_complete": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "total_required": total_required,
        "provided": provided,
        "completion_rate": int((provided / total_required) * 100)
    }


def smart_merge(first_data: dict, new_data: dict) -> Tuple[dict, dict]:
    """
    智能增量合并
    
    Args:
        first_data: 历史数据
        new_data: 新数据
        
    Returns:
        (merged_data, merge_info)
    """
    merged = first_data.copy()
    
    # 提取 targets
    first_targets = get_target_dict(first_data)
    new_targets = get_target_dict(new_data)
    
    # 检测新数据是否为空
    new_valid_count = count_valid_fields_in_dict(new_targets)
    
    if new_valid_count == 0:
        print("⚠️ 警告: 新数据无有效字段,跳过合并")
        merge_info = {
            "new_fields_count": 0,
            "updated_fields_count": 0,
            "merge_failed": True,
            "failure_reason": "新数据无有效字段"
        }
        return merged, merge_info
    
    # 统计信息
    new_fields_count = 0
    updated_fields_count = 0
    
    # 合并各个 section
    for section in ["gamma_metrics", "directional_metrics", "atm_iv", "walls"]:
        if section not in first_targets:
            first_targets[section] = {}
        
        if section in new_targets:
            for key, new_value in new_targets[section].items():
                old_value = first_targets[section].get(key)
                
                if is_valid_value(new_value):
                    if not is_valid_value(old_value):
                        first_targets[section][key] = new_value
                        new_fields_count += 1
                    elif old_value != new_value:
                        first_targets[section][key] = new_value
                        updated_fields_count += 1
    
    # 合并顶层字段
    for key in ["spot_price", "symbol"]:
        old_value = first_targets.get(key)
        new_value = new_targets.get(key)
        
        if is_valid_value(new_value):
            if not is_valid_value(old_value):
                first_targets[key] = new_value
                new_fields_count += 1
            elif old_value != new_value:
                first_targets[key] = new_value
                updated_fields_count += 1
    
    if new_fields_count == 0 and updated_fields_count == 0:
        print("⚠️ 警告: 合并未产生任何变化")
        merge_info = {
            "new_fields_count": 0,
            "updated_fields_count": 0,
            "merge_failed": True,
            "failure_reason": "无新增或更新字段"
        }
        return merged, merge_info
    
    # 更新 targets
    merged["targets"] = first_targets
    
    merge_info = {
        "new_fields_count": new_fields_count,
        "updated_fields_count": updated_fields_count,
        "merge_failed": False
    }
    
    return merged, merge_info


def get_target_dict(data: Dict) -> Dict:
    """提取 targets 字典"""
    targets = data.get("targets")
    
    # 优先级1: 直接是字典
    if isinstance(targets, dict) and targets:
        return targets
    
    # 优先级2: 非空列表
    if isinstance(targets, list) and targets:
        return targets[0] if isinstance(targets[0], dict) else {}
    
    # 优先级3: 回退到根节点
    if "spot_price" in data or "symbol" in data:
        print("⚠️ targets字段缺失，尝试从根节点读取")
        return data
    
    print(f"❌ 无法提取targets，类型: {type(targets)}")
    return {}


def is_valid_value(value: Any) -> bool:
    """判断值是否有效（非缺失值）"""
    if value is None:
        return False
    if value == -999:
        return False
    if value in ["N/A", "数据不足", "", "unknown"]:
        return False
    return True


def count_valid_fields_in_dict(target_dict: dict) -> int:
    """统计字典中的有效字段数量"""
    count = 0
    
    # 标准嵌套结构
    for section in ["gamma_metrics", "directional_metrics", "atm_iv", "walls"]:
        if section in target_dict and isinstance(target_dict[section], dict):
            for value in target_dict[section].values():
                if is_valid_value(value):
                    count += 1
    
    # 检查顶层字段
    for key in ["spot_price"]:
        if is_valid_value(target_dict.get(key)):
            count += 1
    
    return count


def extract_symbol(data: dict) -> str:
    """提取股票代码"""
    target = get_target_dict(data)
    return target.get("symbol", data.get("symbol", "UNKNOWN"))


def format_merge_history(history: list) -> str:
    """格式化合并历史"""
    if not history:
        return "无历史记录"
    
    lines = []
    for record in history:
        lines.append(
            f"第{record['round']}轮 ({record['timestamp']}): "
            f"{record['action']}, "
            f"新增 {record.get('fields_added', 0)} 个字段"
        )
    return "\n".join(lines)


def main(
    agent3_output: dict,
    symbol: str,
    **env_vars
) -> dict:
    """
    数据聚合节点入口（重构版）
    
    职责：
    1. 加载历史缓存（如果存在）
    2. 合并新旧数据
    3. 检查数据完整性并给出提示
    4. 返回合并后的数据
    
    Args:
        agent3_output: Agent3 输出
        symbol: 股票代码
        **env_vars: 环境变量
        
    Returns:
        {"result": 合并后的数据 JSON 字符串, "completeness": 完整性信息}
    """
    try:
        
        current_data = agent3_output
        
        # 加载历史缓存
        cache_dir = Path("data/temp")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{symbol}_partial.json"
        
        if cache_file.exists():
            print(f"📂 发现历史缓存，进入增量合并模式")
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            first_data = cached.get("data", {})
            merged_data, merge_info = smart_merge(first_data, current_data)
            
            # 更新合并历史
            history = cached.get("merge_history", [])
            history.append({
                "round": len(history) + 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fields_added": merge_info["new_fields_count"],
                "fields_updated": merge_info.get("updated_fields_count", 0),
                "action": "增量补齐" if not merge_info.get("merge_failed") else "合并失败",
                "failure_reason": merge_info.get("failure_reason", "")
            })
            merged_data["_merge_history"] = history
            
            merge_log = format_merge_history(history)
            
        else:
            print(f"✨ 首次解析，初始化缓存")
            merged_data = current_data
            merge_history = [{
                "round": 1,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fields_added": count_valid_fields_in_dict(get_target_dict(current_data)),
                "action": "首次解析"
            }]
            merged_data["_merge_history"] = merge_history
            merge_log = format_merge_history(merge_history)
        
        # 检查数据完整性
        target = get_target_dict(merged_data)
        completeness = check_data_completeness(target)
        
        if not completeness["is_complete"]:
            missing_count = len(completeness["missing_fields"])
            print(f"⚠️ 数据不完整，缺失 {missing_count} 个字段:")
            for field in completeness["missing_fields"][:5]:  # 只显示前5个
                print(f"   - {field}")
            if missing_count > 5:
                print(f"   ... 还有 {missing_count - 5} 个字段")
            print(f"   完成度: {completeness['completion_rate']}% ({completeness['provided']}/{completeness['total_required']})")
        else:
            print(f"✅ 原始数据完整 ({completeness['provided']}/{completeness['total_required']} 字段)")
        
        # 保存缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                "symbol": symbol,
                "data": merged_data,
                "merge_history": merged_data.get("_merge_history", []),
                "completeness": completeness,
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 数据聚合完成，已保存到 {cache_file}")
        
        # 返回结果
        return {
            "result": json.dumps(merged_data, ensure_ascii=False, indent=2),
            "merge_log": merge_log,
            "completeness": completeness,
            "symbol": symbol
        }
    
    except Exception as e:
        import traceback
        return {
            "result": json.dumps({
                "error": True,
                "error_message": str(e),
                "error_traceback": traceback.format_exc()
            }, ensure_ascii=False, indent=2)
        }