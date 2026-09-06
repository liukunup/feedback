"""
企业微信 API Scraper
"""
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import aiohttp

from ..base import BaseScraper, ChannelConfig, Message, Platform, ScraperRegistry
from ...core.exceptions import AuthenticationError, ScraperError

logger = logging.getLogger(__name__)


@dataclass
class WeComConfig:
    """企业微信配置"""
    corp_id: str
    corp_secret: str
    agent_id: str
    token: str
    encoding_aes_key: str


@ScraperRegistry.register(Platform.WECOM)
class WeComScraper(BaseScraper):
    """企业微信抓取器"""

    BASE_URL = "https://qyapi.weixin.qq.com"

    def __init__(self):
        super().__init__()
        self._session: Optional[aiohttp.ClientSession] = None
        self._wecom_config: Optional[WeComConfig] = None
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    async def initialize(self, config: ChannelConfig) -> None:
        self._config = config
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

        self._wecom_config = WeComConfig(
            corp_id=config.extra_config.get("corp_id"),
            corp_secret=config.extra_config.get("corp_secret"),
            agent_id=config.extra_config.get("agent_id"),
            token=config.extra_config.get("token", ""),
            encoding_aes_key=config.extra_config.get("encoding_aes_key", ""),
        )

        await self._get_access_token()
        self._initialized = True
        logger.info("WeCom scraper initialized")

    async def close(self) -> None:
        if self._session:
            await self._session.close()
        self._initialized = False

    async def _get_access_token(self) -> None:
        if self._access_token and time.time() < self._token_expires_at:
            return

        params = {
            "corpid": self._wecom_config.corp_id,
            "corpsecret": self._wecom_config.corp_secret,
        }

        async with self._session.get(
            f"{self.BASE_URL}/cgi-bin/gettoken",
            params=params
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("errcode") == 0:
                    self._access_token = data["access_token"]
                    self._token_expires_at = time.time() + data.get("expires_in", 7200) - 300
                    logger.info("Got WeCom access token")
                else:
                    raise AuthenticationError(f"Failed to get access token: {data}")
            else:
                raise AuthenticationError(f"HTTP error: {resp.status}")

    async def verify_connection(self) -> bool:
        try:
            await self._get_access_token()
            return self._access_token is not None
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False

    async def fetch_messages(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
        channel_filter: Optional[str] = None
    ) -> List[Message]:
        if not self._initialized:
            raise ScraperError("Scraper not initialized")

        messages: List[Message] = []

        if channel_filter:
            chat_messages = await self._fetch_app_message(channel_filter, since, limit)
            messages.extend(chat_messages)
        else:
            chats = await self._list_app_chats()
            for chat_id in chats:
                try:
                    chat_messages = await self._fetch_app_message(chat_id, since, limit)
                    messages.extend(chat_messages)
                except Exception as e:
                    logger.warning(f"Failed to fetch chat {chat_id}: {e}")

        return messages

    async def _list_app_chats(self) -> List[str]:
        await self._ensure_token()

        params = {"access_token": self._access_token}

        async with self._session.post(
            f"{self.BASE_URL}/cgi-bin/appchat/list",
            params=params,
            json={"agentid": int(self._wecom_config.agent_id), "limit": 100}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("errcode") == 0:
                    return [chat["chatid"] for chat in data.get("chatlist", [])]

        return []

    async def _fetch_app_message(
        self,
        chat_id: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Message]:
        await self._ensure_token()

        params = {"access_token": self._access_token}

        payload: Dict[str, Any] = {"chatid": chat_id, "limit": limit}

        async with self._session.post(
            f"{self.BASE_URL}/cgi-bin/appchat/get",
            params=params,
            json=payload
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("errcode") == 0:
                    return [self._parse_message(msg, chat_id) for msg in data.get("msg_list", [])]

        return []

    def _parse_message(self, data: Dict[str, Any], chat_id: str) -> Message:
        msg_type = data.get("msgtype")
        content = ""
        attachments = []

        if msg_type == "text":
            content = data.get("text", {}).get("content", "")
        elif msg_type == "image":
            content = "[图片]"
            attachments.append({"type": "image", "media_id": data.get("image", {}).get("media_id")})
        elif msg_type == "voice":
            content = "[语音]"
            attachments.append({"type": "voice", "media_id": data.get("voice", {}).get("media_id")})
        elif msg_type == "video":
            content = "[视频]"
            attachments.append({"type": "video", "media_id": data.get("video", {}).get("media_id")})
        elif msg_type == "file":
            content = f"[文件] {data.get('file', {}).get('file_name', '')}"
            attachments.append({"type": "file", "media_id": data.get("file", {}).get("media_id")})
        elif msg_type == "markdown":
            content = data.get("markdown", {}).get("content", "")
        else:
            content = f"[{msg_type}]"

        created_at = datetime.fromtimestamp(data.get("msgtime", 0) / 1000)

        return Message(
            platform_id=data.get("msgid", ""),
            content=content,
            author_id=data.get("from", ""),
            author_name=data.get("name", ""),
            created_at=created_at,
            metadata=data,
            attachments=attachments,
            channel_name=chat_id,
            channel_id=chat_id,
        )

    async def _ensure_token(self) -> None:
        if not self._access_token or time.time() >= self._token_expires_at:
            await self._get_access_token()

    def parse_webhook_event(self, body: bytes) -> Optional[Message]:
        try:
            root = ET.fromstring(body)
            msg_type = root.findtext("MsgType")
            content = root.findtext("Content")

            if msg_type == "text":
                return Message(
                    platform_id=root.findtext("MsgId", ""),
                    content=content or "",
                    author_id=root.findtext("FromUserName", ""),
                    author_name="",
                    created_at=datetime.now(),
                    metadata={"raw": body.decode()},
                    attachments=[],
                    channel_name="",
                    channel_id=root.findtext("ToUserName", ""),
                )
        except Exception as e:
            logger.error(f"Failed to parse webhook event: {e}")

        return None

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        await self._ensure_token()

        params = {"access_token": self._access_token}

        async with self._session.post(
            f"{self.BASE_URL}/cgi-bin/appchat/get",
            params=params,
            json={"chatid": channel_id}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("errcode") == 0:
                    return data.get("chat_info", {})

        return {}
