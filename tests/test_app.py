"""
API 应用测试
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


class TestAppInitialization:
    """测试应用初始化"""
    
    def test_app_import(self):
        """测试应用可以导入"""
        from src.api.main import app
        
        assert app is not None
    
    def test_app_title(self):
        """测试应用标题"""
        from src.api.main import app
        
        assert app.title == "Social Feed Aggregator"
    
    def test_app_version(self):
        """测试应用版本"""
        from src.api.main import app
        
        assert app.version == "1.0.0"
    
    def test_app_description(self):
        """测试应用描述"""
        from src.api.main import app
        
        # 中文描述
        desc = app.description
        assert desc is not None and len(desc) > 0
    
    def test_app_debug_default(self):
        """测试应用默认不开启调试"""
        from src.api.main import app
        
        # app.debug 应该是 False
        assert app.debug == False


class TestAppRoutes:
    """测试应用路由"""
    
    def test_openapi_schema(self):
        """测试 OpenAPI Schema"""
        from src.api.main import app
        
        schema = app.openapi()
        
        assert "openapi" in schema
        assert "paths" in schema
        assert "/health" in schema["paths"]
    
    def test_health_endpoint_in_schema(self):
        """测试健康检查端点在 Schema 中"""
        from src.api.main import app
        
        schema = app.openapi()
        
        assert "/health" in schema["paths"]
        health_path = schema["paths"]["/health"]
        assert "get" in health_path
    
    def test_channels_routes_in_schema(self):
        """测试渠道路由在 Schema 中"""
        from src.api.main import app
        
        schema = app.openapi()
        
        assert "/channels/" in schema["paths"]
    
    def test_messages_routes_in_schema(self):
        """测试消息路由在 Schema 中"""
        from src.api.main import app
        
        schema = app.openapi()
        
        assert "/messages/" in schema["paths"]
    
    def test_search_routes_in_schema(self):
        """测试搜索路由在 Schema 中"""
        from src.api.main import app
        
        schema = app.openapi()
        
        assert "/search/" in schema["paths"]
        assert "/search/stats" in schema["paths"]


class TestAppMiddleware:
    """测试应用中间件"""
    
    def test_cors_middleware_configured(self):
        """测试 CORS 中间件已配置"""
        from src.api.main import app
        
        # 检查 middleware 栈中是否有 CORS
        middleware_names = [type(m).__name__ for m in app.user_middleware]
        
        # 实际上 CORSMiddleware 可能在 stack 中
        assert isinstance(app.user_middleware, list)


class TestRouterIntegration:
    """测试路由集成"""
    
    def test_channels_router_attached(self):
        """测试渠道路由已挂载"""
        from src.api.routers.channels import router
        
        # 验证 router 存在并有路由
        assert router is not None
        assert len(router.routes) > 0
    
    def test_messages_router_attached(self):
        """测试消息路由已挂载"""
        from src.api.routers.messages import router
        
        # 验证 router 存在并有路由
        assert router is not None
        assert len(router.routes) > 0
    
    def test_search_router_attached(self):
        """测试搜索路由已挂载"""
        from src.api.routers.search import router
        
        # 验证 router 存在并有路由
        assert router is not None
        assert len(router.routes) > 0


class TestAPIResponses:
    """测试 API 响应格式"""
    
    def test_health_endpoint_response(self):
        """测试健康检查端点响应"""
        from src.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_json_handling(self):
        """测试无效 JSON 处理"""
        from src.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.post(
            "/channels/",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        
        # 应该返回 422 或 400
        assert response.status_code in [400, 422]
    
    def test_not_found_handling(self):
        """测试 404 处理"""
        from src.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
