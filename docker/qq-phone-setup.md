# QQ 手机端抓取方案

## 方案概述

使用 `uiautomator2` 通过 USB 或 WiFi 连接 Android 手机，模拟用户操作获取 QQ 消息。

## 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        主机 (Linux/Mac/Windows)                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Python Scraper                            │   │
│  │  ┌───────────────┐    ┌──────────────┐    ┌─────────────┐  │   │
│  │  │ uiautomator2  │    │  Message      │    │   Storage   │  │   │
│  │  │    Client     │───▶│   Parser      │───▶│  Processor  │  │   │
│  │  └───────┬───────┘    └──────────────┘    └─────────────┘  │   │
│  │          │                                                  │   │
│  │          │ ATX HTTP API / ADB                               │   │
│  └──────────┼──────────────────────────────────────────────────┘   │
│              │                                                        │
└──────────────┼──────────────────────────────────────────────────────┘
               │
        ┌──────▼──────┐
        │   USB/WiFi  │
        └──────┬──────┘
               │
┌──────────────┼──────────────────────────────────────────────────────┐
│              │              Android 手机                             │
│         ┌────▼────┐                                               │
│         │   QQ    │                                               │
│         └─────────┘                                               │
│                                                                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │
│  │ ATX Agent   │    │ uiautomator2│    │  QQ (需要保持前台)   │   │
│  │ (可选)      │    │  (系统权限)  │    │                     │   │
│  └─────────────┘    └─────────────┘    └─────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

## 准备工作

### 1. 手机端设置

#### 要求
- Android 5.0 或更高版本
- 已开启 **开发者选项** 和 **USB 调试**
- 安装 **QQ** 并登录

#### 可选：安装 ATX Agent (推荐)

ATX Agent 可以获得更稳定、更快速的控制能力。

```bash
# 方法1: 通过 pip 安装 atx
pip install opencv-python uiautomator2

# 方法2: 下载 ATX Agent APK
# https://github.com/openatx/atx-agent/releases
# 下载对应架构的 atx-agent
adb push atx-agent /data/local/tmp/
adb shell chmod 755 /data/local/tmp/atx-agent
adb shell /data/local/tmp/atx-agent -d
```

#### 安装 uiautomator2

```bash
# 通过 Python 安装
pip install uiautomator2

# 初始化 (会自动安装 helper APK 到手机)
python -m uiautomator2 init
```

### 2. 连接方式

#### USB 连接

```bash
# 1. 手机用 USB 连接电脑
# 2. 启用 USB 调试
adb devices
# 应该显示: <serial> device

# 3. 配置 (设备 ID 为 adb devices 显示的序列号)
```

#### WiFi 连接

```bash
# 1. 手机和电脑在同一网络
# 2. 通过 USB 获取手机 IP
adb shell ip addr show wlan0 | grep 'inet '
# 输出: inet 192.168.1.100/24

# 3. 启用 WiFi 调试
adb tcpip 5555

# 4. 断开 USB，连接 WiFi
adb connect 192.168.1.100:5555
```

### 3. QQ 设置

1. **保持 QQ 在前台**: uiautomator2 需要 QQ 可见才能获取 UI 元素
2. **关闭动画**: 设置 > 辅助功能 > 开发者选项 > 窗口动画缩放 > 关闭
3. **授予权限**: 如果 uiautomator2 提示需要权限，授予即可

## 配置示例

### .env 配置

```env
# QQ 抓取配置
QQ_DEVICE_ID=R3CR12345     # adb devices 显示的设备 ID
```

### 渠道配置 (数据库)

```json
{
  "platform": "qq",
  "name": "我的 QQ 群",
  "config": {
    "device_id": "R3CR12345",
    "fetch_interval": 300,
    "auto_scroll": true,
    "load_pages": 5
  }
}
```

## 使用方式

### 1. 本地开发测试

```bash
# 测试连接
python -c "
import uiautomator2 as u2
d = u2.connect('R3CR12345')  # 或 '192.168.1.100:5555' (WiFi)
print(d.info)
"
```

### 2. Docker 部署

```yaml
# docker-compose.yml 中添加
services:
  qq-scraper:
    build:
      context: .
      dockerfile: docker/Dockerfile.qq-scraper
    devices:
      - /dev/bus/usb/001/001  # USB 设备
    environment:
      QQ_DEVICE_ID: ${QQ_DEVICE_ID}
    volumes:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true  # 需要访问 USB
```

### 3. 运行服务

```bash
# 单独启动 QQ 抓取任务
celery -A src.workers.tasks worker --loglevel=info -Q qq_fetch

# 或通过 API 触发
curl -X POST http://localhost:8000/api/channels/{channel_id}/fetch
```

## 注意事项

### ⚠️ 重要提示

1. **合规性**: 
   - 仅抓取自己账号有权限查看的消息
   - 不要用于商业用途或未经授权的数据收集
   - 遵守 QQ 用户协议

2. **稳定性**:
   - 保持手机屏幕常亮
   - 关闭省电模式
   - 确保网络稳定

3. **性能**:
   - 每次抓取约需 30-60 秒
   - 建议间隔 5-10 分钟
   - 避免频繁操作导致账号异常

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 设备未找到 | 检查 USB 调试是否开启，`adb devices` 是否显示设备 |
| ATX 连接失败 | 确保手机和电脑在同一网络，防火墙允许端口 7912 |
| UI 元素找不到 | QQ 版本可能不同，尝试更新 XML 解析逻辑 |
| 抓取超时 | 减少 `load_pages` 数量，增加超时时间 |

## 备选方案

如果 uiautomator2 不稳定，可以考虑：

1. **go-cqhttp**: 基于协议逆向，需要 QQ 号和密码
2. **PC 端 QQ**: 使用 Windows 虚拟机 + 消息导出插件
3. **企业微信**: 如果是企业 QQ，可以直接用企业微信 API
