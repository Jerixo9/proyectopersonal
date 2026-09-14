import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from backend import network_utils
from backend import app as backend_app

class FooterBar(ctk.CTkFrame):
    def __init__(self, master, port: int = 8000, **kwargs):
        super().__init__(master, height=45, corner_radius=0, fg_color=("#1e222d", "#14171f"), **kwargs)
        self.port = port
        self.raw_ip = network_utils.get_local_ip()
        self.full_url = f"http://{self.raw_ip}:{self.port}"
        self.is_ip_visible = True
        
        self.grid_columnconfigure(1, weight=1)
        self._build_ui()

    def _build_ui(self):
        # Frame Izquierdo: Servidor y Visor de IP
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", padx=15, pady=6)

        # Badge Servidor
        self.lbl_server_status = ctk.CTkLabel(
            left_frame,
            text="🟢 Servidor Activo",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#10b981"
        )
        self.lbl_server_status.pack(side="left", padx=(0, 10))

        # Separador visual
        sep1 = ctk.CTkLabel(left_frame, text="|", text_color="#4b5563", font=ctk.CTkFont(size=13))
        sep1.pack(side="left", padx=6)

        lbl_ip_title = ctk.CTkLabel(
            left_frame,
            text="IP Servidor (para App Móvil):",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        lbl_ip_title.pack(side="left", padx=(6, 4))

        self.lbl_ip_value = ctk.CTkLabel(
            left_frame,
            text=self.full_url,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_ip_value.pack(side="left", padx=(0, 6))

        # Botón con ícono de Ojo para ocultar / revelar IP
        self.btn_eye = ctk.CTkButton(
            left_frame,
            text="👁️",
            width=28,
            height=26,
            corner_radius=6,
            fg_color=("#374151", "#272e3f"),
            hover_color="#4b5563",
            command=self.toggle_ip_visibility
        )
        self.btn_eye.pack(side="left", padx=(0, 4))

        # Botón Copiar IP
        self.btn_copy = ctk.CTkButton(
            left_frame,
            text="📋 Copiar",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            corner_radius=6,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.copy_ip_to_clipboard
        )
        self.btn_copy.pack(side="left", padx=4)

        # Frame Derecho: Semáforo de Conexión del Teléfono Móvil
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", padx=15, pady=6)

        self.lbl_phone_status = ctk.CTkLabel(
            right_frame,
            text="🔴 Móvil Desconectado",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ef4444"
        )
        self.lbl_phone_status.pack(side="right")

    def toggle_ip_visibility(self):
        self.is_ip_visible = not self.is_ip_visible
        if self.is_ip_visible:
            self.lbl_ip_value.configure(text=self.full_url)
            self.btn_eye.configure(text="👁️")
        else:
            masked = network_utils.mask_ip(self.raw_ip)
            self.lbl_ip_value.configure(text=f"http://{masked}:{self.port}")
            self.btn_eye.configure(text="🙈")

    def copy_ip_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.full_url)
        # Feedback visual temporal
        self.btn_copy.configure(text="¡Copiado!", fg_color="#10b981")
        self.after(1500, lambda: self.btn_copy.configure(text="📋 Copiar", fg_color="#3b82f6"))

    def update_connection_state(self):
        """Actualiza el semáforo y texto del estado del teléfono según el heartbeat."""
        is_connected = backend_app.is_phone_connected()
        sec = backend_app.get_seconds_since_last_ping()
        
        if is_connected:
            device = backend_app.heartbeat_state.get("device_name", "Android")
            ping_text = f"hace {sec}s" if sec is not None else "reciente"
            self.lbl_phone_status.configure(
                text=f"🟢 Móvil Conectado ({device} - Ping {ping_text})",
                text_color="#10b981"
            )
        else:
            self.lbl_phone_status.configure(
                text="🔴 Móvil Desconectado (Esperando señal...)",
                text_color="#ef4444"
            )
