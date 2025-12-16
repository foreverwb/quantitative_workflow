"""
RuntimeLabel 构建器 v3.1

基于 code0_cmdlist.py 的命令定义
支持文件名格式: !cmd symbol param1 param2 ... .png
支持 iv_path 时间戳排序和聚合规则生成
支持 confidence_source 配置
"""

import re
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from loguru import logger


@dataclass
class RuntimeLabel:
    """RuntimeLabel 数据类"""
    CMD: str
    SYMBOL: str
    TIMEFRAME_ROLE: str
    STRUCTURE_ROLE: Optional[str] = None
    INDEX_CONTEXT: Optional[bool] = None  # 指数上下文标识
    SYMBOL_POLICY: Optional[Dict[str, Any]] = None  # 新增：symbol 策略
    PARAMS: Dict[str, Any] = field(default_factory=dict)
    PARAM_HINTS: Dict[str, str] = field(default_factory=dict)
    WRITE_TARGET: Optional[Dict[str, str]] = None  # 新增：写入目标
    FIELD_POLICY: Dict[str, List[str]] = field(default_factory=dict)
    EXTRACT_FIELDS: List[str] = field(default_factory=list)
    ALLOWED_FIELDS: Optional[List[str]] = None  # 简化的 allowed_fields
    # 聚合角色字段
    AGGREGATION_ROLE: Optional[Dict[str, Any]] = None
    # 时间戳字段（用于 iv_path 排序）
    TIMESTAMP: Optional[str] = None
    # 置信度来源配置
    CONFIDENCE_SOURCE: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        data = asdict(self)
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def to_compact_json(self) -> str:
        data = asdict(self)
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    
    def to_model_label(self) -> Dict[str, Any]:
        """生成传给模型的简化 label 格式"""
        label = {
            "cmd": self.CMD.lower(),
            "symbol": self.SYMBOL
        }
        
        # 添加 index_context 标识
        if self.INDEX_CONTEXT:
            label["index_context"] = True
        
        # 添加 allowed_fields
        if self.ALLOWED_FIELDS:
            label["allowed_fields"] = self.ALLOWED_FIELDS
        elif self.FIELD_POLICY and self.FIELD_POLICY.get('ALLOWED_FIELDS'):
            label["allowed_fields"] = self.FIELD_POLICY['ALLOWED_FIELDS']
        
        return label
    
    def to_prompt_text(self) -> str:
        """生成用于 prompt 的文本格式"""
        lines = [
            f"=== RUNTIME LABEL: {self.CMD} ===",
            f"CMD: {self.CMD}",
            f"SYMBOL: {self.SYMBOL}",
        ]
        
        # 添加 index_context 标识
        if self.INDEX_CONTEXT:
            lines.append(f"INDEX_CONTEXT: true")
        
        # 添加 symbol_policy
        if self.SYMBOL_POLICY:
            lines.append("SYMBOL_POLICY:")
            lines.append(f"  MODE: {self.SYMBOL_POLICY.get('MODE', 'dynamic')}")
            if self.SYMBOL_POLICY.get('ALLOWED'):
                lines.append(f"  ALLOWED: {self.SYMBOL_POLICY['ALLOWED']}")
        
        lines.append(f"TIMEFRAME_ROLE: {self.TIMEFRAME_ROLE}")
        lines.append(f"STRUCTURE_ROLE: {self.STRUCTURE_ROLE}")
        
        if self.PARAMS:
            lines.append("PARAMS:")
            for k, v in self.PARAMS.items():
                lines.append(f"  {k}: {v}")
        
        if self.PARAM_HINTS:
            lines.append("PARAM_HINTS:")
            for k, v in self.PARAM_HINTS.items():
                lines.append(f"  {k}: {v}")
        
        # 添加 write_target
        if self.WRITE_TARGET:
            lines.append("WRITE_TARGET:")
            for k, v in self.WRITE_TARGET.items():
                lines.append(f"  {k}: {v}")
        
        if self.FIELD_POLICY:
            lines.append("FIELD_POLICY:")
            if self.FIELD_POLICY.get('ALLOWED_FIELDS'):
                lines.append(f"  ALLOWED_FIELDS: {self.FIELD_POLICY['ALLOWED_FIELDS']}")
            if self.FIELD_POLICY.get('FORBIDDEN_FIELDS'):
                lines.append(f"  FORBIDDEN_FIELDS: {self.FIELD_POLICY['FORBIDDEN_FIELDS']}")
        
        if self.EXTRACT_FIELDS:
            lines.append("EXTRACT_FIELDS:")
            for f in self.EXTRACT_FIELDS:
                lines.append(f"  - {f}")
        
        if self.CONFIDENCE_SOURCE:
            lines.append("CONFIDENCE_SOURCE:")
            lines.append(f"  TYPE: {self.CONFIDENCE_SOURCE.get('TYPE', 'unknown')}")
            if self.CONFIDENCE_SOURCE.get('ALLOWED_SIGNALS'):
                lines.append(f"  ALLOWED_SIGNALS: {self.CONFIDENCE_SOURCE['ALLOWED_SIGNALS']}")
            if self.CONFIDENCE_SOURCE.get('FORBIDDEN_SIGNALS'):
                lines.append(f"  FORBIDDEN_SIGNALS: {self.CONFIDENCE_SOURCE['FORBIDDEN_SIGNALS']}")
        
        if self.TIMESTAMP:
            lines.append(f"TIMESTAMP: {self.TIMESTAMP}")
        
        return "\n".join(lines)


@dataclass
class AggregationBlock:
    """聚合规则块"""
    NAME: str
    INPUT_SOURCE: Dict[str, Any]
    WINDOW: Dict[str, Any]
    DECISION_RULE: List[Dict[str, str]]
    CONFIDENCE_RULE: Dict[str, str]
    
    def to_prompt_text(self) -> str:
        """生成用于 prompt 的聚合规则文本"""
        lines = [
            f"=== RUNTIME AGGREGATION: {self.NAME} ===",
            f"NAME: {self.NAME}",
            f"INPUT_SOURCE: CMD={self.INPUT_SOURCE.get('cmd')} FIELD={self.INPUT_SOURCE.get('field')} REQUIRE_TIMESTAMP={self.INPUT_SOURCE.get('require_timestamp', False)}",
            "WINDOW:",
            f"  SIZE: {self.WINDOW.get('size', 3)}",
            f"  ORDER: {self.WINDOW.get('order', 'desc')}",
            "DECISION_RULE:"
        ]
        
        for rule in self.DECISION_RULE:
            lines.append(f"  - If {rule.get('condition')} => {rule.get('result')}")
        
        lines.append("CONFIDENCE_RULE:")
        for level, desc in self.CONFIDENCE_RULE.items():
            lines.append(f"  - {level}: {desc}")
        
        return "\n".join(lines)


class RuntimeLabelBuilder:
    """RuntimeLabel 构建器"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "runtime_label_config.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        self.index_symbols = set(self.config.get("index_symbols", ["SPX", "QQQ", "IWM", "DIA"]))
        
        # DTE 范围配置
        dte_ranges = self.config.get("dte_ranges", {})
        self.short_max = dte_ranges.get("short_max", 21)
        self.mid_max = dte_ranges.get("mid_max", 45)
        
        logger.debug(f"RuntimeLabelBuilder 初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.debug(f"✅ 加载配置: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ 加载配置失败: {e}")
            return {"commands": {}, "index_symbols": ["SPX", "QQQ"]}
    
    def parse_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        解析文件名
        
        支持格式:
        1. !cmd symbol param1 param2 ... .png
        2. {symbol}_iv_path_{timestamp}.png
        """
        name = Path(filename).stem
        
        # 尝试 IV Path 格式
        result = self._parse_iv_path(name)
        if result:
            return result
        
        # 尝试命令格式
        result = self._parse_command_format(name)
        if result:
            return result
        
        logger.warning(f"⚠️ 无法解析文件名: {filename}")
        return None
    
    def _parse_iv_path(self, name: str) -> Optional[Dict[str, Any]]:
        """解析 {symbol}_iv_path_{timestamp}"""
        match = re.match(r'^([A-Za-z]+)_iv_path_(\d{8}T\d{6})$', name, re.IGNORECASE)
        if match:
            symbol = match.group(1).upper()
            timestamp_str = match.group(2)
            
            # 解析时间戳为 ISO 格式
            try:
                dt = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S")
                iso_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                iso_timestamp = timestamp_str
            
            return {
                'cmd': 'iv_path_image',
                'symbol': symbol,
                'is_index': symbol in self.index_symbols,
                'timestamp': iso_timestamp,
                'timestamp_raw': timestamp_str
            }
        return None
    
    def _parse_command_format(self, name: str) -> Optional[Dict[str, Any]]:
        """解析 !cmd symbol param1 param2 ..."""
        clean_name = name.lstrip('!')
        parts = clean_name.split()
        
        if len(parts) < 2:
            return None
        
        cmd = parts[0].lower()
        symbol = parts[1].upper()
        
        result = {
            'cmd': cmd,
            'symbol': symbol,
            'is_index': symbol in self.index_symbols
        }
        
        try:
            if cmd == 'gexr':
                # !gexr AAPL 35 45 w
                if len(parts) >= 5:
                    result['strikes'] = int(parts[2])
                    result['dte'] = int(parts[3])
                    result['filter'] = parts[4].lower()
                    
            elif cmd == 'gexn':
                # !gexn AAPL 60 98
                if len(parts) >= 4:
                    result['window'] = int(parts[2])
                    result['percentile'] = int(parts[3])
                    
            elif cmd == 'trigger':
                # !trigger AAPL 60
                if len(parts) >= 3:
                    result['window'] = int(parts[2])
                    
            elif cmd == 'vanna':
                # !vanna AAPL ntm 60 m
                if len(parts) >= 5:
                    result['moneyness'] = parts[2].lower()
                    result['window'] = int(parts[3])
                    result['unit'] = parts[4].lower()
                    
            elif cmd == 'dexn':
                # !dexn AAPL 35 45 w
                if len(parts) >= 5:
                    result['strikes'] = int(parts[2])
                    result['dte'] = int(parts[3])
                    result['filter'] = parts[4].lower()
                    
            elif cmd == 'skew':
                # !skew AAPL ivmid atm 14 [m]
                if len(parts) >= 5:
                    result['iv_type'] = parts[2].lower()
                    result['strike_ref'] = parts[3].lower()
                    result['dte'] = int(parts[4])
                    if len(parts) >= 6:
                        result['filter'] = parts[5].lower()
                        
            elif cmd == 'volumen':
                # !volumen AAPL 35 21 w
                if len(parts) >= 5:
                    result['strikes'] = int(parts[2])
                    result['dte'] = int(parts[3])
                    result['filter'] = parts[4].lower()
                    
            elif cmd == 'vexn':
                # !vexn AAPL 35 45 w
                if len(parts) >= 5:
                    result['strikes'] = int(parts[2])
                    result['dte'] = int(parts[3])
                    result['filter'] = parts[4].lower()
            
            logger.debug(f"📄 解析: {name} → {result}")
            return result
            
        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ 解析失败: {name}, {e}")
            return None
    
    def _get_config_key(self, parsed: Dict[str, Any]) -> str:
        """根据解析结果确定配置键"""
        cmd = parsed.get('cmd', '')
        is_index = parsed.get('is_index', False)
        
        # IV Path 图片
        if cmd == 'iv_path_image':
            return 'iv_path_image'
        
        # 指数
        if is_index:
            if cmd == 'gexn':
                return 'gexn_index'
            elif cmd == 'skew':
                return 'skew_index'
        
        # gexr 统一使用一个配置
        if cmd == 'gexr':
            return 'gexr'
        
        # 其他命令直接返回
        return cmd
    
    INDEX_SYMBOLS = {'SPX', 'QQQ'}
    
    def build_label(self, filename: str, symbol: str = None) -> Optional[RuntimeLabel]:
        """构建 RuntimeLabel"""
        parsed = self.parse_filename(filename)
        if not parsed:
            return None
        
        config_key = self._get_config_key(parsed)
        cmd_config = self.config.get('commands', {}).get(config_key)
        
        if not cmd_config:
            logger.warning(f"⚠️ 未找到配置: {config_key}")
            cmd_config = self.config.get('default_label', {})
        
        # 构建 PARAMS
        params = {}
        params_mapping = cmd_config.get('params_mapping', {})
        
        for param_key, source in params_mapping.items():
            if isinstance(source, str) and source in parsed:
                params[param_key] = parsed[source]
            elif isinstance(source, str):
                params[param_key] = source
            elif isinstance(source, bool):
                params[param_key] = source
            elif isinstance(source, (int, float)):
                params[param_key] = source
        
        # 处理指数占位符
        field_policy = cmd_config.get('field_policy', {})
        extract_fields = cmd_config.get('extract_fields', [])
        
        if parsed.get('is_index'):
            index_name = parsed.get('symbol', 'SPX')
            field_policy = self._replace_placeholder(field_policy, '{INDEX}', index_name)
            extract_fields = [f.replace('{INDEX}', index_name) for f in extract_fields]
        
        # 修复：确定最终 symbol
        parsed_symbol = parsed.get('symbol', 'UNKNOWN').upper()
        index_context = cmd_config.get('index_context')
        
        # 判断是否为指数：配置标记 或 symbol 在指数列表中
        is_index = index_context or (parsed_symbol in self.INDEX_SYMBOLS)
        
        if is_index:
            # 指数：必须使用文件名中解析的 symbol
            final_symbol = parsed_symbol
        else:
            # 非指数：优先使用外部传入的 symbol，其次使用文件名中的 symbol
            final_symbol = symbol or parsed_symbol
        
        # 提取 symbol_policy 配置
        symbol_policy = None
        sp_config = cmd_config.get('symbol_policy')
        if sp_config:
            symbol_policy = {
                'MODE': sp_config.get('mode', 'dynamic'),
                'ALLOWED': sp_config.get('allowed', [])
            }
        
        # 提取 write_target 配置
        write_target = None
        wt_config = cmd_config.get('write_target')
        if wt_config:
            write_target = {
                'ROOT': wt_config.get('root', 'targets')
            }
        
        # 提取聚合角色配置
        aggregation_role = None
        agg_config = cmd_config.get('aggregation_role')
        if agg_config:
            aggregation_role = {
                'PARTICIPATES_IN': agg_config.get('participates_in', []),
                'AGGREGATION_KEY': agg_config.get('aggregation_key', [])
            }
        
        # 提取时间戳
        timestamp = parsed.get('timestamp')
        
        # 提取置信度来源配置
        confidence_source = None
        conf_config = cmd_config.get('confidence_source')
        if conf_config:
            confidence_source = {
                'TYPE': conf_config.get('type', 'unknown'),
                'ALLOWED_SIGNALS': conf_config.get('allowed_signals', []),
                'FORBIDDEN_SIGNALS': conf_config.get('forbidden_signals', [])
            }
        
        # 自动设置 index_context（基于 symbol 判断）
        final_index_context = is_index if is_index else index_context
        
        label = RuntimeLabel(
            CMD=cmd_config.get('cmd', parsed.get('cmd', 'unknown')),
            SYMBOL=final_symbol.upper(),
            TIMEFRAME_ROLE=cmd_config.get('timeframe_role', 'tactical'),
            STRUCTURE_ROLE=cmd_config.get('structure_role'),
            INDEX_CONTEXT=final_index_context,
            SYMBOL_POLICY=symbol_policy,
            PARAMS=params,
            PARAM_HINTS=cmd_config.get('param_hints', {}),
            WRITE_TARGET=write_target,
            FIELD_POLICY={
                'ALLOWED_FIELDS': field_policy.get('allowed_fields', []),
                'FORBIDDEN_FIELDS': field_policy.get('forbidden_fields', [])
            },
            EXTRACT_FIELDS=extract_fields,
            ALLOWED_FIELDS=field_policy.get('allowed_fields', []),
            AGGREGATION_ROLE=aggregation_role,
            TIMESTAMP=timestamp,
            CONFIDENCE_SOURCE=confidence_source
        )
        
        logger.debug(f"✅ Label: {filename} → CMD={label.CMD}, SYMBOL={label.SYMBOL}, INDEX={is_index}")
        return label
    
    def _replace_placeholder(self, field_policy: Dict, placeholder: str, value: str) -> Dict:
        result = {}
        for key, fields in field_policy.items():
            if isinstance(fields, list):
                result[key] = [f.replace(placeholder, value) for f in fields]
            else:
                result[key] = fields
        return result
    
    def build_labels_batch(self, image_paths: List[Path], symbol: str = None) -> List[Tuple[Path, Optional[RuntimeLabel]]]:
        """批量构建 RuntimeLabel"""
        return [(path, self.build_label(path.name, symbol)) for path in image_paths]
    
    def sort_iv_path_images(self, image_paths: List[Path]) -> List[Path]:
        """
        按时间戳排序 iv_path 图片（降序，最新的在前）
        
        Args:
            image_paths: 图片路径列表
            
        Returns:
            排序后的路径列表
        """
        iv_path_images = []
        other_images = []
        
        for path in image_paths:
            parsed = self.parse_filename(path.name)
            if parsed and parsed.get('cmd') == 'iv_path_image':
                timestamp_raw = parsed.get('timestamp_raw', '')
                iv_path_images.append((path, timestamp_raw))
            else:
                other_images.append(path)
        
        # 按时间戳降序排序
        iv_path_images.sort(key=lambda x: x[1], reverse=True)
        
        # 返回排序后的列表：其他图片在前，iv_path 图片按时间降序在后
        sorted_paths = other_images + [p[0] for p in iv_path_images]
        
        logger.debug(f"📊 iv_path 排序结果: {[p.name for p in sorted_paths]}")
        return sorted_paths
    
    def build_aggregation_block(self, aggregation_name: str) -> Optional[AggregationBlock]:
        """
        构建聚合规则块
        
        Args:
            aggregation_name: 聚合规则名称（如 'iv_path'）
            
        Returns:
            AggregationBlock 实例
        """
        agg_rules = self.config.get('aggregation_rules', {})
        rule_config = agg_rules.get(aggregation_name)
        
        if not rule_config:
            logger.warning(f"⚠️ 未找到聚合规则: {aggregation_name}")
            return None
        
        return AggregationBlock(
            NAME=rule_config.get('name', aggregation_name),
            INPUT_SOURCE=rule_config.get('input_source', {}),
            WINDOW=rule_config.get('window', {'size': 3, 'order': 'desc'}),
            DECISION_RULE=rule_config.get('decision_rule', []),
            CONFIDENCE_RULE=rule_config.get('confidence_rule', {})
        )
    
    def format_label_for_prompt(self, label: RuntimeLabel) -> str:
        """生成用于 prompt 的 RuntimeLabel 文本"""
        return label.to_prompt_text()
    
    def build_request_content(
        self, 
        image_paths: List[Path], 
        symbol: str = None,
        image_url_prefix: str = "https://your.cdn/"
    ) -> List[Dict[str, Any]]:
        """
        构建视觉模型请求的 content 列表
        
        Args:
            image_paths: 图片路径列表
            symbol: 股票代码
            image_url_prefix: 图片 URL 前缀
            
        Returns:
            符合 API 格式的 content 列表
        """
        # 1. 排序图片（iv_path 按时间戳排序）
        sorted_paths = self.sort_iv_path_images(image_paths)
        
        # 2. 构建每个图片的 content
        content_list = []
        aggregation_needed = set()
        
        for path in sorted_paths:
            label = self.build_label(path.name, symbol)
            if not label:
                continue
            
            # 添加 RuntimeLabel 文本和图片
            content_list.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": label.to_prompt_text()
                    },
                    {
                        "type": "input_image",
                        "image_url": f"{image_url_prefix}{path.name}"
                    }
                ]
            })
            
            # 收集需要的聚合规则
            if label.AGGREGATION_ROLE:
                for agg_name in label.AGGREGATION_ROLE.get('PARTICIPATES_IN', []):
                    aggregation_needed.add(agg_name)
        
        # 3. 添加聚合规则块
        for agg_name in aggregation_needed:
            agg_block = self.build_aggregation_block(agg_name)
            if agg_block:
                content_list.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": agg_block.to_prompt_text()
                        }
                    ]
                })
        
        return content_list


# 便捷函数
def build_runtime_label(filename: str, symbol: str = None) -> Optional[RuntimeLabel]:
    return RuntimeLabelBuilder().build_label(filename, symbol)


def build_runtime_labels(image_paths: List[Path], symbol: str = None) -> List[Tuple[Path, Optional[RuntimeLabel]]]:
    return RuntimeLabelBuilder().build_labels_batch(image_paths, symbol)


def sort_iv_path_images(image_paths: List[Path]) -> List[Path]:
    return RuntimeLabelBuilder().sort_iv_path_images(image_paths)


def build_request_content(
    image_paths: List[Path], 
    symbol: str = None,
    image_url_prefix: str = "https://your.cdn/"
) -> List[Dict[str, Any]]:
    return RuntimeLabelBuilder().build_request_content(image_paths, symbol, image_url_prefix)
