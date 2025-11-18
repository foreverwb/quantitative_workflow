"""
统一日志组件
特性：
1. 多级别日志（DEBUG/INFO/WARNING/ERROR/CRITICAL）
2. 文件轮转（按日期/大小自动分割）
3. 结构化日志（JSON格式可选）
4. 性能追踪（耗时统计）
5. 上下文变量（追踪用户/任务ID）
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional
import json


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器（JSON格式）"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加自定义字段（如 task_id, user_id）
        if hasattr(record, 'task_id'):
            log_data["task_id"] = record.task_id
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        if hasattr(record, 'duration'):
            log_data["duration_ms"] = record.duration
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """带颜色的终端日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 格式：时间 | 级别 | 模块:函数 | 消息
        formatted = (
            f"{color}[{self.formatTime(record, '%H:%M:%S')}] "
            f"{record.levelname:8s}{reset} "
            f"| {record.module}:{record.funcName} "
            f"| {record.getMessage()}"
        )
        
        # 添加异常信息
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class WorkflowLogger:
    """工作流日志管理器"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logging()
        return cls._instance
    
    def _setup_logging(self):
        """初始化日志系统"""
        # 创建logs目录
        log_dir = Path(__file__).parent
        log_dir.mkdir(exist_ok=True)
        
        # 主日志文件（按日期轮转）
        main_log = log_dir / "workflow.log"
        
        # 错误日志文件（仅ERROR及以上）
        error_log = log_dir / "error.log"
        
        # 性能日志文件（记录耗时）
        perf_log = log_dir / "performance.log"
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 清除现有的handlers（避免重复）
        root_logger.handlers.clear()
        
        # Handler 1: 控制台输出（彩色，INFO及以上）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)
        
        # Handler 2: 主日志文件（按日期轮转，DEBUG及以上）
        file_handler = TimedRotatingFileHandler(
            main_log,
            when='midnight',
            interval=1,
            backupCount=30,  # 保留30天
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        root_logger.addHandler(file_handler)
        
        # Handler 3: 错误日志文件（按大小轮转，ERROR及以上）
        error_handler = RotatingFileHandler(
            error_log,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
        
        # Handler 4: 性能日志（结构化JSON）
        perf_handler = RotatingFileHandler(
            perf_log,
            maxBytes=10*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(StructuredFormatter())
        
        # 创建性能专用logger
        perf_logger = logging.getLogger('performance')
        perf_logger.setLevel(logging.INFO)
        perf_logger.addHandler(perf_handler)
        perf_logger.propagate = False  # 不传播到根logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的logger"""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        return self._loggers[name]
    
    @staticmethod
    def add_context(logger: logging.Logger, **kwargs):
        """添加上下文变量（如task_id, user_id）"""
        # 使用LoggerAdapter包装原logger
        return logging.LoggerAdapter(logger, kwargs)


# ============================================
# 全局日志实例
# ============================================
workflow_logger = WorkflowLogger()


def get_logger(name: str) -> logging.Logger:
    """快捷获取logger（推荐使用方式）"""
    return workflow_logger.get_logger(name)


# ============================================
# 性能追踪装饰器
# ============================================

import time
from functools import wraps

def log_performance(func):
    """
    性能追踪装饰器
    
    用法：
        @log_performance
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger('performance')
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000  # 转换为毫秒
            
            logger.info(
                f"Function {func.__name__} completed",
                extra={
                    'function': func.__name__,
                    'duration': round(duration, 2),
                    'status': 'success'
                }
            )
            
            return result
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"Function {func.__name__} failed: {str(e)}",
                extra={
                    'function': func.__name__,
                    'duration': round(duration, 2),
                    'status': 'error'
                },
                exc_info=True
            )
            raise
    
    return wrapper


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    # 基本使用
    logger = get_logger('example')
    
    logger.debug("这是DEBUG信息")
    logger.info("这是INFO信息")
    logger.warning("这是WARNING信息")
    logger.error("这是ERROR信息")
    
    # 带上下文的日志
    logger_with_context = workflow_logger.add_context(
        logger, 
        task_id="task_123", 
        user_id="user_456"
    )
    logger_with_context.info("带上下文的日志")
    
    # 性能追踪
    @log_performance
    def slow_function():
        time.sleep(2)
        return "Done"
    
    slow_function()
    
    # 异常日志
    try:
        1 / 0
    except Exception as e:
        logger.exception("发生异常")