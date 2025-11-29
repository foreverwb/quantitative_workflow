"""
Agent 执行器（增强版）
集成美化控制台输出
"""

from typing import Dict, Any, List, Optional, Callable
from loguru import logger

from core.model_client import ModelClientManager
from utils.console_printer import (
    print_agent_start,
    print_agent_result,
    print_code_node_start,
    print_code_node_result,
    print_success,
    print_error,
    print_warning
)
from core.error_handler import classify_agent_error, classify_code_error, WorkflowError

class AgentExecutor:
    """Agent 执行器 - 增强版（带美化输出）"""
    
    def __init__(self, model_client: ModelClientManager, env_vars: Dict[str, Any], 
                 enable_pretty_print: bool = True, show_full_output: bool = False):
        """
        初始化 Agent 执行器
        
        Args:
            model_client: 模型客户端管理器
            env_vars: 环境变量字典
            enable_pretty_print: 是否启用美化打印
            show_full_output: 是否显示完整输出
        """
        self.model_client = model_client
        self.env_vars = env_vars
        self.enable_pretty_print = enable_pretty_print
        self.show_full_output = show_full_output
    
    def execute_agent(
        self,
        agent_name: str,
        messages: List[Dict],
        json_schema: Optional[Dict] = None,
        description: str = '',
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 Agent - 统一入口（增强版）
        
        Args:
            agent_name: Agent 名称
            messages: 消息列表
            json_schema: JSON Schema（用于结构化输出）
            description: 任务描述
            **kwargs: 其他参数
            
        Returns:
            响应字典
        """
        # 打印开始信息
        if self.enable_pretty_print:
            print_agent_start(agent_name, description)
        
        logger.info(f"🔄 [{agent_name}] 开始执行")
        
        try:
            # 调用模型
            response = self.model_client.chat_completion(
                messages=messages,
                agent_name=agent_name,
                json_schema=json_schema,
                **kwargs
            )
            
            # 打印结果
            if self.enable_pretty_print:
                print_agent_result(agent_name, response, show_full=self.show_full_output)
            
            logger.success(f"✅ [{agent_name}] 执行完成")
            
            return response
        
        except Exception as e:
            # 新增：错误分类
            workflow_error = classify_agent_error(agent_name, e)
            
            if self.enable_pretty_print:
                print_error(f"[{agent_name}] 执行失败", str(e))
            
            logger.error(f"❌ [{agent_name}] 执行失败: {str(e)}")
            
            # 抛出分类后的错误
            raise workflow_error from e
    
    def execute_vision_agent(
        self,
        agent_name: str,
        inputs: List[Dict],
        json_schema: Optional[Dict] = None,
        description: str = '',
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行视觉 Agent（增强版）
        
        Args:
            agent_name: Agent 名称
            inputs: 输入列表（包含图片）
            json_schema: JSON Schema
            description: 任务描述
            **kwargs: 其他参数
            
        Returns:
            响应字典
        """
        # 打印开始信息
        if self.enable_pretty_print:
            # 统计图片数量
            image_count = sum(1 for msg in inputs if msg.get('role') == 'user' and 
                            any(c.get('type') == 'image_url' for c in (msg.get('content', []) if isinstance(msg.get('content'), list) else [])))
            desc = f"{description} (包含 {image_count} 张图片)" if description else f"解析 {image_count} 张图片"
            print_agent_start(agent_name, desc)
        
        logger.info(f"📸 [{agent_name}] 开始执行（视觉模式）")
        
        try:
            # 调用模型
            response = self.model_client.responses_create(
                inputs=inputs,
                agent_name=agent_name,
                json_schema=json_schema,
                **kwargs
            )
            
            # 打印结果
            if self.enable_pretty_print:
                print_agent_result(agent_name, response, show_full=self.show_full_output)
            
            logger.success(f"✅ [{agent_name}] 执行完成（视觉模式）")
            
            return response
        
        except Exception as e:
            if self.enable_pretty_print:
                print_error(f"[{agent_name}] 执行失败", str(e))
            
            logger.error(f"❌ [{agent_name}] 执行失败: {str(e)}")
            raise
    
    def execute_code_node(
        self,
        node_name: str,
        func: Callable,
        description: str = '',
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行 Code Node（增强版）
        
        Args:
            node_name: 节点名称
            func: 执行函数
            description: 任务描述
            **kwargs: 函数参数
            
        Returns:
            执行结果
        """
        # 打印开始信息
        if self.enable_pretty_print:
            print_code_node_start(node_name, description)
        
        logger.info(f"🔧 [{node_name}] 开始执行")
        
        try:
            # 执行函数
            result = func(**kwargs)
            
            # 打印结果
            if self.enable_pretty_print:
                print_code_node_result(node_name, result, show_full=self.show_full_output)
            
            logger.success(f"✅ [{node_name}] 执行完成")
            
            return result
        
        except Exception as e:
            error_result = {
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__
            }
            # ⭐ 新增：错误分类
            workflow_error = classify_code_error(node_name, e, kwargs)
            
            if self.enable_pretty_print:
                print_code_node_result(node_name, error_result)
            
            logger.error(f"❌ [{node_name}] 执行失败: {str(e)}")
            
            # ⭐ 抛出分类后的错误
            raise workflow_error from e