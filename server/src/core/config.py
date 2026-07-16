# -*- coding: utf-8 -*-
"""
应用配置管理
支持从环境变量和YAML配置文件读取配置
"""

import os
from typing import Final, Any
from pathlib import Path
from dataclasses import dataclass, field
import yaml

from dotenv import load_dotenv
from constants.enums import Environment

load_dotenv()


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = True


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    file_path: str = "logs/x-langgraph.log"
    rotation: str = "1 day"
    retention: str = "7 days"
    compression: str = "zip"
    console_output: bool = True


@dataclass
class CORSConfig:
    """CORS配置"""
    enabled: bool = True
    allow_origins: str = "*"
    allow_credentials: bool = True
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class RateLimitConfig:
    """限流配置"""
    enabled: bool = True
    requests_per_minute: int = 60
    requests_per_hour: int = 1000


@dataclass
class DatabaseConfig:
    """业务数据库配置"""
    enabled: bool = False
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    name: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False



@dataclass
class RedisConfig:
    """Redis配置"""
    enabled: bool = False
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    pool_size: int = 10
    max_connections: int = 50
    decode_responses: bool = True
    socket_timeout: int = 5


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


@dataclass
class ApiDocsConfig:
    """API文档配置"""
    enabled: bool = True
    title: str = "x-langgraph API"
    description: str = "企业级 LangGraph 工作流 API 服务"
    version: str = "1.0.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"


@dataclass
class LLMConfig:
    """LLM配置"""
    temperature: float = 0.0
    structured: bool = False


@dataclass
class DeepSeekConfig:
    """DeepSeek配置"""
    api_key: str = ""
    api_base: str = "https://api.deepseek.com/v1"
    model_name: str = "deepseek-chat"


@dataclass
class DoubaoConfig:
    """豆包配置"""
    api_key: str = ""
    api_base: str = "https://ark.cn-beijing.volces.com/api/v3"
    model_name: str = ""


@dataclass
class AliyunConfig:
    """阿里云百炼配置"""
    api_key: str = ""
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_name: str = "qwen-turbo"


@dataclass
class ThirdPartyConfig:
    """第三方API配置"""
    amap_api_key: str = ""
    search_api_key: str = ""
    search_api_url: str = ""
    api_key: str = ""


def _to_bool(value: str | None) -> bool:
    """将字符串转换为布尔值"""
    return value.lower() == 'true' if value else False


def _to_int(value: str | None, default: int = 0) -> int:
    """将字符串转换为整数"""
    return int(value) if value else default


def _to_float(value: str | None, default: float = 0.0) -> float:
    """将字符串转换为浮点数"""
    return float(value) if value else default


class Settings:
    """应用配置类

    支持从环境变量和YAML配置文件读取配置
    优先级：环境变量 > YAML配置文件 > 默认配置
    """

    CONFIG_FILE_PATH: Final[str] = 'config.yaml'

    def __init__(self) -> None:
        """初始化配置"""
        self._config: dict[str, Any] = self._load_config()
        self._parse_config()

    def _load_config(self) -> dict[str, Any]:
        """加载配置

        优先级：环境变量 > YAML配置文件 > 默认配置

        Returns:
            dict[str, Any]: 合并后的配置
        """
        config: dict[str, Any] = self._get_default_config()

        config_file: Path = Path(self.CONFIG_FILE_PATH)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config: dict[str, Any] = yaml.safe_load(f) or {}
                self._merge_config(config, file_config)
            except Exception as e:
                print(f"警告: 无法加载配置文件 {self.CONFIG_FILE_PATH}: {e}")

        self._load_from_env(config)

        return config

    def _get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            'app': {
                'name': 'x-langgraph',
                'version': '1.0.0',
                'description': '企业级 LangGraph 工作流编排框架',
                'environment': 'development',
                'debug': True,
                'timezone': 'Asia/Shanghai',
                'locale': 'zh_CN'
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'workers': 1,
                'reload': True
            },
            'logging': {
                'level': 'INFO',
                'format': '{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
                'file_path': 'logs/x-langgraph.log',
                'rotation': '1 day',
                'retention': '7 days',
                'compression': 'zip',
                'console_output': True
            },
            'cors': {
                'enabled': True,
                'allow_origins': '*',
                'allow_credentials': True,
                'allow_methods': ['*'],
                'allow_headers': ['*']
            },
            'rate_limit': {
                'enabled': True,
                'requests_per_minute': 60,
                'requests_per_hour': 1000
            },
            'database': {
                'enabled': False,
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'name': '',
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'echo': False
            },
            'redis': {
                'enabled': False,
                'host': 'localhost',
                'port': 6379,
                'password': '',
                'db': 0,
                'pool_size': 10,
                'max_connections': 50,
                'decode_responses': True,
                'socket_timeout': 5
            },
            'security': {
                'secret_key': 'your-secret-key-here',
                'algorithm': 'HS256',
                'access_token_expire_minutes': 30,
                'refresh_token_expire_days': 7
            },
            'api_docs': {
                'enabled': True,
                'title': 'x-langgraph API',
                'description': '企业级 LangGraph 工作流 API 服务',
                'version': '1.0.0',
                'docs_url': '/docs',
                'redoc_url': '/redoc',
                'openapi_url': '/openapi.json'
            },
            'llm': {
                'temperature': 0.0,
                'structured': False
            },
            'deepseek': {
                'api_key': '',
                'api_base': 'https://api.deepseek.com/v1',
                'model_name': 'deepseek-chat'
            },
            'doubao': {
                'api_key': '',
                'api_base': 'https://ark.cn-beijing.volces.com/api/v3',
                'model_name': ''
            },
            'aliyun': {
                'api_key': '',
                'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                'model_name': 'qwen-turbo'
            },
            'third_party': {
                'amap_api_key': '',
                'search_api_key': '',
                'search_api_url': '',
                'api_key': ''
            }
        }

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """递归合并配置"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def _load_from_env(self, config: dict[str, Any]) -> None:
        """从环境变量加载配置"""
        if (value := os.environ.get('APP_NAME')):
            config['app']['name'] = value
        if (value := os.environ.get('APP_VERSION')):
            config['app']['version'] = value
        if (value := os.environ.get('APP_ENVIRONMENT')):
            config['app']['environment'] = value
        if (value := os.environ.get('APP_DEBUG')):
            config['app']['debug'] = _to_bool(value)

        if (value := os.environ.get('SERVER_HOST')):
            config['server']['host'] = value
        if (value := os.environ.get('SERVER_PORT')):
            config['server']['port'] = _to_int(value)
        if (value := os.environ.get('SERVER_WORKERS')):
            config['server']['workers'] = _to_int(value)
        if (value := os.environ.get('SERVER_RELOAD')):
            config['server']['reload'] = _to_bool(value)

        if (value := os.environ.get('LOG_LEVEL')):
            config['logging']['level'] = value
        if (value := os.environ.get('LOG_FILE_PATH')):
            config['logging']['file_path'] = value

        if (value := os.environ.get('CORS_ENABLED')):
            config['cors']['enabled'] = _to_bool(value)
        if (value := os.environ.get('CORS_ALLOW_ORIGINS')):
            config['cors']['allow_origins'] = value

        if (value := os.environ.get('RATE_LIMIT_ENABLED')):
            config['rate_limit']['enabled'] = _to_bool(value)

        if (value := os.environ.get('DB_ENABLED')):
            config['database']['enabled'] = _to_bool(value)
        if (value := os.environ.get('DB_HOST')):
            config['database']['host'] = value
        if (value := os.environ.get('DB_PORT')):
            config['database']['port'] = _to_int(value)
        if (value := os.environ.get('DB_USER')):
            config['database']['user'] = value
        if (value := os.environ.get('DB_PASSWORD')):
            config['database']['password'] = value
        if (value := os.environ.get('DB_NAME')):
            config['database']['name'] = value

        if (value := os.environ.get('REDIS_HOST')):
            config['redis']['host'] = value
        if (value := os.environ.get('REDIS_PORT')):
            config['redis']['port'] = _to_int(value)
        if (value := os.environ.get('REDIS_PASSWORD')):
            config['redis']['password'] = value
        if (value := os.environ.get('REDIS_DB')):
            config['redis']['db'] = _to_int(value)

        if (value := os.environ.get('SECRET_KEY')):
            config['security']['secret_key'] = value

        if (value := os.environ.get('TEMPERATURE')):
            config['llm']['temperature'] = _to_float(value)
        if (value := os.environ.get('STRUCTURED')):
            config['llm']['structured'] = _to_bool(value)

        if (value := os.environ.get('DEEPSEEK_API_KEY')):
            config['deepseek']['api_key'] = value
        if (value := os.environ.get('DEEPSEEK_API_BASE')):
            config['deepseek']['api_base'] = value
        if (value := os.environ.get('DEEPSEEK_MODEL_NAME')):
            config['deepseek']['model_name'] = value

        if (value := os.environ.get('DOUBAO_API_KEY')):
            config['doubao']['api_key'] = value
        if (value := os.environ.get('DOUBAO_API_BASE')):
            config['doubao']['api_base'] = value
        if (value := os.environ.get('DOUBAO_MODEL_NAME')):
            config['doubao']['model_name'] = value

        if (value := os.environ.get('ALIYUN_API_KEY')):
            config['aliyun']['api_key'] = value
        if (value := os.environ.get('ALIYUN_API_BASE')):
            config['aliyun']['api_base'] = value
        if (value := os.environ.get('ALIYUN_MODEL_NAME')):
            config['aliyun']['model_name'] = value

        if (value := os.environ.get('AMAP_API_KEY')):
            config['third_party']['amap_api_key'] = value
        if (value := os.environ.get('SEARCH_API_KEY')):
            config['third_party']['search_api_key'] = value
        if (value := os.environ.get('SEARCH_API_URL')):
            config['third_party']['search_api_url'] = value
        if (value := os.environ.get('API_KEY')):
            config['third_party']['api_key'] = value

    def _parse_config(self) -> None:
        """解析配置到具体配置对象"""
        self.app_name: str = self._config['app']['name']
        self.app_version: str = self._config['app']['version']
        self.app_description: str = self._config['app'].get('description', '企业级 LangGraph 工作流编排框架')
        self.app_environment: str = self._config['app']['environment']
        self.app_debug: bool = self._config['app']['debug']
        self.app_timezone: str = self._config['app'].get('timezone', 'Asia/Shanghai')
        self.app_locale: str = self._config['app'].get('locale', 'zh_CN')

        self.server = ServerConfig(**self._config['server'])
        self.logging = LoggingConfig(**self._config['logging'])
        self.cors = CORSConfig(**self._config['cors'])
        self.rate_limit = RateLimitConfig(**self._config['rate_limit'])
        self.database = DatabaseConfig(**self._config['database'])
        self.redis = RedisConfig(**self._config['redis'])
        self.security = SecurityConfig(**self._config['security'])
        self.api_docs = ApiDocsConfig(**self._config['api_docs'])
        self.llm = LLMConfig(**self._config['llm'])
        self.deepseek = DeepSeekConfig(**self._config['deepseek'])
        self.doubao = DoubaoConfig(**self._config['doubao'])
        self.aliyun = AliyunConfig(**self._config['aliyun'])
        self.third_party = ThirdPartyConfig(**self._config['third_party'])

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_environment == Environment.DEVELOPMENT.desc

    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.app_environment == Environment.TESTING.desc

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_environment == Environment.PRODUCTION.desc

    def reload(self) -> None:
        """重新加载配置"""
        self._config = self._load_config()
        self._parse_config()

    def get_available_provider(self) -> str:
        """返回第一个有 API Key 的提供者"""
        if self.deepseek.api_key:
            return "deepseek"
        if self.doubao.api_key:
            return "doubao"
        if self.aliyun.api_key:
            return "aliyun"
        return "mock"

    def has_valid_api_key(self) -> bool:
        """检查是否有可用的 API Key"""
        return bool(self.deepseek.api_key or self.doubao.api_key or self.aliyun.api_key)

    def validate_model_config(self, model_name: str) -> bool:
        """验证模型配置是否完整"""
        if model_name == "deepseek":
            return bool(self.deepseek.api_key and self.deepseek.model_name)
        elif model_name == "doubao":
            return bool(self.doubao.api_key and self.doubao.model_name)
        elif model_name == "tongyi" or model_name == "aliyun":
            return bool(self.aliyun.api_key and self.aliyun.model_name)
        elif model_name == "mock":
            return True
        return False

    def get_db_url(self, async_mode: bool = False) -> str:
        """获取数据库连接 URL
        
        Args:
            async_mode: 是否使用异步驱动（asyncmy），默认使用同步驱动（pymysql）
        """
        driver = "asyncmy" if async_mode else "pymysql"
        return (
            f"mysql+{driver}://{self.database.user}:"
            f"{self.database.password}@"
            f"{self.database.host}:"
            f"{self.database.port}/"
            f"{self.database.name}"
        )

    def get_redis_url(self) -> str:
        """获取 Redis 连接 URL"""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"

    @property
    def DEBUG(self) -> bool:
        """兼容旧代码的调试模式属性"""
        return self.app_debug

    @property
    def API_HOST(self) -> str:
        """兼容旧代码的 API 主机属性"""
        return self.server.host

    @property
    def API_PORT(self) -> int:
        """兼容旧代码的 API 端口属性"""
        return self.server.port

    @property
    def API_RELOAD(self) -> bool:
        """兼容旧代码的 API 热重载属性"""
        return self.server.reload

    @property
    def API_KEY(self) -> str:
        """兼容旧代码的 API 访问密钥属性"""
        return self.third_party.api_key

    @property
    def LOG_LEVEL(self) -> str:
        """兼容旧代码的日志级别属性"""
        return self.logging.level

    @property
    def LOG_DIR(self) -> str:
        """兼容旧代码的日志目录属性"""
        return self.logging.file_path.rsplit('/', 1)[0] if '/' in self.logging.file_path else 'logs'

    @property
    def TEMPERATURE(self) -> float:
        """兼容旧代码的温度参数属性"""
        return self.llm.temperature

    @property
    def STRUCTURED(self) -> bool:
        """兼容旧代码的结构化输出模式属性"""
        return self.llm.structured

    @property
    def DEEPSEEK_API_KEY(self) -> str:
        """兼容旧代码的 DeepSeek API 密钥属性"""
        return self.deepseek.api_key

    @property
    def DEEPSEEK_API_BASE(self) -> str:
        """兼容旧代码的 DeepSeek API 基础地址属性"""
        return self.deepseek.api_base

    @property
    def DEEPSEEK_MODEL_NAME(self) -> str:
        """兼容旧代码的 DeepSeek 模型名称属性"""
        return self.deepseek.model_name

    @property
    def DOUBAO_API_KEY(self) -> str:
        """兼容旧代码的豆包 API 密钥属性"""
        return self.doubao.api_key

    @property
    def DOUBAO_API_BASE(self) -> str:
        """兼容旧代码的豆包 API 基础地址属性"""
        return self.doubao.api_base

    @property
    def DOUBAO_MODEL_NAME(self) -> str:
        """兼容旧代码的豆包模型名称属性"""
        return self.doubao.model_name

    @property
    def ALIYUN_API_KEY(self) -> str:
        """兼容旧代码的阿里云 API 密钥属性"""
        return self.aliyun.api_key

    @property
    def ALIYUN_API_BASE(self) -> str:
        """兼容旧代码的阿里云 API 基础地址属性"""
        return self.aliyun.api_base

    @property
    def ALIYUN_MODEL_NAME(self) -> str:
        """兼容旧代码的阿里云模型名称属性"""
        return self.aliyun.model_name

    @property
    def DB_HOST(self) -> str:
        """兼容旧代码的数据库主机属性"""
        return self.database.host

    @property
    def DB_PORT(self) -> int:
        """兼容旧代码的数据库端口属性"""
        return self.database.port

    @property
    def DB_USER(self) -> str:
        """兼容旧代码的数据库用户属性"""
        return self.database.user

    @property
    def DB_PASSWORD(self) -> str:
        """兼容旧代码的数据库密码属性"""
        return self.database.password

    @property
    def DB_NAME(self) -> str:
        """兼容旧代码的数据库名称属性"""
        return self.database.name

    @property
    def REDIS_HOST(self) -> str:
        """兼容旧代码的 Redis 主机属性"""
        return self.redis.host

    @property
    def REDIS_PORT(self) -> int:
        """兼容旧代码的 Redis 端口属性"""
        return self.redis.port

    @property
    def REDIS_PASSWORD(self) -> str:
        """兼容旧代码的 Redis 密码属性"""
        return self.redis.password

    @property
    def REDIS_DB(self) -> int:
        """兼容旧代码的 Redis 数据库属性"""
        return self.redis.db

    @property
    def AMAP_API_KEY(self) -> str:
        """兼容旧代码的高德地图 API 密钥属性"""
        return self.third_party.amap_api_key

    @property
    def SEARCH_API_KEY(self) -> str:
        """兼容旧代码的搜索 API 密钥属性"""
        return self.third_party.search_api_key

    @property
    def SEARCH_API_URL(self) -> str:
        """兼容旧代码的搜索 API 地址属性"""
        return self.third_party.search_api_url


settings: Final[Settings] = Settings()
