"""
Encryption utilities for securing database connection strings
"""
import os
from cryptography.fernet import Fernet


class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self):
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        # Ensure key is bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return base64-encoded ciphertext"""
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        plaintext_bytes = plaintext.encode('utf-8')
        encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
        return encrypted_bytes.decode('utf-8')
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext and return plaintext"""
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")
        
        ciphertext_bytes = ciphertext.encode('utf-8')
        decrypted_bytes = self.cipher.decrypt(ciphertext_bytes)
        return decrypted_bytes.decode('utf-8')


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key().decode('utf-8')


# Global instance
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """Get or create the global encryption manager instance"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager

