"""
Password Hashing and Verification

Secure password handling using bcrypt.
"""

from passlib.context import CryptContext


# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        password: Plaintext password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.
    
    Args:
        plain_password: Plaintext password to verify
        hashed_password: Hashed password to check against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be rehashed.
    
    This is useful when upgrading hashing algorithms or increasing
    the number of rounds for better security.
    
    Args:
        hashed_password: Existing hashed password
        
    Returns:
        True if the hash should be regenerated
    """
    return pwd_context.needs_update(hashed_password)
