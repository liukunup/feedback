#!/bin/bash
# QQ uiautomator2 快速设置脚本

set -e

echo "=============================================="
echo "   QQ uiautomator2 抓取器 - 快速设置"
echo "=============================================="
echo ""

# 检查依赖
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 未安装"
        exit 1
    else
        echo "✅ $1 已安装: $(command -v $1)"
    fi
}

echo "检查系统依赖..."
check_command python3
check_command pip3
check_command adb

# 检查 Android SDK
if [ -z "$ANDROID_HOME" ] && [ -z "$ANDROID_SDK_ROOT" ]; then
    echo "⚠️  未设置 ANDROID_HOME，adb 可能无法正常工作"
fi

# 检查 USB 设备
echo ""
echo "检查连接的设备..."
DEVICES=$(adb devices 2>/dev/null | grep "device$" | grep -v "List" || true)
if [ -z "$DEVICES" ]; then
    echo "❌ 未检测到设备"
    echo ""
    echo "请确保:"
    echo "  1. 手机已用 USB 连接电脑"
    echo "  2. 手机已开启开发者选项"
    echo "  3. 手机已启用 USB 调试"
    echo ""
    echo "然后重新运行此脚本"
    exit 1
else
    echo "✅ 检测到设备:"
    echo "$DEVICES"
fi

# 安装 Python 依赖
echo ""
echo "安装 Python 依赖..."
pip3 install --quiet uiautomator2 opencv-python

# 初始化 uiautomator2
echo ""
echo "初始化 uiautomator2 (请查看手机屏幕)..."
python3 -m uiautomator2 install

# 获取设备信息
echo ""
echo "获取设备信息..."
DEVICE_MODEL=$(adb shell getprop ro.product.model 2>/dev/null | tr -d '\r\n')
DEVICE_ID=$(adb devices | grep "device$" | head -1 | awk '{print $1}')
ANDROID_VERSION=$(adb shell getprop ro.build.version.release 2>/dev/null | tr -d '\r\n')

echo ""
echo "=============================================="
echo "   设备信息"
echo "=============================================="
echo "  设备 ID:   $DEVICE_ID"
echo "  设备型号:   $DEVICE_MODEL"
echo "  Android:   $ANDROID_VERSION"
echo ""

# 测试连接
echo "测试 uiautomator2 连接..."
python3 -c "
import uiautomator2 as u2
import sys
try:
    d = u2.connect('$DEVICE_ID')
    info = d.info
    print(f'✅ 连接成功!')
    print(f'   当前应用: {info.get(\"currentPackageName\", \"unknown\")}')
    print(f'   屏幕尺寸: {info.get(\"displaySizeDpX\")}x{info.get(\"displaySizeDpY\")}')
except Exception as e:
    print(f'❌ 连接失败: {e}')
    sys.exit(1)
"

echo ""
echo "=============================================="
echo "   下一步操作"
echo "=============================================="
echo ""
echo "1. 在 QQ 中打开你想抓取的聊天窗口"
echo ""
echo "2. 配置 .env 文件:"
echo "   QQ_DEVICE_ID=$DEVICE_ID"
echo ""
echo "3. 运行服务:"
echo "   docker-compose up -d"
echo ""
echo "详细文档: docker/qq-phone-setup.md"
echo "=============================================="
