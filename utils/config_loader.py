"""
配置加载工具类
用途：
1. 加载 env_config.yaml 和 model_config.yaml
2. 提供类型安全的配置访问接口
3. 支持环境变量覆盖（优先级：环境变量 > YAML文件）
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


class ConfigLoader:
    """配置加载器（单例模式）"""
    
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all_configs()
        return cls._instance
    
    def _load_all_configs(self):
        """加载所有配置文件"""
        base_dir = Path(__file__).parent.parent
        
        # 加载环境变量配置
        env_config_path = base_dir / "config" / "env_config.yaml"
        if env_config_path.exists():
            with open(env_config_path, 'r', encoding='utf-8') as f:
                self._config['env'] = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"环境配置文件不存在: {env_config_path}")
        
        # 加载模型配置
        model_config_path = base_dir / "config" / "model_config.yaml"
        if model_config_path.exists():
            with open(model_config_path, 'r', encoding='utf-8') as f:
                self._config['models'] = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"模型配置文件不存在: {model_config_path}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）
        
        示例：
            config.get("scoring.weight_gamma_regime")  # 返回 0.4
            config.get("gamma.break_wall_threshold_low")  # 返回 0.4
        """
        keys = key_path.split('.')
        value = self._config
        
        # 首先尝试从环境变量获取（优先级最高）
        env_key = "_".join(keys).upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            return self._parse_env_value(env_value)
        
        # 从YAML配置获取
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_env(self, key_path: str, default: Any = None) -> Any:
        """获取环境变量配置（快捷方法）"""
        return self.get(f"env.{key_path}", default)
    
    def get_model_config(self, agent_name: str) -> Dict[str, Any]:
        """获取指定Agent的模型配置"""
        return self._config.get('models', {}).get('agents', {}).get(agent_name, {})
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """解析环境变量值（自动转换类型）"""
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value


# ============================================
# 全局配置实例（推荐使用方式）
# ============================================
config = ConfigLoader()


# ============================================
# 数据类：强类型配置访问（可选）
# ============================================

@dataclass
class ScoringConfig:
    """评分配置"""
    weight_gamma_regime: float
    weight_break_wall: float
    weight_direction: float
    weight_iv: float
    entry_threshold_score: float
    entry_threshold_probability: int
    
    @classmethod
    def from_config(cls):
        return cls(
            weight_gamma_regime=config.get_env("scoring.weight_gamma_regime"),
            weight_break_wall=config.get_env("scoring.weight_break_wall"),
            weight_direction=config.get_env("scoring.weight_direction"),
            weight_iv=config.get_env("scoring.weight_iv"),
            entry_threshold_score=config.get_env("scoring.entry_threshold_score"),
            entry_threshold_probability=config.get_env("scoring.entry_threshold_probability")
        )


@dataclass
class GammaConfig:
    """Gamma状态配置"""
    break_wall_threshold_low: float
    break_wall_threshold_high: float
    monthly_override_threshold: float
    cluster_strength_threshold_t: float
    cluster_strength_threshold_s: float
    
    @classmethod
    def from_config(cls):
        return cls(
            break_wall_threshold_low=config.get_env("gamma.break_wall_threshold_low"),
            break_wall_threshold_high=config.get_env("gamma.break_wall_threshold_high"),
            monthly_override_threshold=config.get_env("gamma.monthly_override_threshold"),
            cluster_strength_threshold_t=config.get_env("gamma.cluster_strength_threshold_t"),
            cluster_strength_threshold_s=config.get_env("gamma.cluster_strength_threshold_s")
        )


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    # 方式1：直接访问（推荐用于动态场景）
    print(f"Gamma权重: {config.get_env('scoring.weight_gamma_regime')}")
    print(f"破墙低阈值: {config.get_env('gamma.break_wall_threshold_low')}")
    
    # 方式2：强类型访问（推荐用于静态场景）
    scoring_cfg = ScoringConfig.from_config()
    print(f"入场评分阈值: {scoring_cfg.entry_threshold_score}")
    
    # 方式3：批量获取整个section
    all_gamma_params = config.get_env("gamma")
    print(f"所有Gamma参数: {all_gamma_params}")
    
    # 方式4：环境变量覆盖（运行时设置）
    # export SCORING_WEIGHT_GAMMA_REGIME=0.5
    # 则 config.get_env("scoring.weight_gamma_regime") 将返回 0.5