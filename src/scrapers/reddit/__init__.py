"""
Reddit Scraper 模块

使用 PRAW 库通过 OAuth 获取 Reddit 帖子和评论

使用示例:
    from src.scrapers.reddit import RedditScraper
    
    scraper = RedditScraper()
    await scraper.initialize(config)
    messages = await scraper.fetch_messages(channel_filter="technology")
"""
from .reddit_api import RedditScraper

__all__ = ["RedditScraper"]
