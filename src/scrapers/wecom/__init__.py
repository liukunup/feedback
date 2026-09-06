"""
企业微信 Scraper 模块

使用 uiautomator2 控制手机获取企业微信聊天信息

使用示例:
    from src.scrapers.wecom import WeComScraper
    
    scraper = WeComScraper()
    await scraper.initialize(config)
    messages = await scraper.fetch_messages()

设备准备:
    1. 安装 uiautomator2: pip install uiautomator2
    2. 手机开启 USB 调试并连接电脑
    3. 运行初始化脚本安装 ATX 应用
"""
from .wecom_api import WeComScraper

__all__ = ["WeComScraper"]
