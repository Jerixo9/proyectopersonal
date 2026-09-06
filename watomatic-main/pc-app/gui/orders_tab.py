import customtkinter as ctk
from typing import Optional
from tkinter import messagebox
from backend import database

STATUS_COLORS = {
    "Pendiente": ("#d97706", "#f59e0b"),
    "En preparación": ("#2563eb", "#3b82f6"),
    "Enviado": ("#059669", "#10b981"),
    "Despachado": ("#059669", "#10b981"),
    "Cancelado": ("#dc2626", "#ef4444")
}

class OrdersTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_filter = "Todos"
        self._build_ui()
        self.refresh_orders()

    def _build_ui(self):
        # 1. Barra de Estadísticas y Contadores Rápidos
        self.stats_frame = ctk.CTkFrame(self, fg_color=("#222734", "#1a1e29"), corner_radius=12)
        self.stats_frame.pack(fill="x", padx=15, pady=(15, 10))

        self.lbl_stat_pending = ctk.CTkLabel(
            self.stats_frame,
            text="⏳ Pendientes: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f59e0b"
        )
        self.lbl_stat_pending.pack(side="left", padx=20, pady=10)

        self.lbl_stat_prep = ctk.CTkLabel(
            self.stats_frame,
            text="👨‍🍳 En Preparación: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_stat_prep.pack(side="left", padx=20, pady=10)

        self.lbl_stat_sent = ctk.CTkLabel(
            self.stats_frame,
            text="🚀 Enviados: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#10b981"
        )
        self.lbl_stat_sent.pack(side="left", padx=20, pady=10)

        self.lbl_stat_total = ctk.CTkLabel(
            self.stats_frame,
            text="📊 Total Histórico: 0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9ca3af"
        )
        self.lbl_stat_total.pack(side="right", padx=20, pady=10)

        # 2. Barra de Filtros y Búsqueda
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.pack(fill="x", padx=15, pady=(0, 10))

        lbl_filtro = ctk.CTkLabel(filter_bar, text="Filtrar por Estado:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_filtro.pack(side="left", padx=(0, 10))

        self.seg_filter = ctk.CTkSegmentedButton(
            filter_bar,
            values=["Todos", "Pendiente", "En preparación", "Enviado", "Cancelado"],
            command=self._on_filter_changed,
            selected_color="#6366f1",
            selected_hover_color="#4f46e5"
        )
        self.seg_filter.set("Todos")
        self.seg_filter.pack(side="left", padx=(0, 15))

        self.entry_search = ctk.CTkEntry(
            filter_bar,
            placeholder_text="🔍 Buscar cliente, producto o dirección...",
            width=260
        )
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self.refresh_orders())

        btn_refresh = ctk.CTkButton(
            filter_bar,
            text="🔄 Actualizar",
            width=100,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.refresh_orders
        )
        btn_refresh.pack(side="right")

        # 3. Lista de Pedidos con Scroll
        self.scroll_orders = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_orders.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    def _on_filter_changed(self, value: str):
        self.current_filter = value
        self.refresh_orders()

    def refresh_orders(self):
        # Limpiar contenedor
        for widget in self.scroll_orders.winfo_children():
            widget.destroy()

        all_orders = database.get_all_orders()
        
        # Calcular contadores
        c_pend = sum(1 for o in all_orders if o["estado"] == "Pendiente")
        c_prep = sum(1 for o in all_orders if o["estado"] == "En preparación")
        c_sent = sum(1 for o in all_orders if o["estado"] in ("Enviado", "Despachado"))
        
        self.lbl_stat_pending.configure(text=f"⏳ Pendientes: {c_pend}")
        self.lbl_stat_prep.configure(text=f"👨‍🍳 En Preparación: {c_prep}")
        self.lbl_stat_sent.configure(text=f"🚀 Enviados: {c_sent}")
        self.lbl_stat_total.configure(text=f"📊 Total: {len(all_orders)}")

        # Filtrar por estado
        filtered = all_orders
        if self.current_filter != "Todos":
            filtered = [o for o in filtered if o["estado"] == self.current_filter]

        # Filtrar por búsqueda
        query = self.entry_search.get().strip().lower()
        if query:
            filtered = [
                o for o in filtered
                if query in str(o["id_cliente"]).lower()
                or query in str(o["resumen_pedido"]).lower()
                or query in str(o["direccion"]).lower()
                or query in str(o["metodo_pago"]).lower()
            ]

        if not filtered:
            lbl_empty = ctk.CTkLabel(
                self.scroll_orders,
                text="No hay pedidos para mostrar en esta vista.",
                font=ctk.CTkFont(size=14),
                text_color="#6b7280"
            )
            lbl_empty.pack(pady=40)
            return

        for order in filtered:
            self._render_order_card(order)

    def _render_order_card(self, order: dict):
        card = ctk.CTkFrame(self.scroll_orders, fg_color=("#222734", "#1a1e29"), corner_radius=12)
        card.pack(fill="x", pady=6, padx=2)

        # Header de la Card
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=15, pady=(12, 6))

        lbl_id = ctk.CTkLabel(
            top_row,
            text=f"Pedido #{order['id']} • 👤 {order['id_cliente']}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        lbl_id.pack(side="left")

        lbl_date = ctk.CTkLabel(
            top_row,
            text=f"🕒 {order.get('fecha_hora', '')}",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        lbl_date.pack(side="left", padx=15)

        # Badge de Estado
        st = order.get("estado", "Pendiente")
        badge_bg = STATUS_COLORS.get(st, ("#374151", "#4b5563"))[1]
        lbl_status = ctk.CTkLabel(
            top_row,
            text=f"  {st.upper()}  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=badge_bg,
            corner_radius=6,
            text_color="#ffffff"
        )
        lbl_status.pack(side="right")

        # Cuerpo del Pedido
        body_frame = ctk.CTkFrame(card, fg_color=("#1a1e29", "#13161f"), corner_radius=8)
        body_frame.pack(fill="x", padx=15, pady=6)

        # Productos
        resumen = order.get("resumen_pedido", "")
        notas = order.get("notas_especiales", "")
        prod_text = f"🍔 {resumen}"
        if notas:
            prod_text += f"\n   📝 Notas: {notas}"
        lbl_prod = ctk.CTkLabel(
            body_frame,
            text=prod_text,
            font=ctk.CTkFont(size=13),
            text_color="#f3f4f6",
            justify="left",
            wraplength=700
        )
        lbl_prod.pack(anchor="w", padx=12, pady=(8, 4))

        # Dirección y Pago
        info_row = ctk.CTkFrame(body_frame, fg_color="transparent")
        info_row.pack(fill="x", padx=12, pady=(0, 8))

        lbl_dir = ctk.CTkLabel(
            info_row,
            text=f"📍 {order.get('direccion', '')}",
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )
        lbl_dir.pack(side="left", padx=(0, 20))

        pago_info = f"💳 {order.get('metodo_pago', '')} ({order.get('cambio_de', '')})"
        if order.get("total", 0) > 0:
            pago_info += f" • Total: ${order.get('total', 0):,.0f}"
        lbl_pago = ctk.CTkLabel(
            info_row,
            text=pago_info,
            font=ctk.CTkFont(size=12),
            text_color="#a855f7"
        )
        lbl_pago.pack(side="left")

        # Botones de Acción
        actions_row = ctk.CTkFrame(card, fg_color="transparent")
        actions_row.pack(fill="x", padx=15, pady=(4, 12))

        oid = order["id"]

        btn_print = ctk.CTkButton(
            actions_row,
            text="🖨️ Imprimir",
            width=100,
            height=30,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=lambda o=order: self._print_order(o)
        )
        btn_print.pack(side="right", padx=(8, 0))

        if st == "Pendiente":
            btn_prep = ctk.CTkButton(
                actions_row,
                text="👨‍🍳 Enviar a Cocina",
                width=140,
                height=30,
                fg_color="#3b82f6",
                hover_color="#2563eb",
                command=lambda id_=oid: self._set_status(id_, "En preparación")
            )
            btn_prep.pack(side="left", padx=(0, 8))

            btn_send = ctk.CTkButton(
                actions_row,
                text="🚀 Marcar Enviado",
                width=130,
                height=30,
                fg_color="#10b981",
                hover_color="#059669",
                command=lambda id_=oid: self._set_status(id_, "Enviado")
            )
            btn_send.pack(side="left", padx=(0, 8))

            btn_cancel = ctk.CTkButton(
                actions_row,
                text="❌ Cancelar",
                width=90,
                height=30,
                fg_color="#ef4444",
                hover_color="#dc2626",
                command=lambda id_=oid: self._set_status(id_, "Cancelado")
            )
            btn_cancel.pack(side="left")

        elif st == "En preparación":
            btn_send = ctk.CTkButton(
                actions_row,
                text="🚀 Marcar como Enviado / Despachado",
                width=240,
                height=30,
                fg_color="#10b981",
                hover_color="#059669",
                command=lambda id_=oid: self._set_status(id_, "Enviado")
            )
            btn_send.pack(side="left", padx=(0, 8))

            btn_cancel = ctk.CTkButton(
                actions_row,
                text="❌ Cancelar",
                width=90,
                height=30,
                fg_color="#ef4444",
                hover_color="#dc2626",
                command=lambda id_=oid: self._set_status(id_, "Cancelado")
            )
            btn_cancel.pack(side="left")

        else: # Enviado o Cancelado
            btn_reopen = ctk.CTkButton(
                actions_row,
                text="↩️ Reabrir como Pendiente",
                width=170,
                height=30,
                fg_color="#374151",
                hover_color="#4b5563",
                command=lambda id_=oid: self._set_status(id_, "Pendiente")
            )
            btn_reopen.pack(side="left", padx=(0, 8))

            btn_del = ctk.CTkButton(
                actions_row,
                text="🗑️ Eliminar Registro",
                width=140,
                height=30,
                fg_color="#991b1b",
                hover_color="#7f1d1d",
                command=lambda id_=oid: self._delete_order(id_)
            )
            btn_del.pack(side="left")

    def _set_status(self, order_id: int, new_status: str):
        database.update_order_status(order_id, new_status)
        self.refresh_orders()

    def _delete_order(self, order_id: int):
        if messagebox.askyesno("Confirmar eliminación", f"¿Deseas eliminar el pedido #{order_id}?"):
            database.delete_order(order_id)
            self.refresh_orders()

    def _print_order(self, order: dict):
        if database.get_config("impresora_activa", "0") != "1":
            messagebox.showwarning("Impresora Desactivada", "La generación de recibos está desactivada en la pestaña de Configuración.")
            return
            
        try:
            from backend.impresora import imprimir_ticket_simulado
            imprimir_ticket_simulado(
                order["id"],
                order["id_cliente"],
                order["resumen_pedido"],
                order.get("notas_especiales", ""),
                order["direccion"],
                order["metodo_pago"],
                order.get("cambio_de", "N/A"),
                order.get("total", 0.0)
            )
        except Exception as e:
            messagebox.showerror("Error de Impresora", f"No se pudo generar el recibo:\n{e}")
