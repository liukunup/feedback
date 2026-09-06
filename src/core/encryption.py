"""
加密工具模块
用于加密存储敏感信息（如 API keys, tokens）
"""
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from .config import get_settings


def _get_fernet() -> Fernet:
    """获取 Fernet 加密实例"""
    settings = get_settings()
    
    # 使用 secret_key 派生加密密钥
    # Fernet 需要 32 字节的 base64 编码密钥
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    
    return Fernet(fernet_key)


def encrypt_token(plaintext: str) -> str:
    """加密 Token"""
    if not plaintext:
        return plaintext
    
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_token(ciphertext: str) -> Optional[str]:
    """解密 Token"""
    if not ciphertext:
        return ciphertext
    
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken:
        # 如果解密失败，可能是旧数据或未加密的 token
        return ciphertext


def mask_token(token: str, visible_chars: int = 4) -> str:
    """掩码 Token，只显示前 N 个字符"""
    if not token:
        return "***"
    
    if len(token) <= visible_chars:
        return "*" * len(token)
    
    return token[:visible_chars] + "*" * (len(token) - visible_chars)
