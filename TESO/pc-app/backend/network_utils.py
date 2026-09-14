import socket
import re

def get_local_ip() -> str:
    """Detecta la dirección IP local de red del equipo."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No se envía tráfico real, solo se abre socket para identificar la interfaz LAN
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def mask_ip(ip_str: str) -> str:
    """Oculta los octetos de la IP para modo privacidad (ej: ***.***.*.*:8000)."""
    if not ip_str:
        return "***.***.*.*"
    
    parts = ip_str.split(":")
    ip_part = parts[0]
    port_part = f":{parts[1]}" if len(parts) > 1 else ""
    
    octets = ip_part.split(".")
    if len(octets) == 4:
        masked_ip = f"***.***.*.{octets[3]}" if octets[3].isdigit() else "***.***.*.*"
    else:
        masked_ip = "***.***.*.*"
        
    return f"{masked_ip}{port_part}"

def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Verifica si un puerto está disponible para enlazar."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False
