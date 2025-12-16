"""
Prompts - Agent 提示词模块
包含所有 Agent 的 Prompt 定义
"""

# 导入所有 Agent prompt 模块
from . import agent5_scenario
from . import agent6_strategy
from . import agent7_comparison
from . import agent8_report
from . import agent3_validate

__all__ = [
    'agent3_validate',
    'agent5_scenario',
    'agent6_strategy',
    'agent7_comparison',
    'agent8_report'
]