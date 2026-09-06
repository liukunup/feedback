"""
Discord Bot Scraper - 使用 discord.py
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Callable

import discord

from ..base import BaseScraper, ChannelConfig, Message, Platform, ScraperRegistry
from ...core.exceptions import AuthenticationError, ScraperError

logger = logging.getLogger(__name__)


class DiscordBotClient(discord.Client):
    """Discord Bot 客户端"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = asyncio.Event()
        self.messages: List[Message] = []

    async def on_ready(self):
        logger.info(f"Discord Bot connected as {self.user}")
        self.connected.set()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        msg = self._parse_message(message)
        if msg:
            self.messages.append(msg)

    def _parse_message(self, msg: discord.Message) -> Message:
        attachments = []
        for att in msg.attachments:
            attachments.append({
                "id": str(att.id),
                "filename": att.filename,
                "url": att.url,
                "content_type": att.content_type,
                "size": att.size,
            })

        embeds_data = []
        for embed in msg.embeds:
            embeds_data.append({
                "title": embed.title,
                "description": embed.description,
                "url": embed.url,
            })

        channel_name = None
        if hasattr(msg.channel, 'name'):
            channel_name = f"{msg.guild.name}/{msg.channel.name}" if msg.guild else msg.channel.name

        return Message(
            platform_id=str(msg.id),
            content=msg.content,
            author_id=str(msg.author.id),
            author_name=msg.author.name,
            author_avatar=str(msg.author.avatar) if msg.author.avatar else None,
            created_at=msg.created_at,
            metadata={
                "guild_id": str(msg.guild.id) if msg.guild else None,
                "guild_name": msg.guild.name if msg.guild else None,
                "channel_id": str(msg.channel.id),
                "channel_name": msg.channel.name if hasattr(msg.channel, 'name') else None,
                "type": str(msg.type),
                "embeds": embeds_data,
            },
            attachments=attachments,
            channel_name=channel_name,
            channel_id=str(msg.channel.id),
        )


@ScraperRegistry.register(Platform.DISCORD)
class DiscordPyScraper(BaseScraper):
    """使用 discord.py 的 Discord 抓取器"""

    def __init__(self):
        super().__init__()
        self._bot: Optional[DiscordBotClient] = None
        self._intents: Optional[discord.Intents] = None
        self._event_callbacks: List[Callable] = []
        self._listener_task: Optional[asyncio.Task] = None

    async def initialize(self, config: ChannelConfig) -> None:
        self._config = config

        self._intents = discord.Intents.default()
        self._intents.message_content = True
        self._intents.messages = True
        self._intents.guilds = True

        self._bot = DiscordBotClient(intents=self._intents)

        try:
            async with self._bot:
                await self._bot.start(config.access_token)
        except discord.errors.LoginFailure:
            raise AuthenticationError("Invalid Discord bot token")
        except Exception as e:
            raise ScraperError(f"Failed to connect: {e}")

        await asyncio.wait_for(self._bot.connected.wait(), timeout=30)
        self._initialized = True
        logger.info(f"Discord scraper initialized, {len(self._bot.guilds)} guilds accessible")

    async def close(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._bot:
            await self._bot.close()
        self._initialized = False

    async def verify_connection(self) -> bool:
        if not self._bot:
            return False
        return self._bot.is_ready()

    async def fetch_messages(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
        channel_filter: Optional[str] = None
    ) -> List[Message]:
        if not self._initialized or not self._bot:
            raise ScraperError("Scraper not initialized")

        messages: List[Message] = []
        self._bot.messages.clear()

        if channel_filter:
            try:
                channel = self._bot.get_channel(int(channel_filter))
                if channel:
                    messages.extend(await self._fetch_channel_messages(channel, since, limit))
            except Exception as e:
                logger.error(f"Failed to fetch channel {channel_filter}: {e}")
        else:
            for guild in self._bot.guilds:
                for channel in guild.text_channels:
                    try:
                        if not channel.permissions_for(guild.me).read_message_history:
                            continue
                        channel_messages = await self._fetch_channel_messages(channel, since, limit)
                        messages.extend(channel_messages)
                        if len(messages) >= limit:
                            return messages[:limit]
                    except Exception as e:
                        logger.warning(f"Failed to fetch {channel.name}: {e}")
                        continue

        return messages

    async def _fetch_channel_messages(
        self,
        channel: discord.TextChannel,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Message]:
        messages = []
        try:
            async for msg in channel.history(limit=limit, after=since, oldest_first=False):
                if not msg.author.bot:
                    messages.append(self._bot._parse_message(msg))
        except discord.Forbidden:
            logger.warning(f"No permission to read {channel.name}")
        except Exception as e:
            logger.error(f"Error fetching {channel.name}: {e}")
        return messages

    def register_event_callback(self, callback: Callable) -> None:
        self._event_callbacks.append(callback)

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        if not self._bot:
            return {}
        channel = self._bot.get_channel(int(channel_id))
        if not channel:
            return {}
        return {
            "id": str(channel.id),
            "name": channel.name,
            "guild_id": str(channel.guild.id),
            "guild_name": channel.guild.name,
            "topic": getattr(channel, 'topic', None),
        }


class DiscordCachedScraper(DiscordPyScraper):
    """带缓存的 Discord 抓取器"""

    def __init__(self):
        super().__init__()
        self._message_cache: Set[str] = set()

    async def fetch_messages(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
        channel_filter: Optional[str] = None
    ) -> List[Message]:
        all_messages = await super().fetch_messages(since, limit * 2, channel_filter)
        new_messages = [m for m in all_messages if m.platform_id not in self._message_cache]
        for msg in all_messages:
            self._message_cache.add(msg.platform_id)
        if len(self._message_cache) > 10000:
            self._message_cache = set(list(self._message_cache)[-5000:])
        return new_messages[:limit]
