"""
JSON Schema 数据类包
用于结构化输出验证
"""

from .agent3_schema import Agent3Response
from .agent5_schema import Agent5Response
from .agent6_schema import Agent6Response
from .agent7_schema import Agent7Response

__all__ = [
    'Agent3Response',
    'Agent5Response',
    'Agent6Response',
    'Agent7Response'
]
