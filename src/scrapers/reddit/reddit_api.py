"""
Reddit API Scraper - 使用 PRAW
"""
import base64
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

import aiohttp
import praw

from ..base import BaseScraper, ChannelConfig, Message, Platform, ScraperRegistry
from ...core.exceptions import AuthenticationError, ScraperError

logger = logging.getLogger(__name__)


@ScraperRegistry.register(Platform.REDDIT)
class RedditScraper(BaseScraper):
    """Reddit 抓取器"""

    BASE_URL = "https://oauth.reddit.com"

    def __init__(self):
        super().__init__()
        self._reddit: Optional[praw.Reddit] = None
        self._access_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self, config: ChannelConfig) -> None:
        self._config = config

        self._reddit = praw.Reddit(
            client_id=config.extra_config.get("client_id"),
            client_secret=config.extra_config.get("client_secret"),
            username=config.extra_config.get("username"),
            password=config.extra_config.get("password"),
            user_agent="social-feed-aggregator/1.0",
        )

        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._get_access_token()

        self._initialized = True
        logger.info("Reddit scraper initialized")

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
        self._reddit = None
        self._initialized = False

    async def _get_access_token(self) -> None:
        client_id = self._config.extra_config.get("client_id")
        client_secret = self._config.extra_config.get("client_secret")

        credentials = f"{client_id}:{client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "social-feed-aggregator/1.0",
        }

        data = {"grant_type": "client_credentials", "duration": "permanent"}

        async with self._session.post(
            "https://www.reddit.com/api/v1/access_token",
            headers=headers,
            data=data
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                self._access_token = result["access_token"]
                logger.info("Got Reddit OAuth token")
            else:
                raise AuthenticationError(f"Failed to get Reddit token: {resp.status}")

    async def verify_connection(self) -> bool:
        try:
            self._reddit.user.me()
            return True
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
            messages.extend(await self._fetch_subreddit(channel_filter, since, limit))
        else:
            subreddits = self._config.extra_config.get("subreddits", [])
            for subreddit_name in subreddits:
                try:
                    subreddit_messages = await self._fetch_subreddit(subreddit_name, since, limit)
                    messages.extend(subreddit_messages)
                except Exception as e:
                    logger.warning(f"Failed to fetch r/{subreddit_name}: {e}")
                    continue

        return messages

    async def _fetch_subreddit(
        self,
        subreddit_name: str,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Message]:
        messages: List[Message] = []

        try:
            subreddit = self._reddit.subreddit(subreddit_name)

            for submission in subreddit.new(limit=limit):
                submission_msg = self._parse_submission(submission)
                if submission_msg:
                    if since and submission_msg.created_at < since:
                        continue
                    messages.append(submission_msg)

                    if submission.num_comments > 0:
                        submission.comments.replace_more(limit=3)
                        for comment in submission.comments[:10]:
                            try:
                                comment_msg = self._parse_comment(comment, submission)
                                if comment_msg:
                                    if since and comment_msg.created_at < since:
                                        continue
                                    messages.append(comment_msg)
                            except Exception:
                                continue

        except Exception as e:
            logger.error(f"Failed to fetch subreddit {subreddit_name}: {e}")

        return messages

    def _parse_submission(self, submission) -> Optional[Message]:
        if not submission.title and not submission.selftext:
            return None

        content = f"{submission.title}\n{submission.selftext or ''}".strip()

        return Message(
            platform_id=submission.id,
            content=content,
            author_id=str(submission.author) if submission.author else "[deleted]",
            author_name=str(submission.author) if submission.author else "[deleted]",
            created_at=datetime.fromtimestamp(submission.created_utc),
            metadata={
                "type": "submission",
                "subreddit": str(submission.subreddit),
                "score": submission.score,
                "num_comments": submission.num_comments,
                "url": submission.url,
                "is_self": submission.is_self,
            },
            attachments=[],
            channel_name=f"r/{submission.subreddit.display_name}",
            channel_id=str(submission.subreddit),
        )

    def _parse_comment(self, comment, parent_submission) -> Optional[Message]:
        if not comment.body:
            return None

        return Message(
            platform_id=comment.id,
            content=comment.body,
            author_id=str(comment.author) if comment.author else "[deleted]",
            author_name=str(comment.author) if comment.author else "[deleted]",
            created_at=datetime.fromtimestamp(comment.created_utc),
            metadata={
                "type": "comment",
                "subreddit": str(comment.subreddit),
                "parent_id": comment.parent_id,
                "link_id": comment.link_id,
                "score": comment.score,
            },
            attachments=[],
            channel_name=f"r/{parent_submission.subreddit.display_name}",
            channel_id=str(comment.subreddit),
        )

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        try:
            subreddit = self._reddit.subreddit(channel_id)
            return {
                "name": subreddit.display_name,
                "title": subreddit.title,
                "description": subreddit.description,
                "subscribers": subreddit.subscribers,
            }
        except Exception as e:
            logger.error(f"Failed to get subreddit info: {e}")
            return {}
