import threading
import customtkinter as ctk
from tkinter import messagebox
from backend import app as backend_app
from backend import database

class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.sim_client_id = "Cliente_Prueba_PC"
        self._build_ui()
        self.check_ollama()

    def _build_ui(self):
        # Frame dividido en dos columnas: Izquierda (Configuración Servidor e IA), Derecha (Simulador de Chat en Vivo)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================= COLUMNA IZQUIERDA: CONFIGURACIÓN =================
        left_box = ctk.CTkScrollableFrame(self, fg_color=("#222734", "#1a1e29"), corner_radius=12)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)

        lbl_cfg_title = ctk.CTkLabel(
            left_box,
            text="⚙️ Configuración del Motor de IA y Servidor",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        lbl_cfg_title.pack(anchor="w", padx=15, pady=(15, 12))

        # 1. Estado de Ollama
        ollama_card = ctk.CTkFrame(left_box, fg_color=("#1a1e29", "#13161f"), corner_radius=10)
        ollama_card.pack(fill="x", padx=15, pady=(0, 15))

        lbl_ol_title = ctk.CTkLabel(
            ollama_card,
            text="🧠 Motor Local Ollama (Llama 3.1)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_ol_title.pack(anchor="w", padx=12, pady=(10, 4))

        self.lbl_ollama_status = ctk.CTkLabel(
            ollama_card,
            text="Comprobando conexión con Ollama...",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        self.lbl_ollama_status.pack(anchor="w", padx=12, pady=(0, 8))

        btn_check_ol = ctk.CTkButton(
            ollama_card,
            text="🔍 Verificar Ollama",
            height=30,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.check_ollama
        )
        btn_check_ol.pack(anchor="w", padx=12, pady=(0, 10))

        # 2. Configuración de Parámetros
        ctk.CTkLabel(left_box, text="URL del Servidor Ollama:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(0, 2))
        self.entry_ollama_url = ctk.CTkEntry(left_box, height=35)
        self.entry_ollama_url.insert(0, backend_app.ai_engine.ollama_url)
        self.entry_ollama_url.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(left_box, text="Modelo de IA Local:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(0, 2))
        self.entry_model = ctk.CTkEntry(left_box, height=35)
        self.entry_model.insert(0, backend_app.ai_engine.model)
        self.entry_model.pack(fill="x", padx=15, pady=(0, 15))

        self.sw_sim_mode = ctk.CTkSwitch(
            left_box,
            text="Modo Simulación / Fallback Automático (Recomendado)",
            command=self._on_sim_mode_toggle
        )
        self.sw_sim_mode.select()
        self.sw_sim_mode.pack(anchor="w", padx=15, pady=(0, 15))

        btn_save_cfg = ctk.CTkButton(
            left_box,
            text="💾 Aplicar Cambios de IA",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self._save_ai_config
        )
        btn_save_cfg.pack(fill="x", padx=15, pady=(0, 15))

        # ================= COLUMNA DERECHA: SIMULADOR DE CHAT =================
        right_box = ctk.CTkFrame(self, fg_color=("#222734", "#1a1e29"), corner_radius=12)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(8, 15), pady=15)
        right_box.grid_rowconfigure(1, weight=1)
        right_box.grid_columnconfigure(0, weight=1)

        # Header del Simulador
        sim_header = ctk.CTkFrame(right_box, fg_color="transparent")
        sim_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))

        lbl_sim_title = ctk.CTkLabel(
            sim_header,
            text="💬 Simulador y Probador de Chat WhatsApp",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#10b981"
        )
        lbl_sim_title.pack(side="left")

        btn_clear_sim = ctk.CTkButton(
            sim_header,
            text="🧹 Limpiar Chat",
            width=95,
            height=28,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._clear_sim_chat
        )
        btn_clear_sim.pack(side="right")

        # Área de Mensajes con Scroll
        self.txt_chat_history = ctk.CTkTextbox(
            right_box,
            font=ctk.CTkFont(size=13),
            wrap="word",
            state="disabled",
            fg_color=("#1a1e29", "#13161f")
        )
        self.txt_chat_history.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

        # Input de Mensaje de Prueba
        input_bar = ctk.CTkFrame(right_box, fg_color="transparent")
        input_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))

        self.entry_test_msg = ctk.CTkEntry(
            input_bar,
            placeholder_text="Escribe un mensaje de prueba (Ej: 'Hola, quiero una hamburguesa')...",
            height=40
        )
        self.entry_test_msg.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_test_msg.bind("<Return>", lambda e: self._send_test_message())

        self.btn_send_sim = ctk.CTkButton(
            input_bar,
            text="Enviar 📤",
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._send_test_message
        )
        self.btn_send_sim.pack(side="right")

        self._append_system_msg("Bienvenido al simulador. Escribe cualquier mensaje para probar el flujo de atención y toma de pedidos con IA.")

    def check_ollama(self):
        def _check():
            status = backend_app.ai_engine.check_ollama_status()
            if status["online"]:
                if status["has_target_model"]:
                    txt = f"🟢 Ollama Online • Modelo '{status['target_model']}' Listo"
                    color = "#10b981"
                else:
                    txt = f"🟡 Ollama Online • Modelo '{status['target_model']}' no encontrado (Modelos: {', '.join(status['available_models']) or 'ninguno'})"
                    color = "#f59e0b"
            else:
                txt = "🔴 Ollama no detectado en localhost:11434 (Usando simulación inteligente)"
                color = "#ef4444"
                
            self.lbl_ollama_status.configure(text=txt, text_color=color)

        threading.Thread(target=_check, daemon=True).start()

    def _save_ai_config(self):
        url = self.entry_ollama_url.get().strip()
        model = self.entry_model.get().strip()
        backend_app.ai_engine.ollama_url = url
        backend_app.ai_engine.model = model
        self.check_ollama()
        messagebox.showinfo("Configuración", "Parámetros de IA actualizados con éxito.")

    def _on_sim_mode_toggle(self):
        backend_app.ai_engine.simulation_mode = not bool(self.sw_sim_mode.get())

    def _send_test_message(self):
        msg = self.entry_test_msg.get().strip()
        if not msg:
            return

        self.entry_test_msg.delete(0, "end")
        self._append_user_msg(msg)
        self.btn_send_sim.configure(state="disabled", text="Pensando...")

        def _process():
            reply, order = backend_app.ai_engine.process_incoming_message(
                id_cliente=self.sim_client_id,
                incoming_msg=msg
            )
            
            self.after(0, lambda: self._on_msg_processed(reply, order))

        threading.Thread(target=_process, daemon=True).start()

    def _on_msg_processed(self, reply: str, order):
        self.btn_send_sim.configure(state="normal", text="Enviar 📤")
        self._append_ai_msg(reply)
        if order:
            self._append_system_msg(f"🎉 ¡PEDIDO CREADO EXITOSAMENTE! (ID #{order['id']}) - Ver en Monitor de Pedidos.")

    def _append_user_msg(self, text: str):
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.insert("end", f"\n👤 Cliente (WhatsApp):\n{text}\n")
        self.txt_chat_history.see("end")
        self.txt_chat_history.configure(state="disabled")

    def _append_ai_msg(self, text: str):
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.insert("end", f"\n🤖 Asistente IA:\n{text}\n")
        self.txt_chat_history.see("end")
        self.txt_chat_history.configure(state="disabled")

    def _append_system_msg(self, text: str):
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.insert("end", f"\nℹ️ {text}\n")
        self.txt_chat_history.see("end")
        self.txt_chat_history.configure(state="disabled")

    def _clear_sim_chat(self):
        database.reset_client_session(self.sim_client_id)
        self.txt_chat_history.configure(state="normal")
        self.txt_chat_history.delete("1.0", "end")
        self.txt_chat_history.configure(state="disabled")
        self._append_system_msg("Chat y carrito de prueba reiniciados por completo.")
