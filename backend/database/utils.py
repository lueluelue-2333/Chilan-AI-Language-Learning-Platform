import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# 初始化加密上下文
# 新密码默认使用 bcrypt_sha256，兼容旧 bcrypt 哈希。
# 这样可以规避 bcrypt 的 72-byte 限制以及部分新环境下 passlib+bcrypt 的兼容问题。
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET", "fallback_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

def get_password_hash(password: str):
    """哈希化存储密码"""
    return pwd_context.hash(str(password))

def verify_password(plain_password: str, hashed_password: str):
    """校验明文密码与哈希值是否匹配"""
    return pwd_context.verify(str(plain_password), hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT 访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
