"""
配置加载工具类（重构版）
特性：
1. 自动将 YAML 转换为对象（支持点号访问）
2. 支持环境变量覆盖（自动类型转换）
3. 单例模式（全局唯一实例）
4. 无需手动映射（删除 aliases）
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class DotDict(dict):
    """支持点号访问的字典（递归）"""
    
    def __init__(self, data: Dict = None):
        super().__init__()
        if data:
            for key, value in data.items():
                self[key] = self._convert(value)
    
    def _convert(self, value):
        """递归转换嵌套字典为 DotDict"""
        if isinstance(value, dict):
            return DotDict(value)
        elif isinstance(value, list):
            return [self._convert(item) for item in value]
        return value
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"配置项不存在: {key}")
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"配置项不存在: {key}")


class ConfigLoader:
    """配置加载器（重构版）"""
    
    _instance = None
    _config: DotDict = None
    
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
                env_data = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"环境配置文件不存在: {env_config_path}")
        
        # 加载模型配置
        model_config_path = base_dir / "config" / "model_config.yaml"
        if model_config_path.exists():
            with open(model_config_path, 'r', encoding='utf-8') as f:
                model_data = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"模型配置文件不存在: {model_config_path}")
        
        # 合并配置（转换为 DotDict）
        self._config = DotDict({
            'env': env_data,
            'models': model_data
        })
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """
        自动从环境变量覆盖配置
        
        规则：
        - 环境变量格式：SECTION_KEY (大写 + 下划线)
        - 例：GAMMA_LAMBDA_K_SYS=0.6 → config.env.gamma.lambda_k_sys = 0.6
        """
        for env_key, env_value in os.environ.items():
            # 跳过系统环境变量
            if env_key.startswith('_') or env_key in ['PATH', 'HOME', 'USER']:
                continue
            
            # 尝试解析为配置路径
            parts = env_key.lower().split('_')
            if len(parts) >= 2:
                try:
                    # 构建配置路径: GAMMA_LAMBDA_K_SYS → env.gamma.lambda_k_sys
                    section = parts[0]
                    key_path = '.'.join(parts[1:])
                    
                    if section in self._config.env:
                        # 设置值（自动类型转换）
                        self._set_nested_value(
                            self._config.env[section],
                            key_path,
                            self._parse_env_value(env_value)
                        )
                except Exception:
                    pass  # 忽略无法解析的环境变量
    
    def _set_nested_value(self, obj: dict, key_path: str, value: Any):
        """设置嵌套字典的值"""
        keys = key_path.split('.')
        for key in keys[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]
        obj[keys[-1]] = value
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """解析环境变量值（自动转换类型）"""
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        elif value.lower() == 'null' or value.lower() == 'none':
            return None
        
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    
    # ============================================
    # 公共 API
    # ============================================
    
    def get_section(self, section_name: str) -> DotDict:
        """
        获取整个配置节（推荐方式）
        
        示例：
            gamma_config = config.get_section('gamma')
            k_sys = gamma_config.lambda_k_sys  # 点号访问
        
        Args:
            section_name: 配置节名称（env 下的一级键）
        
        Returns:
            DotDict 对象（支持点号访问）
        """
        section = self._config.env.get(section_name)
        if section is None:
            raise ValueError(f"配置节不存在: {section_name}")
        return section
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（点号路径，兼容旧代码）
        
        示例：
            value = config.get('gamma.lambda_k_sys', 0.5)
        
        Args:
            key_path: 配置路径（如 'gamma.lambda_k_sys'）
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self._config.env
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_env(self, key_path: str, default: Any = None) -> Any:
        """获取环境变量配置（快捷方法，等同于 get）"""
        return self.get(key_path, default)
    
    def get_model_config(self, agent_name: str) -> DotDict:
        """获取指定 Agent 的模型配置"""
        agents_config = self._config.models.get('agents', {})
        agent_config = agents_config.get(agent_name, {})
        
        if not agent_config:
            # 返回默认配置
            return self._config.models.get('default', DotDict())
        
        return DotDict(agent_config)
    
    # ============================================
    # 快捷属性访问
    # ============================================
    
    @property
    def gamma(self) -> DotDict:
        """快捷访问 gamma 配置"""
        return self.get_section('gamma')
    
    @property
    def scoring(self) -> DotDict:
        """快捷访问 scoring 配置"""
        return self.get_section('scoring')
    
    @property
    def dte(self) -> DotDict:
        """快捷访问 dte 配置"""
        return self.get_section('dte')
    
    @property
    def direction(self) -> DotDict:
        """快捷访问 direction 配置"""
        return self.get_section('direction')
    
    @property
    def strikes(self) -> DotDict:
        """快捷访问 strikes 配置"""
        return self.get_section('strikes')


# ============================================
# 全局配置实例
# ============================================
config = ConfigLoader()


# ============================================
# 配置展开工具
# ============================================

def expand_config_to_env_vars(env_vars: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 config 对象展开为 code_nodes 期望的扁平化 env_vars 格式
    
    Args:
        env_vars: 原始环境变量字典，必须包含 'config' 键
        
    Returns:
        展开后的环境变量字典（包含原有内容 + 扁平化配置）
    
    示例:
        env_vars = {'config': config, 'market_params': {...}}
        expanded = expand_config_to_env_vars(env_vars)
        # expanded['SCORE_WEIGHT_GAMMA_REGIME'] = 0.4
        # expanded['BREAK_WALL_THRESHOLD_LOW'] = 0.4
    """
    cfg = env_vars.get('config')
    if cfg is None:
        return env_vars
    
    expanded = dict(env_vars)  # 复制原有内容
    
    # ======================================
    # 1. Alpha Vantage API 配置 (code1_event_detection)
    # ======================================
    try:
        av = cfg.get_section('alpha_vantage')
        expanded['ALPHA_VANTAGE_API_KEY'] = av.get('api_key', '')
        expanded['ALPHA_VANTAGE_API_URL'] = av.get('api_url', 'https://www.alphavantage.co/query?')
        expanded['ENABLE_EARNINGS_API'] = av.get('enable_earnings_api', True)
        expanded['EARNINGS_CACHE_DAYS'] = av.get('earnings_cache_days', 90)
    except (ValueError, AttributeError):
        pass  # 配置节不存在，使用默认值
    
    # ======================================
    # 2. 评分配置 (code2_scoring)
    # ======================================
    try:
        scoring = cfg.get_section('scoring')
        expanded['SCORE_WEIGHT_GAMMA_REGIME'] = scoring.get('weight_gamma_regime', 0.4)
        expanded['SCORE_WEIGHT_BREAK_WALL'] = scoring.get('weight_break_wall', 0.3)
        expanded['SCORE_WEIGHT_DIRECTION'] = scoring.get('weight_direction', 0.2)
        expanded['SCORE_WEIGHT_IV'] = scoring.get('weight_iv', 0.1)
        expanded['ENTRY_THRESHOLD_SCORE'] = scoring.get('entry_threshold_score', 3)
        expanded['ENTRY_THRESHOLD_PROBABILITY'] = scoring.get('entry_threshold_probability', 60)
        expanded['LIGHT_POSITION_PROBABILITY'] = scoring.get('light_position_probability', 50)
        expanded['INDEX_GAP_THRESHOLD_RATIO'] = scoring.get('index_gap_threshold_ratio', 0.5)
        expanded['INDEX_CONFLICT_PENALTY'] = scoring.get('index_conflict_penalty', -1)
        expanded['INDEX_CONSISTENCY_BONUS'] = scoring.get('index_consistency_bonus', 1)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 3. Gamma 配置 (code2_scoring)
    # ======================================
    try:
        gamma = cfg.get_section('gamma')
        expanded['BREAK_WALL_THRESHOLD_LOW'] = gamma.get('break_wall_threshold_low', 0.4)
        expanded['BREAK_WALL_THRESHOLD_HIGH'] = gamma.get('break_wall_threshold_high', 0.8)
        expanded['MONTHLY_OVERRIDE_THRESHOLD'] = gamma.get('monthly_override_threshold', 0.7)
        expanded['MONTHLY_CLUSTER_STRENGTH_RATIO'] = gamma.get('monthly_cluster_strength_ratio', 1.5)
        expanded['CLUSTER_STRENGTH_THRESHOLD_S'] = gamma.get('cluster_strength_threshold_s', 2.0)
        expanded['CLUSTER_STRENGTH_THRESHOLD_T'] = gamma.get('cluster_strength_threshold_t', 1.2)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 4. 方向配置 (code2_scoring)
    # ======================================
    try:
        direction = cfg.get_section('direction')
        expanded['DEX_SAME_DIR_THRESHOLD_STRONG'] = direction.get('dex_same_dir_threshold_strong', 70)
        expanded['DEX_SAME_DIR_THRESHOLD_MEDIUM'] = direction.get('dex_same_dir_threshold_medium', 60)
        expanded['DEX_SAME_DIR_THRESHOLD_WEAK'] = direction.get('dex_same_dir_threshold_weak', 50)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 5. Pw 计算配置 (code2_scoring, code3_strategy_calc)
    # ======================================
    try:
        pw = cfg.get_section('pw_calculation')
        # 信用策略
        credit = pw.get('credit', {})
        expanded['PW_CREDIT_BASE'] = credit.get('base', 0.5)
        expanded['PW_CREDIT_CLUSTER_COEF'] = credit.get('cluster_coef', 0.1)
        expanded['PW_CREDIT_DISTANCE_PENALTY_COEF'] = credit.get('distance_penalty_coef', 0.05)
        expanded['PW_CREDIT_MIN'] = credit.get('min', 0.4)
        expanded['PW_CREDIT_MAX'] = credit.get('max', 0.85)
        # 借贷策略
        debit = pw.get('debit', {})
        expanded['PW_DEBIT_BASE'] = debit.get('base', 0.3)
        expanded['PW_DEBIT_DEX_COEF'] = debit.get('dex_coef', 0.1)
        expanded['PW_DEBIT_VANNA_COEF'] = debit.get('vanna_coef', 0.2)
        expanded['PW_DEBIT_MIN'] = debit.get('min', 0.25)
        expanded['PW_DEBIT_MAX'] = debit.get('max', 0.75)
        # 蝶式策略
        butterfly = pw.get('butterfly', {})
        expanded['PW_BUTTERFLY_BODY_INSIDE'] = butterfly.get('body_inside', 0.65)
        expanded['PW_BUTTERFLY_BODY_OFFSET_1EM'] = butterfly.get('body_offset_1em', 0.45)
        # Vanna 权重（code2_scoring 使用）
        expanded['PW_DEBIT_VANNA_WEIGHT_HIGH'] = debit.get('vanna_weight_high', 1.0)
        expanded['PW_DEBIT_VANNA_WEIGHT_MEDIUM'] = debit.get('vanna_weight_medium', 0.6)
        expanded['PW_DEBIT_VANNA_WEIGHT_LOW'] = debit.get('vanna_weight_low', 0.3)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 6. Greeks 目标范围 (code3_strategy_calc)
    # ======================================
    try:
        greeks = cfg.get_section('greeks')
        # 保守策略
        conservative = greeks.get('conservative', {})
        expanded['CONSERVATIVE_DELTA_MIN'] = conservative.get('delta_min', -0.1)
        expanded['CONSERVATIVE_DELTA_MAX'] = conservative.get('delta_max', 0.1)
        expanded['CONSERVATIVE_THETA_MIN'] = conservative.get('theta_min', 5.0)
        expanded['CONSERVATIVE_VEGA_MAX'] = conservative.get('vega_max', -10.0)
        # 均衡策略
        balanced = greeks.get('balanced', {})
        expanded['BALANCED_DELTA_RANGE'] = balanced.get('delta_range', 0.2)
        expanded['BALANCED_THETA_MIN'] = balanced.get('theta_min', 8.0)
        # 进取策略
        aggressive = greeks.get('aggressive', {})
        expanded['AGGRESSIVE_DELTA_MIN'] = aggressive.get('delta_min', 0.3)
        expanded['AGGRESSIVE_DELTA_MAX'] = aggressive.get('delta_max', 0.6)
        expanded['AGGRESSIVE_VEGA_MIN'] = aggressive.get('vega_min', 10.0)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 7. DTE 选择配置 (code3_strategy_calc)
    # ======================================
    try:
        dte = cfg.get_section('dte')
        expanded['DTE_GAP_HIGH_THRESHOLD'] = dte.get('gap_high_threshold', 3.0)
        expanded['DTE_GAP_MID_THRESHOLD'] = dte.get('gap_mid_threshold', 2.0)
        expanded['DTE_MONTHLY_ADJUSTMENT'] = dte.get('monthly_adjustment', 7)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 8. 行权价偏移配置 (code3_strategy_calc)
    # ======================================
    try:
        strikes = cfg.get_section('strikes')
        expanded['STRIKE_CONSERVATIVE_LONG_OFFSET'] = strikes.get('conservative_long_offset', 1.5)
        expanded['STRIKE_BALANCED_WING_OFFSET'] = strikes.get('balanced_wing_offset', 1.0)
        expanded['STRIKE_AGGRESSIVE_LONG_OFFSET'] = strikes.get('aggressive_long_offset', 0.2)
        expanded['STRIKE_RATIO_SHORT_OFFSET'] = strikes.get('ratio_short_offset', 0.5)
        expanded['STRIKE_RATIO_LONG_OFFSET'] = strikes.get('ratio_long_offset', 1.5)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 9. RR 计算配置 (code3_strategy_calc)
    # ======================================
    try:
        rr = cfg.get_section('rr_calculation')
        # 信用 IVR 映射
        credit_ivr = rr.get('credit_ivr', {})
        expanded['CREDIT_IVR_0_25'] = credit_ivr.get('0-25', 0.20)
        expanded['CREDIT_IVR_25_50'] = credit_ivr.get('25-50', 0.30)
        expanded['CREDIT_IVR_50_75'] = credit_ivr.get('50-75', 0.40)
        expanded['CREDIT_IVR_75_100'] = credit_ivr.get('75-100', 0.50)
        # 借贷 IVR 映射
        debit_ivr = rr.get('debit_ivr', {})
        expanded['DEBIT_IVR_0_40'] = debit_ivr.get('0-40', 0.30)
        expanded['DEBIT_IVR_40_70'] = debit_ivr.get('40-70', 0.40)
        expanded['DEBIT_IVR_70_100'] = debit_ivr.get('70-100', 0.50)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 10. 止盈止损配置 (code3_strategy_calc)
    # ======================================
    try:
        exit_rules = cfg.get_section('exit_rules')
        # 信用策略
        credit = exit_rules.get('credit', {})
        expanded['PROFIT_TARGET_CREDIT_PCT'] = credit.get('profit_target_pct', 30)
        expanded['STOP_LOSS_CREDIT_PCT'] = credit.get('stop_loss_pct', 150)
        expanded['TIME_DECAY_EXIT_DAYS'] = credit.get('time_decay_exit_days', 3)
        # 借贷策略
        debit = exit_rules.get('debit', {})
        expanded['PROFIT_TARGET_DEBIT_PCT'] = debit.get('profit_target_pct', 60)
        expanded['STOP_LOSS_DEBIT_PCT'] = debit.get('stop_loss_pct', 50)
    except (ValueError, AttributeError):
        pass
    
    # ======================================
    # 11. 风险管理配置 (code3_strategy_calc)
    # ======================================
    try:
        risk = cfg.get_section('risk_management')
        expanded['MAX_SINGLE_RISK_PCT'] = risk.get('max_single_risk_pct', 2)
        expanded['MAX_TOTAL_EXPOSURE_PCT'] = risk.get('max_total_exposure_pct', 10)
    except (ValueError, AttributeError):
        pass
    
    return expanded


# ============================================
# 向后兼容（保留旧的 API）
# ============================================

# 这些函数/类仍然可用，但建议使用新的 API
__all__ = ['config', 'ConfigLoader', 'DotDict', 'expand_config_to_env_vars']