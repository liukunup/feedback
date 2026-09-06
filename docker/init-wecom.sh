#!/bin/bash
# 企业微信 Webhook 初始化脚本

# 设置企业微信回调 URL (需要公网可访问)
WECHAT_CALLBACK_URL="${WEBHOOK_BASE_URL}/webhook/wecom/callback"

echo "企业微信配置说明:"
echo "=================="
echo ""
echo "1. 登录企业微信管理后台: https://work.weixin.qq.com/"
echo ""
echo "2. 进入「应用管理」-> 选择你的应用"
echo ""
echo "3. 在「应用消息」中设置:"
echo "   - 接收消息: 启用"
echo "   - API 接收消息 URL: ${WECHAT_CALLBACK_URL}"
echo "   - Token: ${WECOM_WEBHOOK_TOKEN}"
echo "   - EncodingAESKey: (生成或手动输入)"
echo ""
echo "4. 配置「企业可信IP」为服务器 IP"
echo ""
echo "5. 将 Token 和 EncodingAESKey 填入 .env 文件"
