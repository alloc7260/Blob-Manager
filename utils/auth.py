"""
Authentication utilities for TOTP and JWT
"""

import os
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional, Dict

from dotenv import load_dotenv
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 1


class TOTPAuth:
    """TOTP authentication handler"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a random TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(username: str, secret: str, issuer: str = "BlobManager") -> str:
        """Generate TOTP URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    @staticmethod
    def generate_qr_code(username: str, secret: str) -> str:
        """Generate QR code image as base64 string"""
        uri = TOTPAuth.get_totp_uri(username, secret)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)


class JWTAuth:
    """JWT token handler"""
    
    @staticmethod
    def create_access_token(data: Dict[str, str], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return {"username": username}
        except JWTError:
            return None
