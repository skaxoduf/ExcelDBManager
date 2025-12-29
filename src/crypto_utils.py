from cryptography.fernet import Fernet
import os

class CryptoManager:
    def __init__(self, key_file="secret.key"):
        self.key_file = key_file
        self.key = self._load_key()
        self.cipher = Fernet(self.key)

    def _load_key(self):
        """
        Loads the key from the current directory or generates a new one.
        """
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as key_file:
                return key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as key_file:
                key_file.write(key)
            return key

    def encrypt(self, text):
        """
        Encrypts a plain text string.
        """
        if not text: return ""
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        """
        Decrypts an encrypted string. Returns empty string on failure.
        """
        if not encrypted_text: return ""
        try:
            return self.cipher.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # If decryption fails (e.g. key changed, or plain text in file), return simple text or empty
            # But for this requirement, we assume strictly encrypted content.
            # Fallback for transition: return text as is if likely not encrypted? 
            # Fernet raises InvalidToken.
            return ""
