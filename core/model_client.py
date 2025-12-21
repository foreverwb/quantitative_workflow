"""
模型客户端封装（修复版）
修复内容：
1. 初始化时读取完整的 API 参数配置
2. chat_completion 和 responses_create 方法支持所有 OpenAI API 参数
3. 支持参数覆盖机制（kwargs 优先级最高）
"""

import os
import json
from typing import Dict, Any, List, Optional
from loguru import logger
import copy
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

def _sanitize_json_schema_for_vision(schema: Dict[str, Any]) -> Dict[str, Any]:
    """递归规范化 JSON Schema"""
    def _rec(node):
        if not isinstance(node, dict):
            return node

        node = dict(node)
        node_type = node.get("type")
        has_props = isinstance(node.get("properties"), dict)

        if node_type == "object" or has_props:
            if "additionalProperties" not in node:
                node["additionalProperties"] = False
            elif isinstance(node["additionalProperties"], dict):
                node["additionalProperties"] = _rec(node["additionalProperties"])

            if has_props:
                prop_keys = list(node["properties"].keys())
                existing_required = node.get("required")
                if isinstance(existing_required, list):
                    missing = [k for k in prop_keys if k not in existing_required]
                    if missing:
                        node["required"] = existing_required + missing
                else:
                    node["required"] = prop_keys

        if isinstance(node.get("properties"), dict):
            for k, v in list(node["properties"].items()):
                node["properties"][k] = _rec(v)

        if isinstance(node.get("patternProperties"), dict):
            for k, v in list(node["patternProperties"].items()):
                node["patternProperties"][k] = _rec(v)

        it = node.get("items")
        if isinstance(it, dict):
            node["items"] = _rec(it)
        elif isinstance(it, list):
            node["items"] = [_rec(x) for x in it]

        for comb in ("allOf", "anyOf", "oneOf"):
            if isinstance(node.get(comb), list):
                node[comb] = [_rec(s) for s in node[comb]]

        ap = node.get("additionalProperties")
        if isinstance(ap, dict):
            node["additionalProperties"] = _rec(ap)

        return node

    return _rec(copy.deepcopy(schema))


class ModelClient:
    """OpenAI 兼容模型客户端（修复版）"""
    
    # ✅ 定义所有支持的 API 参数
    SUPPORTED_API_PARAMS = [
        'temperature',
        'max_tokens', 
        'top_p',
        'frequency_penalty',
        'presence_penalty',
        'stop',
        'stream',
        'n',
        'logprobs',
        'top_logprobs',
        'logit_bias',
        'seed'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """初始化模型客户端（修复版）"""
        if not OPENAI_AVAILABLE:
            raise ImportError("请安装: pip install openai")
        
        self.config = config
        self.provider = config.get('provider', 'openai')
        self.model = config.get('model', 'gpt-4o')
        self.api_key = self._get_api_key_from_env()
        self.base_url = self._get_base_url_from_env()
        self.timeout = config.get('timeout', 120)
        self.supports_vision = config.get('supports_vision', False)
        
        # ✅ 修复：读取完整的 API 参数配置
        self.default_params = {}
        for param in self.SUPPORTED_API_PARAMS:
            if param in config:
                self.default_params[param] = config[param]
        
        # 保持向后兼容（直接属性访问）
        self.temperature = config.get('temperature', 0.3)
        self.max_tokens = config.get('max_tokens', 4096)
        
        if not self.api_key:
            raise ValueError("未找到 API Key")
        
        # 初始化 OpenAI 客户端
        client_kwargs = {'api_key': self.api_key}
        if self.base_url:
            client_kwargs['base_url'] = self.base_url
        if self.timeout:
            client_kwargs['timeout'] = self.timeout
        
        self.client = OpenAI(**client_kwargs)
        
        logger.debug(f"{self.provider.upper()} 客户端初始化完成")
        logger.debug(f"默认参数: {self.default_params}")
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """从环境变量获取 API Key"""
        return os.environ.get('API_KEY')
    
    def _get_base_url_from_env(self) -> Optional[str]:
        """从环境变量获取 Base URL"""
        base_url = os.environ.get('API_BASE_URL')
        if base_url:
            return base_url
        return os.environ.get('OPENAI_BASE_URL') or self.config.get('base_url')
    
    def _build_api_params(self, **kwargs) -> Dict[str, Any]:
        """
        构建 API 请求参数（合并默认配置和运行时参数）
        
        优先级：kwargs > 方法参数 > 配置文件
        
        Args:
            **kwargs: 运行时传入的参数
            
        Returns:
            合并后的参数字典
        """
        # 1. 从配置文件获取默认值
        params = self.default_params.copy()
        
        # 2. 合并运行时参数（kwargs 优先级最高）
        for key in self.SUPPORTED_API_PARAMS:
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        
        return params
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        json_schema: Optional[Dict] = None,
        use_strict_mode: bool = True,
        **kwargs  # ✅ 支持所有 OpenAI API 参数
    ) -> Dict[str, Any]:
        """
        聊天补全接口（修复版）
        
        Args:
            messages: 消息列表
            json_schema: JSON Schema（结构化输出）
            use_strict_mode: 是否使用严格模式
            **kwargs: 运行时参数（temperature, top_p, presence_penalty 等）
            
        Returns:
            响应字典
        """
        # ✅ 构建完整的 API 参数
        api_params = self._build_api_params(**kwargs)
        
        request_params = {
            "model": self.model,
            "messages": messages,
            **api_params  # ✅ 合并所有参数
        }
        
        # 处理 Strict JSON Schema
        if json_schema:
            if use_strict_mode:
                sanitized_schema = _sanitize_json_schema_for_vision(json_schema)
                request_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "schema": sanitized_schema,
                        "strict": True
                    }
                }
                logger.debug("✅ 已启用 Strict JSON Schema Mode")
            else:
                request_params["response_format"] = {"type": "json_object"}
                logger.debug("ℹ️ 使用兼容 JSON 模式（非严格）")
        
        try:
            response = self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            # JSON 解析
            if json_schema and content:
                try:
                    content = json.loads(content)
                    logger.debug("✅ JSON 解析成功")
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON 解析失败: {str(e)[:100]}")
            
            return {
                "content": content,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                "model": response.model
            }
        
        except Exception as e:
            logger.error(f"API 调用失败: {str(e)}")
            raise
    
    def responses_create(
        self,
        inputs: List[Dict[str, Any]],
        json_schema: Optional[Dict] = None,
        use_strict_mode: bool = True,
        **kwargs  # ✅ 支持所有 OpenAI API 参数
    ) -> Dict[str, Any]:
        """
        Responses API 接口（修复版 - Vision 支持）
        
        Args:
            inputs: 输入列表（包含图片）
            json_schema: JSON Schema
            use_strict_mode: 是否使用严格模式
            **kwargs: 运行时参数（temperature, top_p, presence_penalty 等）
            
        Returns:
            响应字典
        """
        # ✅ 构建完整的 API 参数
        api_params = self._build_api_params(**kwargs)
        print(">>>>>>>>>> api_params <<<<<<<<", api_params)
        request_params = {
            "model": self.model,
            "messages": inputs,
            **api_params  # ✅ 合并所有参数
        }
        
        # 处理 Strict JSON Schema（Vision）
        if json_schema:
            if use_strict_mode:
                sanitized_schema = _sanitize_json_schema_for_vision(json_schema)
                request_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "vision_structured_output",
                        "schema": sanitized_schema,
                        "strict": True
                    }
                }
                logger.debug("✅ 已启用 Vision Strict JSON Schema Mode")
            else:
                request_params["response_format"] = {"type": "json_object"}
                logger.debug("ℹ️ 使用兼容 JSON 模式（非严格）")
        
        # 强化 Vision 模型的 JSON 输出提示
        if self.supports_vision and json_schema:
            for msg in inputs:
                if msg.get("role") == "system":
                    original_content = msg["content"]
                    msg["content"] = (
                        "**CRITICAL: You must respond with ONLY valid JSON. "
                        "No markdown, no explanations, no code blocks. "
                        "Just pure JSON starting with { and ending with }.**\n\n"
                        + original_content
                    )
                    break
        
        try:
            logger.debug(f"调用 Vision API: model={self.model}, params={api_params}")
            
            response = self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            # JSON 解析
            if json_schema and content:
                try:
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    if json_match:
                        content = json.loads(json_match.group(1))
                    else:
                        content = json.loads(content)
                    logger.debug("✅ JSON 解析成功")
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON 解析失败: {str(e)[:100]}")
            
            return {
                "content": content,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                "model": response.model
            }
        
        except Exception as e:
            logger.error(f"Vision API 调用失败: {str(e)}")
            raise


class ModelClientManager:
    """多模型客户端管理器（修复版）"""
    
    def __init__(self, config_path: str = "config/model_config.yaml"):
        """初始化管理器"""
        import yaml
        from pathlib import Path
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"模型配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.full_config = yaml.safe_load(f)
        
        self.default_config = self.full_config.get('default', {})
        self.agents_config = self.full_config.get('agents', {})
        self._clients_cache = {}
        
        logger.info(f"模型客户端管理器初始化完成")
        logger.info(f"默认模型: {self.default_config.get('provider')}/{self.default_config.get('model')}")
    
    def _merge_config(self, agent_config: Dict, default_config: Dict) -> Dict:
        """合并配置（保留所有参数）"""
        merged = default_config.copy()
        merged.update(agent_config)
        return merged
    
    def get_client(self, agent_name: str = "default") -> ModelClient:
        """获取指定 Agent 的客户端"""
        if agent_name in self._clients_cache:
            return self._clients_cache[agent_name]
        
        if agent_name in self.agents_config:
            agent_config = self.agents_config[agent_name]
            full_config = self._merge_config(agent_config, self.default_config)
        else:
            full_config = self.default_config
        
        client = ModelClient(full_config)
        self._clients_cache[agent_name] = client
        
        logger.info(f"为 [{agent_name}] 创建客户端: {full_config.get('provider')}/{full_config.get('model')}")
        logger.debug(f"API 参数: {client.default_params}")
        
        return client
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        agent_name: str = "default",
        json_schema: Optional[Dict] = None,
        use_strict_mode: bool = True,
        **kwargs  # ✅ 透传所有参数
    ) -> Dict[str, Any]:
        """统一的聊天补全接口（修复版）"""
        client = self.get_client(agent_name)
        
        logger.info(f"[{agent_name}] 调用模型: {client.provider}/{client.model}")
        
        if json_schema and use_strict_mode:
            logger.info(f"[{agent_name}] 🔒 启用 Strict JSON Schema Mode")
        
        result = client.chat_completion(
            messages=messages,
            json_schema=json_schema,
            use_strict_mode=use_strict_mode,
            **kwargs  # ✅ 透传运行时参数
        )
        
        result['agent_name'] = agent_name
        result['provider'] = client.provider
        
        logger.success(
            f"[{agent_name}] ✓ 完成 "
            f"(输入:{result['usage']['input_tokens']} "
            f"输出:{result['usage']['output_tokens']})"
        )
        
        return result
    
    def responses_create(
        self,
        inputs: List[Dict[str, Any]],
        agent_name: str = "agent3",
        json_schema: Optional[Dict] = None,
        use_strict_mode: bool = True,
        **kwargs  # ✅ 透传所有参数
    ) -> Dict[str, Any]:
        """Responses API 接口（修复版）"""
        client = self.get_client(agent_name)
        
        logger.info(f"[{agent_name}] 调用 Responses API: {client.provider}/{client.model}")
        logger.debug(f"[{agent_name}] 运行时参数: {kwargs}")
        
        if json_schema and use_strict_mode:
            logger.info(f"[{agent_name}] 🔒 启用 Vision Strict JSON Schema Mode")
        
        result = client.responses_create(
            inputs=inputs,
            json_schema=json_schema,
            use_strict_mode=use_strict_mode,
            **kwargs  # ✅ 透传运行时参数
        )
        
        result['agent_name'] = agent_name
        result['provider'] = client.provider
        
        logger.success(
            f"[{agent_name}] ✓ Responses API 完成 "
            f"(输入:{result['usage']['input_tokens']} "
            f"输出:{result['usage']['output_tokens']})"
        )
        
        return result
    
    def get_model_info(self, agent_name: str = "default") -> Dict[str, Any]:
        """获取指定 Agent 的模型信息"""
        client = self.get_client(agent_name)
        return {
            "agent_name": agent_name,
            "provider": client.provider,
            "model": client.model,
            "supports_vision": client.supports_vision,
            "default_params": client.default_params
        }
    
    def list_all_agents(self) -> List[str]:
        """列出所有配置的 Agent"""
        return list(self.agents_config.keys())


class ModelClientFactory:
    """模型客户端工厂"""
    
    @staticmethod
    def create_from_config(config_path: str = "config/model_config.yaml") -> ModelClientManager:
        """从配置文件创建管理器"""
        return ModelClientManager(config_path)