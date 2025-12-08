"""
容错机制 - 错误处理器
职责：统一的错误分类、记录和报告
"""

import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from loguru import logger


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"      # 致命错误，必须终止
    RECOVERABLE = "recoverable" # 可恢复错误，记录后继续
    WARNING = "warning"         # 警告，不影响流程


class ErrorCategory(Enum):
    """错误类别"""
    API_FAILURE = "api_failure"              # API调用失败
    DATA_FORMAT = "data_format_error"        # 数据格式错误
    CODE_BUG = "code_bug"                    # 代码逻辑错误
    VALIDATION = "validation_error"          # 数据校验失败
    SYSTEM = "system_error"                  # 系统资源错误
    DATA_INCOMPLETE = "data_incomplete"      # 数据不完整(非错误)


class WorkflowError(Exception):
    """工作流错误基类"""
    
    def __init__(
        self, 
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        node_name: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.node_name = node_name
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now().isoformat()
        self.traceback = traceback.format_exc() if original_error else None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "node_name": self.node_name,
            "timestamp": self.timestamp,
            "context": self.context,
            "traceback": self.traceback,
            "original_error": str(self.original_error) if self.original_error else None
        }
    
    def should_terminate(self) -> bool:
        """是否应该终止流程"""
        return self.severity == ErrorSeverity.CRITICAL


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, symbol: str, output_dir: Path = Path("data/output")):
        # 验证 symbol 参数
        if not symbol or symbol.strip() == "" or symbol.upper() == "UNKNOWN":
            raise ValueError(f"无效的 symbol: '{symbol}'，无法创建错误处理器")
        self.symbol = symbol
        self.output_dir = output_dir / symbol
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 关键改动：仅在目录不存在时创建
        if not self.output_dir.exists():
            logger.info(f"📁 创建输出目录: {self.output_dir}")
            self.output_dir.mkdir(parents=True, exist_ok=True)
        else:
            logger.debug(f"📁 输出目录已存在: {self.output_dir}")
        
        self.error_log = []
        self.completed_steps = []
    
    def add_completed_step(self, step_name: str):
        """记录已完成的步骤"""
        self.completed_steps.append({
            "step": step_name,
            "timestamp": datetime.now().isoformat()
        })
    
    def handle_error(self, error: WorkflowError) -> Dict[str, Any]:
        """
        处理错误
        
        Returns:
            错误报告字典
        """
        # 1. 记录错误
        self.error_log.append(error.to_dict())
        
        # 2. 保存错误上下文
        if error.should_terminate():
            self._save_error_context(error)
        
        # 3. 生成错误报告
        return self._generate_error_report(error)
    
    def _save_error_context(self, error: WorkflowError):
        """保存错误上下文到文件（统一路径格式）"""
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        # 创建日期子目录: data/output/NVDA/20251130/
        date_dir = self.output_dir / date_str
        
        if not date_dir.exists():
            logger.debug(f"📁 创建日期目录: {date_dir}")
            date_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件名格式: NVDA_20251130_214518_error.json
        error_file = date_dir / f"{self.symbol}_{date_str}_{time_str}_error.json"
        
        error_context = {
            "symbol": self.symbol,
            "error": error.to_dict(),
            "completed_steps": self.completed_steps,
            "error_log": self.error_log,
            "saved_at": now.isoformat()
        }
        
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_context, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 错误上下文已保存: {error_file}")
    
    def _generate_error_report(self, error: WorkflowError) -> Dict[str, Any]:
        """生成错误报告"""
        suggestions = self._get_suggestions(error)
        
        return {
            "status": "error",
            "error_summary": {
                "severity": error.severity.value,
                "category": error.category.value,
                "node": error.node_name,
                "message": error.message,
                "timestamp": error.timestamp
            },
            "completed_steps": self.completed_steps,
            "suggestions": suggestions,
            "context": error.context,
            "full_error": error.to_dict()
        }
    
    def _get_suggestions(self, error: WorkflowError) -> list:
        """根据错误类别生成修复建议"""
        suggestions = []
        
        if error.category == ErrorCategory.API_FAILURE:
            suggestions.extend([
                "检查 API Key 是否有效",
                "检查网络连接",
                "查看 API 配额是否用尽",
                "稍后重试"
            ])
        
        elif error.category == ErrorCategory.DATA_FORMAT:
            suggestions.extend([
                "检查 JSON Schema 是否正确",
                "查看模型返回的原始响应",
                "尝试调整 Prompt 明确要求 JSON 格式",
                "检查是否启用了 Strict Mode"
            ])
        
        elif error.category == ErrorCategory.CODE_BUG:
            suggestions.extend([
                "查看完整的错误堆栈",
                "检查输入数据是否符合预期",
                "检查是否有 None 值未处理",
                "联系开发者报告 Bug"
            ])
        
        elif error.category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "检查必需字段是否存在",
                "检查字段类型是否正确",
                "查看详细的验证报告"
            ])
        
        elif error.category == ErrorCategory.SYSTEM:
            suggestions.extend([
                "检查磁盘空间",
                "检查文件权限",
                "检查路径是否正确"
            ])
        
        return suggestions


def classify_agent_error(
    node_name: str,
    exception: Exception,
    response: Optional[Dict] = None
) -> WorkflowError:
    """分类 Agent 节点错误"""
    error_msg = str(exception)
    
    # API 调用失败
    if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
        return WorkflowError(
            message=f"API 调用超时或连接失败: {error_msg}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.API_FAILURE,
            node_name=node_name,
            context={"response": response},
            original_error=exception
        )
    
    # API 认证失败
    if "401" in error_msg or "403" in error_msg or "api key" in error_msg.lower():
        return WorkflowError(
            message=f"API 认证失败，请检查 API Key: {error_msg}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.API_FAILURE,
            node_name=node_name,
            context={"response": response},
            original_error=exception
        )
    
    # JSON 解析失败
    if "json" in error_msg.lower() or isinstance(exception, json.JSONDecodeError):
        return WorkflowError(
            message=f"JSON 解析失败，模型返回格式错误: {error_msg}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATA_FORMAT,
            node_name=node_name,
            context={"response": response},
            original_error=exception
        )
    
    # 默认：代码 Bug
    return WorkflowError(
        message=f"未知错误（可能是代码 Bug）: {error_msg}",
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.CODE_BUG,
        node_name=node_name,
        context={"response": response},
        original_error=exception
    )


def classify_code_error(
    node_name: str,
    exception: Exception,
    input_data: Optional[Dict] = None
) -> WorkflowError:
    """分类 Code 节点错误"""
    error_msg = str(exception)
    
    # 除零错误
    if isinstance(exception, ZeroDivisionError):
        return WorkflowError(
            message=f"计算错误：除数为零",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CODE_BUG,
            node_name=node_name,
            context={"input_data": input_data},
            original_error=exception
        )
    
    # 键不存在错误
    if isinstance(exception, KeyError):
        return WorkflowError(
            message=f"数据字段缺失: {error_msg}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.VALIDATION,
            node_name=node_name,
            context={"input_data": input_data},
            original_error=exception
        )
    
    # 类型错误
    if isinstance(exception, TypeError):
        return WorkflowError(
            message=f"数据类型错误: {error_msg}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CODE_BUG,
            node_name=node_name,
            context={"input_data": input_data},
            original_error=exception
        )
    
    # 文件操作错误
    if isinstance(exception, (FileNotFoundError, PermissionError, IOError)):
        return WorkflowError(
            message=f"文件操作失败: {error_msg}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.SYSTEM,
            node_name=node_name,
            context={"input_data": input_data},
            original_error=exception
        )
    
    # 默认
    return WorkflowError(
        message=f"代码执行错误: {error_msg}",
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.CODE_BUG,
        node_name=node_name,
        context={"input_data": input_data},
        original_error=exception
    )