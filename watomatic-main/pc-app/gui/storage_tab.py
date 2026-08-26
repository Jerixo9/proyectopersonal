import customtkinter as ctk
from tkinter import messagebox
from backend import database

class StorageTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        # Header / Título
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(20, 10))

        lbl_title = ctk.CTkLabel(
            top_frame,
            text="💾 Almacenamiento y Limpieza de Datos",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(side="left")

        btn_refresh = ctk.CTkButton(
            top_frame,
            text="🔄 Actualizar Métricas",
            width=140,
            height=34,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.refresh_stats
        )
        btn_refresh.pack(side="right")

        # Tarjetas de Métricas de Almacenamiento
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=20, pady=10)

        # 1. Tamaño DB
        self.card_size = self._create_metric_card(
            metrics_frame,
            title="TAMAÑO BASE DE DATOS",
            initial_val="0.0 KB",
            sub_text="Archivo local pedidos.db",
            accent_color="#38bdf8"
        )
        self.card_size.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 2. Mensajes en Contexto
        self.card_msgs = self._create_metric_card(
            metrics_frame,
            title="HISTORIAL DE CHATS",
            initial_val="0 mensajes",
            sub_text="Memoria temporal de IA",
            accent_color="#a855f7"
        )
        self.card_msgs.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 3. Pedidos Almacenados
        self.card_orders = self._create_metric_card(
            metrics_frame,
            title="PEDIDOS GUARDADOS",
            initial_val="0 pedidos",
            sub_text="Registros confirmados",
            accent_color="#10b981"
        )
        self.card_orders.pack(side="left", fill="both", expand=True)

        # Contenedor de Acciones de Limpieza
        actions_box = ctk.CTkFrame(self, fg_color=("#222734", "#1a1e29"), corner_radius=12)
        actions_box.pack(fill="both", expand=True, padx=20, pady=15)

        lbl_actions_title = ctk.CTkLabel(
            actions_box,
            text="🧹 Herramientas de Mantenimiento Manual",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffffff"
        )
        lbl_actions_title.pack(anchor="w", padx=20, pady=(15, 10))

        # Fila 1: Purgar mensajes antiguos
        r1 = ctk.CTkFrame(actions_box, fg_color="transparent")
        r1.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            r1,
            text="Liberar memoria de chat conservando los últimos 7 días:",
            font=ctk.CTkFont(size=13),
            text_color="#d1d5db"
        ).pack(side="left")

        btn_purge_7 = ctk.CTkButton(
            r1,
            text="Purgar chats > 7 días",
            width=180,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._purge_chats_7_days
        )
        btn_purge_7.pack(side="right")

        # Fila 2: Vaciar todos los chats
        r2 = ctk.CTkFrame(actions_box, fg_color="transparent")
        r2.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            r2,
            text="Vaciar toda la memoria de conversación (No borra el menú ni pedidos):",
            font=ctk.CTkFont(size=13),
            text_color="#d1d5db"
        ).pack(side="left")

        btn_purge_all = ctk.CTkButton(
            r2,
            text="Vaciar Todos los Chats",
            width=180,
            fg_color="#d97706",
            hover_color="#b45309",
            command=self._purge_all_chats
        )
        btn_purge_all.pack(side="right")

        # Fila 3: Purgar pedidos finalizados
        r3 = ctk.CTkFrame(actions_box, fg_color="transparent")
        r3.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            r3,
            text="Eliminar pedidos finalizados (Despachados o Cancelados):",
            font=ctk.CTkFont(size=13),
            text_color="#d1d5db"
        ).pack(side="left")

        btn_purge_orders = ctk.CTkButton(
            r3,
            text="Limpiar Pedidos Finalizados",
            width=180,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._purge_finished_orders
        )
        btn_purge_orders.pack(side="right")

        # Fila 4: Optimizar con VACUUM
        r4 = ctk.CTkFrame(actions_box, fg_color="transparent")
        r4.pack(fill="x", padx=20, pady=6)

        ctk.CTkLabel(
            r4,
            text="Desfragmentar y optimizar archivo SQLite (VACUUM):",
            font=ctk.CTkFont(size=13),
            text_color="#d1d5db"
        ).pack(side="left")

        btn_vacuum = ctk.CTkButton(
            r4,
            text="⚡ Optimizar BD",
            width=180,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._vacuum_db
        )
        btn_vacuum.pack(side="right")

        # Sección de Limpieza Automática
        auto_box = ctk.CTkFrame(actions_box, fg_color=("#1a1e29", "#13161f"), corner_radius=10)
        auto_box.pack(fill="x", padx=20, pady=(15, 20))

        lbl_auto = ctk.CTkLabel(
            auto_box,
            text="⚙️ Programación de Limpieza Automática:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f3f4f6"
        )
        lbl_auto.pack(side="left", padx=15, pady=12)

        self.combo_auto = ctk.CTkComboBox(
            auto_box,
            values=["Desactivado", "Semanal (Mantener 7 días)", "Mensual (Mantener 30 días)", "Limitar tamaño a 50 MB"],
            width=260,
            command=self._on_auto_clean_changed
        )
        self.combo_auto.set("Semanal (Mantener 7 días)")
        self.combo_auto.pack(side="right", padx=15, pady=12)

    def _create_metric_card(self, parent, title: str, initial_val: str, sub_text: str, accent_color: str):
        card = ctk.CTkFrame(parent, fg_color=("#222734", "#1a1e29"), corner_radius=12)

        lbl_t = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#9ca3af"
        )
        lbl_t.pack(anchor="w", padx=15, pady=(12, 2))

        lbl_v = ctk.CTkLabel(
            card,
            text=initial_val,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=accent_color
        )
        lbl_v.pack(anchor="w", padx=15, pady=(0, 2))
        card.lbl_val = lbl_v

        lbl_s = ctk.CTkLabel(
            card,
            text=sub_text,
            font=ctk.CTkFont(size=11),
            text_color="#6b7280"
        )
        lbl_s.pack(anchor="w", padx=15, pady=(0, 12))

        return card

    def refresh_stats(self):
        stats = database.get_storage_stats()
        self.card_size.lbl_val.configure(text=stats["size_formatted"])
        self.card_msgs.lbl_val.configure(text=f"{stats['total_mensajes']} msgs")
        self.card_orders.lbl_val.configure(text=f"{stats['total_pedidos']} ({stats['pedidos_pendientes']} pend.)")

    def _purge_chats_7_days(self):
        if messagebox.askyesno("Confirmar purga", "¿Deseas eliminar los mensajes de chat con más de 7 días de antigüedad?"):
            deleted = database.purge_chat_messages(days_older_than=7)
            self.refresh_stats()
            messagebox.showinfo("Limpieza completada", f"Se eliminaron {deleted} mensajes antiguos.")

    def _purge_all_chats(self):
        if messagebox.askyesno("Confirmar vaciado", "¿Estás seguro de que deseas vaciar TODOS los mensajes de conversación?"):
            deleted = database.purge_chat_messages(days_older_than=0)
            self.refresh_stats()
            messagebox.showinfo("Limpieza completada", f"Se eliminaron {deleted} mensajes de chat.")

    def _purge_finished_orders(self):
        if messagebox.askyesno("Confirmar limpieza de pedidos", "¿Deseas eliminar todos los pedidos Despachados o Cancelados?"):
            deleted = database.purge_completed_orders()
            self.refresh_stats()
            messagebox.showinfo("Limpieza completada", f"Se eliminaron {deleted} pedidos finalizados.")

    def _vacuum_db(self):
        database.optimize_db()
        self.refresh_stats()
        messagebox.showinfo("Optimización", "La base de datos ha sido optimizada con éxito.")

    def _on_auto_clean_changed(self, choice: str):
        pass
