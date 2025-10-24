from typing import Dict, Type, Optional, Any
from crewai import Agent, LLM

from src.ai_write_x.core.base_framework import AgentConfig
from src.ai_write_x.config.config import Config
from src.ai_write_x.core.tool_registry import GlobalToolRegistry
from src.ai_write_x.utils import log


class AgentFactory:
    """智能体工厂类"""

    def __init__(self):
        self._agent_templates: Dict[str, Type] = {}
        # 使用全局工具注册表
        self._tool_registry = GlobalToolRegistry.get_instance()
        self._llm_cache: Dict[str, LLM] = {}

    def register_agent_template(self, name: str, template_class: Type):
        """注册智能体模板"""
        self._agent_templates[name] = template_class

    def register_tool(self, name: str, tool_class):
        """注册工具类"""
        self._tool_registry.register_tool(name, tool_class)

    def _get_llm(self, llm_config: Dict[str, Any] | None = None) -> Optional[LLM]:
        """获取LLM实例，支持缓存"""
        config = Config.get_instance()

        # 如果没有指定特殊配置，使用全局配置
        if not llm_config:
            cache_key = f"{config.api_type}_{config.api_model}_{config.api_apibase}"
            if cache_key not in self._llm_cache:
                if config.api_key:
                    llm_kwargs: Dict[str, Any] = {
                        "model": config.api_model,
                        "api_key": config.api_key,
                        "max_tokens": 8192,
                    }
                    api_base = config.api_apibase
                    if api_base:
                        llm_kwargs["base_url"] = api_base
                        llm_kwargs["api_base"] = api_base

                    self._llm_cache[cache_key] = LLM(**llm_kwargs)
                else:
                    return None
            return self._llm_cache.get(cache_key)

        # 使用自定义LLM配置
        llm_params = {**llm_config}

        if not llm_params.get("api_key"):
            llm_params["api_key"] = config.api_key

        base_url = llm_params.get("base_url") or llm_params.get("api_base")
        if not base_url:
            base_url = config.api_apibase

        if base_url:
            llm_params.setdefault("base_url", base_url)
            llm_params.setdefault("api_base", base_url)

        cache_key = (
            f"{llm_params.get('model', 'default')}"
            f"_{llm_params.get('api_key', 'default')}"
            f"_{llm_params.get('base_url', '')}"
        )
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = LLM(**llm_params)
        return self._llm_cache[cache_key]

    def create_agent(self, config: AgentConfig, custom_llm: LLM | None = None) -> Agent:
        """创建智能体实例"""
        tools = []
        if config.tools:
            for tool_name in config.tools:
                tool_class = self._tool_registry.get_tool(tool_name)
                if tool_class:
                    tools.append(tool_class())
                else:
                    log.print_log(f"警告: 找不到 {tool_name} 工具")

        agent_kwargs = {
            "role": config.role,
            "goal": config.goal,
            "backstory": config.backstory,
            "tools": tools,
            "allow_delegation": config.allow_delegation,
            "memory": config.memory,
            "max_rpm": config.max_rpm,
            "verbose": config.verbose,
        }

        # 添加模板支持
        if hasattr(config, "system_template") and config.system_template:
            agent_kwargs["system_template"] = config.system_template
        if hasattr(config, "prompt_template") and config.prompt_template:
            agent_kwargs["prompt_template"] = config.prompt_template
        if hasattr(config, "response_template") and config.response_template:
            agent_kwargs["response_template"] = config.response_template

        # LLM优先级：自定义LLM > 配置中的LLM > 全局LLM
        llm = custom_llm or self._get_llm(config.llm_config)
        if llm:
            agent_kwargs["llm"] = llm

        return Agent(**agent_kwargs)

    def create_specialized_agent(self, name: str, **kwargs) -> Agent:
        """创建专门化智能体"""
        if name in self._agent_templates:
            template_class = self._agent_templates[name]
            return template_class(**kwargs)
        else:
            raise ValueError(f"未知 agent : {name}")

    def get_agent_by_name(self, agents: Dict[str, Agent], name: str) -> Optional[Agent]:
        """通过 name 获取 agent 实例"""
        return agents.get(name)
