# -*- coding: utf-8 -*-
"""
配置管理模块

使用 pydantic-settings 从环境变量加载配置，提供统一的配置访问接口。
支持自动类型转换和验证。
"""

import os
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    配置类，使用 pydantic-settings 自动从环境变量加载配置
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ========== DeepSeek 配置 ==========
    DEEPSEEK_API_KEY: str = Field(default="", description="DeepSeek API 密钥")
    DEEPSEEK_API_BASE: str = Field(
        default="https://api.deepseek.com/v1",
        description="DeepSeek API 基础地址"
    )
    DEEPSEEK_MODEL_NAME: str = Field(
        default="deepseek-chat",
        description="DeepSeek 模型名称"
    )

    # ========== 豆包配置 ==========
    DOUBAO_API_KEY: str = Field(default="", description="豆包 API 密钥")
    DOUBAO_API_BASE: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        description="豆包 API 基础地址"
    )
    DOUBAO_MODEL_NAME: str = Field(default="", description="豆包模型名称")

    # ========== 阿里云百炼配置 ==========
    ALIYUN_API_KEY: str = Field(default="", description="阿里云 API 密钥")
    ALIYUN_API_BASE: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="阿里云 API 基础地址"
    )
    ALIYUN_MODEL_NAME: str = Field(
        default="qwen-turbo",
        description="阿里云模型名称"
    )

    # ========== 业务数据库配置 ==========
    DB_HOST: str = Field(default="localhost", description="数据库主机")
    DB_PORT: int = Field(default=3306, description="数据库端口")
    DB_USER: str = Field(default="root", description="数据库用户")
    DB_PASSWORD: str = Field(default="", description="数据库密码")
    DB_NAME: str = Field(default="", description="数据库名称")

    # ========== Checkpoint 数据库配置（LangGraph 状态持久化）==========
    CHECKPOINT_DB_HOST: str = Field(default="localhost", description="Checkpoint 数据库主机")
    CHECKPOINT_DB_PORT: int = Field(default=3306, description="Checkpoint 数据库端口")
    CHECKPOINT_DB_USER: str = Field(default="root", description="Checkpoint 数据库用户")
    CHECKPOINT_DB_PASSWORD: str = Field(default="", description="Checkpoint 数据库密码")
    CHECKPOINT_DB_NAME: str = Field(default="x-langgraph", description="Checkpoint 数据库名称")

    # ========== Redis 配置 ==========
    REDIS_HOST: str = Field(default="localhost", description="Redis 主机")
    REDIS_PORT: int = Field(default=6379, description="Redis 端口")
    REDIS_PASSWORD: str = Field(default="", description="Redis 密码")
    REDIS_DB: int = Field(default=0, description="Redis 数据库")

    # ========== API 服务配置 ==========
    API_HOST: str = Field(default="0.0.0.0", description="API 服务主机")
    API_PORT: int = Field(default=8000, description="API 服务端口")
    API_RELOAD: bool = Field(default=False, description="API 热重载")
    API_KEY: str = Field(default="", description="API 访问密钥（留空则不启用认证）")

    # ========== 高德地图 API 配置 ==========
    AMAP_API_KEY: str = Field(default="", description="高德地图 API 密钥")

    # ========== 搜索 API 配置 ==========
    SEARCH_API_KEY: str = Field(default="", description="搜索服务 API 密钥")
    SEARCH_API_URL: str = Field(default="", description="搜索服务 API 地址")

    # ========== 通用配置 ==========
    TEMPERATURE: float = Field(default=0.0, description="LLM 温度参数")
    DEBUG: bool = Field(default=True, description="调试模式")
    STRUCTURED: bool = Field(default=False, description="结构化输出模式")

    # ========== 日志配置 ==========
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_DIR: str = Field(default="logs", description="日志目录")

    @field_validator("DB_PORT", "CHECKPOINT_DB_PORT", "API_PORT", "REDIS_PORT", mode="before")
    @classmethod
    def parse_int_field(cls, v):
        """将字符串转换为整数"""
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return 0
        return v

    @field_validator("API_RELOAD", "DEBUG", "STRUCTURED", mode="before")
    @classmethod
    def parse_bool_field(cls, v):
        """将字符串转换为布尔值"""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    @field_validator("TEMPERATURE", mode="before")
    @classmethod
    def parse_float_field(cls, v):
        """将字符串转换为浮点数"""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return 0.0
        return v

    def get_available_provider(self) -> str:
        """
        返回第一个有 API Key 的提供者

        Returns:
            str: 提供者名称（deepseek, doubao, aliyun, mock）
        """
        if self.DEEPSEEK_API_KEY:
            return "deepseek"
        if self.DOUBAO_API_KEY:
            return "doubao"
        if self.ALIYUN_API_KEY:
            return "aliyun"
        return "mock"

    def has_valid_api_key(self) -> bool:
        """检查是否有可用的 API Key"""
        return bool(self.DEEPSEEK_API_KEY or self.DOUBAO_API_KEY or self.ALIYUN_API_KEY)

    def validate_model_config(self, model_name: str) -> bool:
        """
        验证模型配置是否完整

        Args:
            model_name: 模型名称（deepseek, doubao, tongyi, mock）

        Returns:
            bool: 配置是否完整
        """
        if model_name == "deepseek":
            return bool(self.DEEPSEEK_API_KEY and self.DEEPSEEK_MODEL_NAME)
        elif model_name == "doubao":
            return bool(self.DOUBAO_API_KEY and self.DOUBAO_MODEL_NAME)
        elif model_name == "tongyi" or model_name == "aliyun":
            return bool(self.ALIYUN_API_KEY and self.ALIYUN_MODEL_NAME)
        elif model_name == "mock":
            return True
        return False

    def get_checkpoint_db_url(self) -> str:
        """获取 Checkpoint 数据库连接 URL（asyncmy 驱动）"""
        return (
            f"mysql+asyncmy://{self.CHECKPOINT_DB_USER}:"
            f"{self.CHECKPOINT_DB_PASSWORD}@"
            f"{self.CHECKPOINT_DB_HOST}:"
            f"{self.CHECKPOINT_DB_PORT}/"
            f"{self.CHECKPOINT_DB_NAME}"
        )

    def get_db_url(self) -> str:
        """获取业务数据库连接 URL"""
        return (
            f"mysql+pymysql://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:"
            f"{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )

    def get_redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings: Settings = Settings()
