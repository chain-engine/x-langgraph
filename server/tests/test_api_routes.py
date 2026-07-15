# -*- coding: utf-8 -*-
"""
API 路由测试

测试 FastAPI 路由的基本功能
"""

import pytest
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSettings:
    """配置测试"""

    def test_settings_creation(self):
        """测试配置创建"""
        from config.settings import Settings

        settings = Settings()
        assert settings is not None
        assert settings.DEBUG is not None

    def test_get_available_provider(self):
        """测试获取可用提供者"""
        from config.settings import settings

        provider = settings.get_available_provider()
        assert provider in ["deepseek", "doubao", "aliyun", "mock"]

    def test_has_valid_api_key(self):
        """测试 API Key 检查"""
        from config.settings import settings

        # 方法存在即可
        assert hasattr(settings, "has_valid_api_key")

    def test_validate_model_config(self):
        """测试模型配置验证"""
        from config.settings import settings

        # Mock 总是有效的
        assert settings.validate_model_config("mock") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
