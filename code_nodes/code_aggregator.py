"""
CODE_AGGREGATOR - 数据聚合节点（重构版 v2.0）
职责：
1. 增量合并数据
2. [新增] 时间序列分析 (Delta Metrics)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from pathlib import Path
import traceback
from loguru import logger

def check_data_completeness(target: dict) -> dict:
    missing_fields = []
    validation_missing = []
    
    # 1. 顶层字段
    if not is_valid_value(target.get("symbol")): missing_fields.append("symbol")
    if not is_valid_value(target.get("spot_price")): missing_fields.append("spot_price")
    
    # 2. walls (4个字段)
    walls = target.get("walls", {})
    for field in ["call_wall", "put_wall", "major_wall"]:
        if not is_valid_value(walls.get(field)):
            missing_fields.append(f"walls.{field}")
    
    # 3. gamma_metrics (12个字段)
    gamma = target.get("gamma_metrics", {})
    for field in ["vol_trigger", "spot_vs_trigger", "net_gex", "gap_distance_dollar"]:
        if not is_valid_value(gamma.get(field)):
            missing_fields.append(f"gamma_metrics.{field}")
    
    nearby_peak = gamma.get("nearby_peak", {})
    if not isinstance(nearby_peak, dict):
        missing_fields.append("gamma_metrics.nearby_peak.price")
        missing_fields.append("gamma_metrics.nearby_peak.abs_gex")
    else:
        for field in ["price", "abs_gex"]:
            if not is_valid_value(nearby_peak.get(field)):
                missing_fields.append(f"gamma_metrics.nearby_peak.{field}")
    
    next_cluster = gamma.get("next_cluster_peak", {})
    if not isinstance(next_cluster, dict):
        missing_fields.append("gamma_metrics.next_cluster_peak.price")
        missing_fields.append("gamma_metrics.next_cluster_peak.abs_gex")
    else:
        for field in ["price", "abs_gex"]:
            if not is_valid_value(next_cluster.get(field)):
                missing_fields.append(f"gamma_metrics.next_cluster_peak.{field}")
    
    monthly_data = gamma.get("monthly_data", {})
    if not isinstance(monthly_data, dict):
        missing_fields.append("gamma_metrics.monthly_data.cluster_strength.price")
        missing_fields.append("gamma_metrics.monthly_data.cluster_strength.abs_gex")
    else:
        monthly_cluster = monthly_data.get("cluster_strength", {})
        if not isinstance(monthly_cluster, dict):
            missing_fields.append("gamma_metrics.monthly_data.cluster_strength.price")
            missing_fields.append("gamma_metrics.monthly_data.cluster_strength.abs_gex")
        else:
            for field in ["price", "abs_gex"]:
                if not is_valid_value(monthly_cluster.get(field)):
                    missing_fields.append(f"gamma_metrics.monthly_data.cluster_strength.{field}")
    
    weekly_data = gamma.get("weekly_data", {})
    if not isinstance(weekly_data, dict):
        missing_fields.append("gamma_metrics.weekly_data.cluster_strength.price")
        missing_fields.append("gamma_metrics.weekly_data.cluster_strength.abs_gex")
    else:
        weekly_cluster = weekly_data.get("cluster_strength", {})
        if not isinstance(weekly_cluster, dict):
            missing_fields.append("gamma_metrics.weekly_data.cluster_strength.price")
            missing_fields.append("gamma_metrics.weekly_data.cluster_strength.abs_gex")
        else:
            for field in ["price", "abs_gex"]:
                if not is_valid_value(weekly_cluster.get(field)):
                    missing_fields.append(f"gamma_metrics.weekly_data.cluster_strength.{field}")
    
    # 4. directional_metrics
    directional = target.get("directional_metrics", {})
    for field in ["dex_same_dir_pct", "vanna_dir", "vanna_confidence", "iv_path", "iv_path_confidence"]:
        if not is_valid_value(directional.get(field)):
            missing_fields.append(f"directional_metrics.{field}")
    
    # 5. atm_iv
    atm_iv = target.get("atm_iv", {})
    for field in ["iv_7d", "iv_14d", "iv_source"]:
        if not is_valid_value(atm_iv.get(field)):
            missing_fields.append(f"atm_iv.{field}")
    
    # 6. validation_metrics
    validation_metrics = target.get("validation_metrics", {})
    validation_fields = ["net_volume_signal", "net_vega_exposure"]
    
    if not validation_metrics or not isinstance(validation_metrics, dict):
        for field in validation_fields:
            validation_missing.append({
                "field": field, 
                "path": f"validation_metrics.{field}", 
                "severity": "high",
                "reason": "validation_metrics 对象缺失"
            })
    else:
        for field in validation_fields:
            if field not in validation_metrics:
                validation_missing.append({
                    "field": field, 
                    "path": f"validation_metrics.{field}", 
                    "severity": "high",
                    "reason": "字段缺失"
                })
    
    core_required = 26
    core_provided = 26 - len(missing_fields)
    validation_provided = 4 - len(validation_missing)
    total_required = 30
    total_provided = core_provided + validation_provided
    
    return {
        "is_complete": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "validation_missing": validation_missing,
        "core_required": core_required,
        "total_required": total_required,
        "core_provided": core_provided,
        "provided": total_provided,
        "completion_rate": int((core_provided / core_required) * 100) if core_required > 0 else 0,
        "validation_rate": int((validation_provided / 4) * 100)
    }

def smart_merge(first_data: dict, new_data: dict) -> Tuple[dict, dict]:
    merged = first_data.copy()
    first_targets = get_target_dict(first_data)
    new_targets = get_target_dict(new_data)
    
    new_valid_count = count_valid_fields_in_dict(new_targets)
    if new_valid_count == 0:
        return merged, {"new_fields_count": 0, "updated_fields_count": 0, "merge_failed": True, "failure_reason": "新数据无有效字段"}
    
    new_fields_count = 0
    updated_fields_count = 0
    
    sections = ["gamma_metrics", "directional_metrics", "atm_iv", "walls", "validation_metrics"]
    for section in sections:
        if section not in first_targets:
            first_targets[section] = {}
        
        if section in new_targets:
            for key, new_value in new_targets[section].items():
                old_value = first_targets[section].get(key)
                if section == "validation_metrics":
                    if key not in first_targets[section]:
                        first_targets[section][key] = new_value
                        new_fields_count += 1
                    elif old_value != new_value and new_value is not None:
                        first_targets[section][key] = new_value
                        updated_fields_count += 1
                elif is_valid_value(new_value):
                    if not is_valid_value(old_value):
                        first_targets[section][key] = new_value
                        new_fields_count += 1
                    elif old_value != new_value:
                        first_targets[section][key] = new_value
                        updated_fields_count += 1
    
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
    
    merged["targets"] = first_targets
    return merged, {"new_fields_count": new_fields_count, "updated_fields_count": updated_fields_count, "merge_failed": False}

def _analyze_time_series(current_data: dict, history_cache: dict) -> dict:
    """
    [新增] 时间序列分析
    计算关键指标的日环比变化 (Delta)
    """
    delta_metrics = {}
    
    curr_targets = get_target_dict(current_data)
    curr_spot = curr_targets.get("spot_price")
    curr_gamma = curr_targets.get("gamma_metrics", {})
    
    last_data = history_cache.get("last_complete_analysis", {})
    if not last_data:
        return {}
        
    last_targets = get_target_dict(last_data)
    last_spot = last_targets.get("spot_price")
    last_gamma = last_targets.get("gamma_metrics", {})
    
    if is_valid_value(curr_spot) and is_valid_value(last_spot):
        delta_metrics["price_change_pct"] = round((curr_spot - last_spot) / last_spot * 100, 2)
    
    curr_net = curr_gamma.get("net_gex")
    last_net = last_gamma.get("net_gex")
    if is_valid_value(curr_net) and is_valid_value(last_net):
        change = curr_net - last_net
        delta_metrics["net_gex_change"] = round(change, 2)
        delta_metrics["gex_flow_note"] = "GEX累积(阻力增强)" if change > 0 else "GEX流失(阻力减弱)"
    
    curr_trig = curr_gamma.get("vol_trigger")
    last_trig = last_gamma.get("vol_trigger")
    if is_valid_value(curr_trig) and is_valid_value(last_trig):
        shift = curr_trig - last_trig
        if abs(shift) > 0:
            delta_metrics["trigger_shift"] = shift
            delta_metrics["trigger_shift_note"] = "Trigger上移(看涨)" if shift > 0 else "Trigger下移(看跌)"
            
    return delta_metrics

def main(
    agent3_output: dict,
    symbol: str,
    **env_vars
) -> dict:
    """
    聚合节点入口
    """
    try:
        if isinstance(agent3_output, str):
            current_data = json.loads(agent3_output)
        else:
            current_data = agent3_output
        
        cache_dir = Path("data/temp")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{symbol}_partial.json"
        
        cached = {}
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
            except:
                pass
        
        first_data = cached.get("data", {})
        if not first_data: 
            merged_data = current_data
            merge_info = {"action": "Initial"}
        else:
            merged_data, merge_info = smart_merge(first_data, current_data)
        
        # delta_metrics = _analyze_time_series(merged_data, cached)
        # if delta_metrics:
        #     target = get_target_dict(merged_data)
        #     target["delta_metrics"] = delta_metrics
            
        target = get_target_dict(merged_data)
        completeness = check_data_completeness(target)
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                "symbol": symbol,
                "data": merged_data,
                "last_complete_analysis": merged_data if completeness['is_complete'] else cached.get('last_complete_analysis'),
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
            
        return {
            "result": json.dumps(merged_data, ensure_ascii=False, indent=2),
            "completeness": completeness,
            "symbol": symbol,
            # "delta_analysis": delta_metrics,
            "merge_log": format_merge_history(cached.get("merge_history", [])) # Return merge log
        }
        
    except Exception as e:
        logger.error(f"❌ Aggregator 执行失败: {e}")
        logger.error(traceback.format_exc())
        return {
            "result": json.dumps({
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "trace": traceback.format_exc()
            }, ensure_ascii=False, indent=2)
        }

def get_target_dict(data: Dict) -> Dict:
    targets = data.get("targets")
    if isinstance(targets, dict) and targets: return targets
    if isinstance(targets, list) and targets: return targets[0]
    if "spot_price" in data or "symbol" in data: return data
    return {}

def is_valid_value(val: Any) -> bool:
    return val is not None and val != -999 and val not in ["N/A", ""]

def count_valid_fields_in_dict(target_dict: dict) -> int:
    count = 0
    for section in ["gamma_metrics", "directional_metrics", "atm_iv", "walls"]:
        if section in target_dict and isinstance(target_dict[section], dict):
            for value in target_dict[section].values():
                if is_valid_value(value):
                    count += 1
    validation_metrics = target_dict.get("validation_metrics", {})
    if isinstance(validation_metrics, dict):
        count += len(validation_metrics)
    for key in ["spot_price", "symbol"]:
        if is_valid_value(target_dict.get(key)):
            count += 1
    return count

def format_merge_history(history: list) -> str:
    if not history: return "无历史记录"
    lines = []
    for record in history:
        lines.append(f"第{record.get('round', '?')}轮: {record.get('action')}")
    return "\n".join(lines)