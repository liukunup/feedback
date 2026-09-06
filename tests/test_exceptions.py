"""
异常模块测试
"""
import pytest
from fastapi import status


class TestSocialFeedException:
    """测试基础异常类"""
    
    def test_exception_with_message(self):
        """测试异常消息"""
        from src.core.exceptions import SocialFeedException
        
        exc = SocialFeedException("Test error")
        assert exc.message == "Test error"
        assert exc.details == {}
        assert str(exc) == "Test error"
    
    def test_exception_with_details(self):
        """测试带详情的异常"""
        from src.core.exceptions import SocialFeedException
        
        details = {"field": "value", "code": 123}
        exc = SocialFeedException("Error with details", details=details)
        assert exc.message == "Error with details"
        assert exc.details == details


class TestChannelNotFoundError:
    """测试渠道未找到异常"""
    
    def test_channel_not_found(self):
        """测试渠道未找到异常"""
        from src.core.exceptions import ChannelNotFoundError
        
        exc = ChannelNotFoundError("Channel abc not found")
        assert "abc" in exc.message
        assert isinstance(exc, Exception)


class TestScraperError:
    """测试抓取器异常"""
    
    def test_scraper_error(self):
        """测试抓取器错误"""
        from src.core.exceptions import ScraperError
        
        exc = ScraperError("Failed to fetch")
        assert exc.message == "Failed to fetch"


class TestAuthenticationError:
    """测试认证异常"""
    
    def test_authentication_error(self):
        """测试认证错误"""
        from src.core.exceptions import AuthenticationError
        
        exc = AuthenticationError("Invalid token")
        assert exc.message == "Invalid token"


class TestRateLimitError:
    """测试限流异常"""
    
    def test_rate_limit_error(self):
        """测试限流错误"""
        from src.core.exceptions import RateLimitError
        
        exc = RateLimitError("Rate limit exceeded")
        assert exc.message == "Rate limit exceeded"
        # RateLimitError 应该是 ScraperError 的子类
        from src.core.exceptions import ScraperError
        assert isinstance(exc, ScraperError)


class TestMessageNotFoundError:
    """测试消息未找到异常"""
    
    def test_message_not_found(self):
        """测试消息未找到异常"""
        from src.core.exceptions import MessageNotFoundError
        
        exc = MessageNotFoundError("Message xyz not found")
        assert "xyz" in exc.message


class TestAIAnalysisError:
    """测试 AI 分析异常"""
    
    def test_ai_analysis_error(self):
        """测试 AI 分析错误"""
        from src.core.exceptions import AIAnalysisError
        
        exc = AIAnalysisError("AI analysis failed", details={"model": "gpt-4"})
        assert exc.message == "AI analysis failed"
        assert exc.details["model"] == "gpt-4"


class TestHTTPExceptionConversion:
    """测试 HTTP 异常转换"""
    
    def test_channel_not_found_conversion(self):
        """测试渠道未找到转换为 404"""
        from src.core.exceptions import ChannelNotFoundError, http_exception_from_social
        
        exc = ChannelNotFoundError("Channel not found")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
        assert "Channel not found" in http_exc.detail["message"]
    
    def test_message_not_found_conversion(self):
        """测试消息未找到转换为 404"""
        from src.core.exceptions import MessageNotFoundError, http_exception_from_social
        
        exc = MessageNotFoundError("Message not found")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_404_NOT_FOUND
    
    def test_authentication_error_conversion(self):
        """测试认证错误转换为 401"""
        from src.core.exceptions import AuthenticationError, http_exception_from_social
        
        exc = AuthenticationError("Invalid credentials")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_rate_limit_conversion(self):
        """测试限流转换为 429"""
        from src.core.exceptions import RateLimitError, http_exception_from_social
        
        exc = RateLimitError("Too many requests")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    
    def test_scraper_error_conversion(self):
        """测试抓取器错误转换为 500"""
        from src.core.exceptions import ScraperError, http_exception_from_social
        
        exc = ScraperError("Internal error")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_ai_analysis_error_conversion(self):
        """测试 AI 分析错误转换为 500"""
        from src.core.exceptions import AIAnalysisError, http_exception_from_social
        
        exc = AIAnalysisError("AI failed")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    def test_unknown_error_default_500(self):
        """测试未知错误默认返回 500"""
        from src.core.exceptions import SocialFeedException, http_exception_from_social
        
        exc = SocialFeedException("Unknown error")
        http_exc = http_exception_from_social(exc)
        
        assert http_exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
