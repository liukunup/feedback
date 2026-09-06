"""
Scrapers 模块 - 多渠道消息抓取器

支持以下平台:
- Discord: 使用 discord.py
- Reddit: 使用 PRAW
- QQ: 使用手机 uiautomator2 控制 QQ 应用获取聊天记录
- 企业微信: 使用手机 uiautomator2 控制企业微信应用获取聊天记录

设备要求:
- Android 手机一台
- 手机开启 USB 调试模式
- 安装 uiautomator2 和 ATX 应用
"""
from .base import BaseScraper, ChannelConfig, Message, Platform, ScraperRegistry

# 导入所有平台实现
from .discord import DiscordPyScraper, DiscordCachedScraper
from .reddit import RedditScraper
from .qq import QQUIAutomatorScraper
from .wecom import WeComScraper

__all__ = [
    # 基类
    "BaseScraper",
    "ChannelConfig",
    "Message",
    "Platform",
    "ScraperRegistry",
    # Discord
    "DiscordPyScraper",
    "DiscordCachedScraper",
    # Reddit
    "RedditScraper",
    # QQ (uiautomator2)
    "QQUIAutomatorScraper",
    # 企业微信 (uiautomator2)
    "WeComScraper",
]
