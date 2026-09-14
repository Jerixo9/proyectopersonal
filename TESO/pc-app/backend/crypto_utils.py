import base64
import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Clave AES de 256 bits (32 bytes) fija y compartida entre PC y Celular.
# IMPORTANTE: Si se cambia aquí, DEBE cambiarse exactamente igual en AESGCMUtils.java de Android.
SECRET_KEY_STR = "P9y/1Y8L6q3X7r2H5v8W0b4N1c7M5z2K9x/1V8L6q3X=" # Base64 encoded 32 bytes (example)
# Let's use a simpler 32-byte string encoded in base64: "watomatic_secure_key_12345678901" (32 chars)
SECRET_KEY_BYTES = b"watomatic_secure_key_12345678901"

def _get_aesgcm() -> AESGCM:
    return AESGCM(SECRET_KEY_BYTES)

def encrypt_payload(data: dict) -> dict:
    """
    Toma un diccionario, lo convierte a JSON string, lo encripta y devuelve
    un diccionario con el IV y el Ciphertext codificados en Base64.
    """
    try:
        aesgcm = _get_aesgcm()
        nonce = os.urandom(12) # GCM standard nonce size
        
        json_data = json.dumps(data).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, json_data, None)
        
        return {
            "iv": base64.b64encode(nonce).decode('utf-8'),
            "data": base64.b64encode(ciphertext).decode('utf-8')
        }
    except Exception as e:
        print(f"Error encrypting payload: {e}")
        return {}

def decrypt_payload(encrypted_dict: dict) -> dict:
    """
    Toma un diccionario con 'iv' y 'data' (ambos base64), los desencripta y
    devuelve el diccionario original.
    """
    try:
        iv = base64.b64decode(encrypted_dict.get("iv", ""))
        ciphertext = base64.b64decode(encrypted_dict.get("data", ""))
        
        if not iv or not ciphertext:
            raise ValueError("Missing 'iv' or 'data' in encrypted payload.")
            
        aesgcm = _get_aesgcm()
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext, None)
        
        return json.loads(decrypted_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Error decrypting payload: {e}")
        return {}
