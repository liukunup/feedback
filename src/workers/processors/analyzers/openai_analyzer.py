"""
OpenAI/Claude AI 分析器
"""
import logging
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

import httpx
from openai import AsyncOpenAI

from ....core.config import get_settings
from ....core.exceptions import AIAnalysisError

logger = logging.getLogger(__name__)


class Sentiment(str, Enum):
    """情感倾向"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass
class AnalysisResult:
    """分析结果"""
    sentiment: Optional[Sentiment]
    categories: List[str]
    entities: dict  # {users: [], orgs: [], topics: []}
    summary: str


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    embedding: List[float]
    model: str


class MessageAnalyzer:
    """基于 LLM 的消息分析器"""
    
    SYSTEM_PROMPT = """你是一个社交媒体消息分析助手。请分析用户消息并提取以下信息:

1. 情感倾向 (positive/neutral/negative)
2. 分类标签 (最多5个，使用中文标签)
3. 关键实体 (提到的用户、组织、主题)
4. 简短摘要 (50字以内)

请以JSON格式返回结果，不要包含任何其他内容。"""
    
    RESPONSE_FORMAT = {
        "sentiment": "positive | neutral | negative",
        "categories": ["标签1", "标签2"],
        "entities": {
            "users": ["用户名"],
            "organizations": ["组织名"],
            "topics": ["主题"]
        },
        "summary": "简短摘要"
    }
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            # 确定 API key
            api_key = (
                self.settings.openai_api_key or 
                self.settings.anthropic_api_key
            )
            if not api_key:
                raise AIAnalysisError("No API key configured")
            
            self._client = AsyncOpenAI(api_key=api_key)
        
        return self._client
    
    async def analyze(self, content: str) -> AnalysisResult:
        """分析消息内容
        
        Args:
            content: 消息文本
            
        Returns:
            分析结果
        """
        if not content or not content.strip():
            return AnalysisResult(
                sentiment=None,
                categories=[],
                entities={},
                summary=""
            )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.ai_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": content[:4000]}  # 限制输入长度
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            
            result_text = response.choices[0].message.content
            
            # 解析 JSON
            import json
            result = json.loads(result_text)
            
            return AnalysisResult(
                sentiment=Sentiment(result.get("sentiment", "neutral")),
                categories=result.get("categories", [])[:5],
                entities={
                    "users": result.get("entities", {}).get("users", []),
                    "organizations": result.get("entities", {}).get("organizations", []),
                    "topics": result.get("entities", {}).get("topics", []),
                },
                summary=result.get("summary", "")[:500],
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            # 返回默认结果
            return AnalysisResult(
                sentiment=Sentiment.NEUTRAL,
                categories=["未分类"],
                entities={"users": [], "organizations": [], "topics": []},
                summary=content[:50] + "..." if len(content) > 50 else content,
            )
    
    async def analyze_batch(self, contents: List[str]) -> List[AnalysisResult]:
        """批量分析 (使用 batch API 或循环)"""
        results = []
        for content in contents:
            result = await self.analyze(content)
            results.append(result)
        return results
    
    async def get_embedding(self, text: str) -> EmbeddingResult:
        """获取文本嵌入
        
        Args:
            text: 文本内容
            
        Returns:
            嵌入结果
        """
        if not text:
            return EmbeddingResult(embedding=[], model="")
        
        try:
            response = await self.client.embeddings.create(
                model=self.settings.ai_embedding_model,
                input=text[:8000],
            )
            
            return EmbeddingResult(
                embedding=response.data[0].embedding,
                model=response.model,
            )
            
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return EmbeddingResult(embedding=[], model="")


class ClaudeAnalyzer(MessageAnalyzer):
    """Claude 分析器 (如果使用 Anthropic API)"""
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    async def analyze(self, content: str) -> AnalysisResult:
        """使用 Claude API 分析"""
        if not content or not content.strip():
            return AnalysisResult(
                sentiment=None,
                categories=[],
                entities={},
                summary=""
            )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.API_URL,
                    headers={
                        "x-api-key": self.settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1000,
                        "system": self.SYSTEM_PROMPT,
                        "messages": [
                            {"role": "user", "content": content[:4000]}
                        ],
                    },
                    timeout=30,
                )
                
                if response.status_code == 200:
                    result = response.json()
                    result_text = result["content"][0]["text"]
                    
                    import json
                    parsed = json.loads(result_text)
                    
                    return AnalysisResult(
                        sentiment=Sentiment(parsed.get("sentiment", "neutral")),
                        categories=parsed.get("categories", [])[:5],
                        entities={
                            "users": parsed.get("entities", {}).get("users", []),
                            "organizations": parsed.get("entities", {}).get("organizations", []),
                            "topics": parsed.get("entities", {}).get("topics", []),
                        },
                        summary=parsed.get("summary", "")[:500],
                    )
                else:
                    raise AIAnalysisError(f"Claude API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return AnalysisResult(
                sentiment=Sentiment.NEUTRAL,
                categories=["未分类"],
                entities={"users": [], "organizations": [], "topics": []},
                summary=content[:50] + "..." if len(content) > 50 else content,
            )


def get_analyzer() -> MessageAnalyzer:
    """根据配置获取合适的分析器"""
    settings = get_settings()
    
    if settings.anthropic_api_key:
        return ClaudeAnalyzer()
    
    return MessageAnalyzer()
