"""
QQ UI Automator Scraper - 通过手机获取 QQ 消息
"""
import asyncio
import logging
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

from ..base import BaseScraper, ChannelConfig, Message, Platform, ScraperRegistry
from ...core.exceptions import ScraperError

logger = logging.getLogger(__name__)


@dataclass
class QQConversation:
    """QQ 会话"""
    name: str
    conv_id: str
    type: str = "group"
    unread: int = 0


class UIAutomator2Client:
    """uiautomator2 客户端"""

    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id or ""
        self._atx_url: Optional[str] = None

    def _run_adb(self, command: str) -> str:
        device_arg = f"-s {self.device_id}" if self.device_id else ""
        cmd = f"adb {device_arg} {command}".strip()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise ScraperError(f"ADB error: {result.stderr}")
        return result.stdout.strip()

    async def connect(self) -> bool:
        try:
            devices = self._run_adb("devices").split("\n")[1:]
            connected = any("device" in d and not "offline" in d for d in devices)
            if not connected:
                raise ScraperError("No device connected")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def _get_screen_size(self) -> tuple:
        output = self._run_adb("shell wm size")
        if "x" in output:
            parts = output.split("x")
            return (int(parts[0]), int(parts[1]))
        return (1080, 1920)

    async def screenshot(self) -> bytes:
        return self._run_adb("exec-out screencap -p").encode()

    async def dump_hierarchy(self) -> str:
        self._run_adb("exec-out uiautomator dump /dev/tty")
        time.sleep(0.5)
        return self._run_adb("shell cat /sdcard/window_dump.xml")

    def click(self, x: int, y: int) -> bool:
        self._run_adb(f"shell input tap {x} {y}")
        return True

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        self._run_adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
        return True

    def press_back(self) -> bool:
        self._run_adb("shell input keyevent BACK")
        return True

    def press_home(self) -> bool:
        self._run_adb("shell input keyevent HOME")
        return True


@ScraperRegistry.register(Platform.QQ)
class QQUIAutomatorScraper(BaseScraper):
    """基于 uiautomator2 的 QQ 消息抓取器"""

    QQ_PACKAGE = "com.tencent.mobileqq"
    QQ_LAUNCHER_ACTIVITY = ".activity.SplashActivity"

    def __init__(self):
        super().__init__()
        self._client: Optional[UIAutomator2Client] = None
        self._event_callbacks: List[Callable] = []
        self._running = False
        self._message_counter = 0

    async def initialize(self, config: ChannelConfig) -> None:
        self._config = config
        device_id = config.extra_config.get("device_id")
        self._client = UIAutomator2Client(device_id)

        if not await self._client.connect():
            raise ScraperError("Failed to connect to device")

        await self._launch_qq()
        self._initialized = True
        logger.info("QQ scraper (uiautomator2) initialized")

    async def close(self) -> None:
        self._running = False
        if self._client:
            self._client.press_home()
        self._initialized = False

    async def verify_connection(self) -> bool:
        if not self._client:
            return False
        try:
            result = self._client._run_adb(f"shell dumpsys activity activities | grep {self.QQ_PACKAGE}")
            return self.QQ_PACKAGE in result
        except Exception:
            return False

    async def _launch_qq(self) -> None:
        logger.info("Launching QQ...")
        is_running = await self.verify_connection()

        if not is_running:
            self._client._run_adb(
                f"shell am start -n {self.QQ_PACKAGE}/{self.QQ_LAUNCHER_ACTIVITY}"
            )
            time.sleep(3)

        await self._wait_for_main_page()

    async def _wait_for_main_page(self, timeout: int = 30) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                xml = await self._client.dump_hierarchy()
                if "消息" in xml or "联系人" in xml:
                    return True
            except Exception:
                pass
            time.sleep(1)
        raise ScraperError("Timeout waiting for QQ main page")

    async def fetch_messages(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
        channel_filter: Optional[str] = None
    ) -> List[Message]:
        if not self._initialized:
            raise ScraperError("Scraper not initialized")

        messages: List[Message] = []
        conversations = await self._get_conversations()

        for conv in conversations:
            if channel_filter and conv.conv_id != channel_filter:
                continue

            try:
                conv_messages = await self._fetch_conversation_messages(conv, since, limit)
                messages.extend(conv_messages)
                if len(messages) >= limit:
                    return messages[:limit]
            except Exception as e:
                logger.warning(f"Failed to fetch conversation {conv.name}: {e}")

            await self._return_to_conversation_list()

        return messages

    async def _get_conversations(self) -> List[QQConversation]:
        conversations = []
        xml = await self._client.dump_hierarchy()

        try:
            root = ET.fromstring(xml)
            for node in root.iter():
                res_id = node.get("resource-id", "")
                text = node.get("text", "")

                if "conversation" in res_id.lower():
                    if text and len(text) < 50:
                        conv_type = "group" if "群" not in text else "private"
                        conv_id = res_id.split("/")[-1] if "/" in res_id else text
                        conversations.append(QQConversation(
                            name=text,
                            conv_id=conv_id,
                            type=conv_type
                        ))
        except ET.ParseError:
            pass

        logger.info(f"Found {len(conversations)} conversations")
        return conversations[:20]

    async def _fetch_conversation_messages(
        self,
        conv: QQConversation,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Message]:
        messages: List[Message] = []
        await self._click_conversation(conv)
        await asyncio.sleep(1)

        page_count = 0
        max_pages = 10

        while page_count < max_pages and len(messages) < limit:
            xml = await self._client.dump_hierarchy()
            page_messages = await self._parse_message_list(xml, conv)
            messages.extend(page_messages)

            if not await self._load_more_messages():
                break

            page_count += 1
            await asyncio.sleep(0.5)

        return messages

    async def _click_conversation(self, conv: QQConversation) -> None:
        xml = await self._client.dump_hierarchy()
        try:
            root = ET.fromstring(xml)
            for node in root.iter():
                text = node.get("text", "")
                bounds = node.get("bounds", "")
                if conv.name in text and bounds:
                    coords = self._parse_bounds(bounds)
                    if coords:
                        cx, cy = (coords[0] + coords[2]) // 2, (coords[1] + coords[3]) // 2
                        self._client.click(cx, cy)
                        return
        except ET.ParseError:
            pass

        self._client.click(540, 300)

    async def _parse_message_list(self, xml: str, conv: QQConversation) -> List[Message]:
        messages = []
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return messages

        for node in root.iter():
            res_id = node.get("resource-id", "")
            if "chatmsg" in res_id.lower() or "bubble" in res_id.lower():
                msg = self._parse_message_node(node, conv)
                if msg:
                    messages.append(msg)

        return messages

    def _parse_message_node(self, node: ET.Element, conv: QQConversation) -> Optional[Message]:
        try:
            content = ""
            author = ""
            time_str = ""

            for child in node.iter():
                res_id = child.get("resource-id", "")
                text = child.get("text", "")

                if "nick" in res_id.lower() or "name" in res_id.lower():
                    author = text
                elif "content" in res_id.lower():
                    content = text
                elif "time" in res_id.lower():
                    time_str = text

            if not content:
                return None

            self._message_counter += 1
            return Message(
                platform_id=f"{conv.conv_id}_{self._message_counter}",
                content=content,
                author_id=author or "unknown",
                author_name=author or "未知用户",
                created_at=self._parse_time(time_str),
                metadata={"conversation": conv.name, "type": conv.type},
                attachments=[],
                channel_name=conv.name,
                channel_id=conv.conv_id,
            )
        except Exception:
            return None

    async def _load_more_messages(self) -> bool:
        screen_size = self._client._get_screen_size()
        start_x = screen_size[0] // 2
        start_y = int(screen_size[1] * 0.7)
        end_x = start_x
        end_y = int(screen_size[1] * 0.3)
        self._client.swipe(start_x, start_y, end_x, end_y, 500)
        return True

    async def _return_to_conversation_list(self) -> None:
        self._client.press_back()
        await asyncio.sleep(0.5)
        self._client.press_back()
        await asyncio.sleep(0.5)

    def _parse_bounds(self, bounds: str) -> Optional[tuple]:
        try:
            bounds = bounds.strip("[]")
            parts = bounds.split("][")
            x1, y1 = map(int, parts[0].split(","))
            x2, y2 = map(int, parts[1].split(","))
            return (x1, y1, x2, y2)
        except Exception:
            return None

    def _parse_time(self, time_str: str) -> datetime:
        if not time_str:
            return datetime.now()
        try:
            formats = ["%H:%M", "%Y-%m-%d %H:%M", "%m-%d %H:%M"]
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        return datetime.now()

    def register_event_callback(self, callback: Callable) -> None:
        self._event_callbacks.append(callback)

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        return {"id": channel_id, "name": channel_id, "type": "qq_conversation"}
