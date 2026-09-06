"""
Discord Scraper 模块

使用 discord.py 库通过 Bot Token 获取 Discord 频道消息

使用示例:
    from src.scrapers.discord import DiscordPyScraper
    
    scraper = DiscordPyScraper()
    await scraper.initialize(config)
    messages = await scraper.fetch_messages()
"""
from .discord_bot import DiscordPyScraper, DiscordCachedScraper

__all__ = ["DiscordPyScraper", "DiscordCachedScraper"]
