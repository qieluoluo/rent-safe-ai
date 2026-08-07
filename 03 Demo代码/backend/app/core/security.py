import hashlib
import secrets


def hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 生成不可逆密码摘要。认证能力将在后续阶段接入。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 600_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"
