import os
import math
import struct
import wave
import threading
import sys

SOUND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
CHIME_WAV = os.path.join(SOUND_DIR, "new_order_chime.wav")

def generate_chime_wav(filepath: str = CHIME_WAV):
    """Genera un archivo de audio WAV con un acorde armónico y agradable tipo campana de restaurante."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        return
    
    sample_rate = 44100
    duration = 1.0  # segundos
    num_samples = int(sample_rate * duration)
    
    # Frecuencias para un acorde dulce de campana (Do Mayor: C5 = 523.25, E5 = 659.25, G5 = 783.99, C6 = 1046.50)
    freqs = [523.25, 659.25, 783.99, 1046.50]
    
    with wave.open(filepath, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = []
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Decay exponencial para sonido percusivo de campana
            decay = math.exp(-3.5 * t)
            
            sample_val = 0.0
            for idx, f in enumerate(freqs):
                amplitude = (0.35 / (idx + 1))
                sample_val += amplitude * math.sin(2.0 * math.pi * f * t)
            
            sample_val *= decay
            # Clamp
            sample_val = max(-1.0, min(1.0, sample_val))
            packed_sample = struct.pack("<h", int(sample_val * 32767.0))
            frames.append(packed_sample)
            
        wav_file.writeframes(b"".join(frames))

def play_order_alert_sound():
    """Reproduce el sonido de nuevo pedido en un hilo independiente para no bloquear."""
    def _play():
        try:
            generate_chime_wav(CHIME_WAV)
            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(CHIME_WAV, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                # Fallback pygame
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(CHIME_WAV)
                pygame.mixer.music.play()
        except Exception:
            try:
                # Fallback tono básico
                if sys.platform == "win32":
                    import winsound
                    winsound.Beep(880, 250)
                    winsound.Beep(1174, 350)
            except Exception:
                pass

    t = threading.Thread(target=_play, daemon=True)
    t.start()
