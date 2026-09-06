"""
QQ Scraper 模块

使用 uiautomator2 控制手机获取 QQ 聊天信息

使用示例:
    from src.scrapers.qq import QQUIAutomatorScraper
    
    scraper = QQUIAutomatorScraper()
    await scraper.initialize(config)
    messages = await scraper.fetch_messages()

设备准备:
    1. 安装 uiautomator2: pip install uiautomator2
    2. 手机开启 USB 调试并连接电脑
    3. 运行初始化脚本安装 ATX 应用
"""
from .qq_ui import QQUIAutomatorScraper

__all__ = ["QQUIAutomatorScraper"]
