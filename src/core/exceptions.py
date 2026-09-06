"""
自定义异常类
"""
from fastapi import HTTPException, status


class SocialFeedException(Exception):
    """基础异常"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ChannelNotFoundError(SocialFeedException):
    """渠道未找到"""
    pass


class ScraperError(SocialFeedException):
    """抓取器错误"""
    pass


class AuthenticationError(SocialFeedException):
    """认证错误"""
    pass


class RateLimitError(ScraperError):
    """API 限流错误"""
    pass


class MessageNotFoundError(SocialFeedException):
    """消息未找到"""
    pass


class AIAnalysisError(SocialFeedException):
    """AI 分析错误"""
    pass


# HTTP 异常映射
def http_exception_from_social(exc: SocialFeedException) -> HTTPException:
    """将业务异常转换为 HTTP 异常"""
    status_map = {
        ChannelNotFoundError: status.HTTP_404_NOT_FOUND,
        MessageNotFoundError: status.HTTP_404_NOT_FOUND,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        ScraperError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AIAnalysisError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    for exc_type, code in status_map.items():
        if isinstance(exc, exc_type):
            status_code = code
            break
    
    return HTTPException(
        status_code=status_code,
        detail={"message": exc.message, "details": exc.details}
    )
