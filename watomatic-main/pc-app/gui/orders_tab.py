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

import os
from PIL import Image

class OrdersTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="#131314", **kwargs)
        self.current_filter = "Todos"
        
        # Cargar imagenes de gradiente específicas
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        try:
            def load_img(name, w, h):
                img_path = os.path.join(assets_dir, name)
                img = Image.open(img_path)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))

            self.img_print = load_img("btn_print.png", 100, 32)
            self.img_prep = load_img("btn_prep.png", 140, 32)
            self.img_send = load_img("btn_send.png", 130, 32)
            self.img_cancel = load_img("btn_cancel.png", 90, 32)
            self.img_send_long = load_img("btn_send_long.png", 240, 32)
            self.img_reopen = load_img("btn_reopen.png", 170, 32)
            self.img_delete = load_img("btn_delete.png", 140, 32)
            self.img_primary_prep = load_img("btn_primary_prep.png", 360, 40)
            self.img_primary_send = load_img("btn_primary_send.png", 360, 40)
        except Exception as e:
            print("Error cargando gradientes específicos:", e)
            self.img_print = self.img_prep = self.img_send = self.img_cancel = self.img_send_long = self.img_reopen = self.img_delete = self.img_primary_prep = self.img_primary_send = None
            
        self._build_ui()
        self.refresh_orders()

    def _build_ui(self):
        # 1. Barra de Estadísticas y Contadores Rápidos
        self.stats_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=24)
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
        filter_bar = ctk.CTkFrame(self, fg_color="#222428", corner_radius=12)
        filter_bar.pack(fill="x", padx=15, pady=(0, 10))

        lbl_filter = ctk.CTkLabel(filter_bar, text="Filtrar por Estado:", font=ctk.CTkFont(weight="bold"))
        lbl_filter.pack(side="left", padx=(15, 10), pady=10)

        self.seg_filter = ctk.CTkSegmentedButton(
            filter_bar,
            values=["Todos", "Pendiente", "En preparación", "Enviado", "Cancelado"],
            command=self._on_filter_changed,
            selected_color="#374151",
            selected_hover_color="#4b5563"
        )
        self.seg_filter.set("Todos")
        self.seg_filter.pack(side="left")

        # Búsqueda
        self.entry_search = ctk.CTkEntry(
            filter_bar,
            placeholder_text="🔍 Buscar...",
            width=260,
            corner_radius=100,
            fg_color="#1E1F20",
            border_width=0
        )
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self.refresh_orders())

        btn_refresh = ctk.CTkButton(
            filter_bar,
            text="🔄 Actualizar",
            width=100,
            fg_color="#374151",
            hover_color="#4b5563",
            corner_radius=100,
            command=self.refresh_orders
        )
        btn_refresh.pack(side="right")

        # 3. Lista de Pedidos con Scroll
        self.scroll_orders = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_orders.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        # Configurar 2 columnas
        self.scroll_orders.grid_columnconfigure((0, 1), weight=1)

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

        for index, order in enumerate(filtered):
            self._render_order_card(order, index)

    def _render_order_card(self, order: dict, index: int):
        card = ctk.CTkFrame(self.scroll_orders, fg_color="#222428", corner_radius=24, border_width=1, border_color="#333333")
        card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=10, pady=10)

        # Header de la Card
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=(20, 10))

        lbl_id = ctk.CTkLabel(
            top_row,
            text=f"💬 {order['id_cliente']}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#E3E3E3"
        )
        lbl_id.pack(side="left")

        lbl_date = ctk.CTkLabel(
            top_row,
            text=f"{order.get('fecha_hora', '')}",
            font=ctk.CTkFont(size=11),
            text_color="#A0A0A0"
        )
        lbl_date.pack(side="right")

        # Cuerpo del Pedido
        body_frame = ctk.CTkFrame(card, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=20, pady=0)

        lbl_order_id = ctk.CTkLabel(
            body_frame,
            text=f"Pedido #{order['id']}",
            font=ctk.CTkFont(size=12),
            text_color="#A0A0A0",
            anchor="w"
        )
        lbl_order_id.pack(fill="x")

        # Productos
        resumen = order.get("resumen_pedido", "")
        notas = order.get("notas_especiales", "")
        prod_text = resumen
        if notas:
            prod_text += f"\nNotas: {notas}"
        lbl_prod = ctk.CTkLabel(
            body_frame,
            text=prod_text,
            font=ctk.CTkFont(size=14),
            text_color="#E3E3E3",
            justify="left",
            wraplength=350
        )
        lbl_prod.pack(anchor="w", pady=(10, 10))

        # Badge de Estado Píldora
        st = order.get("estado", "Pendiente")
        badge_bg = STATUS_COLORS.get(st, ("#374151", "#4b5563"))[1]
        lbl_status = ctk.CTkLabel(
            body_frame,
            text=f"  {st.upper()}  ",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=badge_bg,
            corner_radius=12,
            text_color="#ffffff"
        )
        lbl_status.pack(anchor="w", pady=(0, 10))

        # Dirección y Pago en texto secundario
        info_row = ctk.CTkFrame(body_frame, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 10))

        pago_info = f"{order.get('metodo_pago', '')}"
        if order.get("total", 0) > 0:
            pago_info += f" • ${order.get('total', 0):,.0f}"
        
        lbl_info = ctk.CTkLabel(
            info_row,
            text=f"📍 {order.get('direccion', '')}   💳 {pago_info}",
            font=ctk.CTkFont(size=12),
            text_color="#A0A0A0"
        )
        lbl_info.pack(side="left")

        # Botones de Acción
        actions_row = ctk.CTkFrame(card, fg_color="transparent")
        actions_row.pack(fill="x", padx=20, pady=(10, 20))

        oid = order["id"]

        if st == "Pendiente":
            btn_prep = ctk.CTkButton(
                actions_row,
                text="",
                width=360,
                height=40,
                corner_radius=20,
                fg_color="transparent",
                image=self.img_primary_prep,
                hover_color="#1E1F20",
                command=lambda id_=oid: self._set_status(id_, "En preparación")
            )
            btn_prep.pack(fill="x", pady=(0, 10))

            # Fila secundaria
            sec_row = ctk.CTkFrame(actions_row, fg_color="transparent")
            sec_row.pack(fill="x")

            btn_cancel = ctk.CTkButton(
                sec_row,
                text="Rechazar",
                fg_color="transparent",
                border_width=1,
                border_color="#ef4444",
                text_color="#ef4444",
                hover_color="#451a1a",
                corner_radius=20,
                command=lambda id_=oid: self._set_status(id_, "Cancelado")
            )
            btn_cancel.pack(side="left", expand=True, padx=(0, 5))

            btn_print = ctk.CTkButton(
                sec_row,
                text="Imprimir",
                fg_color="transparent",
                border_width=1,
                border_color="#C490E4",
                text_color="#C490E4",
                hover_color="#3b2046",
                corner_radius=20,
                command=lambda o=order: self._print_order(o)
            )
            btn_print.pack(side="right", expand=True, padx=(5, 0))

        elif st == "En preparación":
            btn_send = ctk.CTkButton(
                actions_row,
                text="",
                width=360,
                height=40,
                corner_radius=20,
                fg_color="transparent",
                image=self.img_primary_send,
                hover_color="#1E1F20",
                command=lambda id_=oid: self._set_status(id_, "Enviado")
            )
            btn_send.pack(fill="x", pady=(0, 10))

            btn_print = ctk.CTkButton(
                actions_row,
                text="Imprimir",
                fg_color="transparent",
                border_width=1,
                border_color="#C490E4",
                text_color="#C490E4",
                hover_color="#3b2046",
                corner_radius=20,
                command=lambda o=order: self._print_order(o)
            )
            btn_print.pack(fill="x")

        else: # Enviado o Cancelado
            btn_reopen = ctk.CTkButton(
                actions_row,
                text="Reabrir como Pendiente",
                fg_color="transparent",
                border_width=1,
                border_color="#A0A0A0",
                text_color="#E3E3E3",
                hover_color="#374151",
                corner_radius=20,
                command=lambda id_=oid: self._set_status(id_, "Pendiente")
            )
            btn_reopen.pack(fill="x", pady=(0, 10))

            btn_del = ctk.CTkButton(
                actions_row,
                text="Eliminar Registro",
                fg_color="transparent",
                border_width=1,
                border_color="#ef4444",
                text_color="#ef4444",
                hover_color="#451a1a",
                corner_radius=20,
                command=lambda id_=oid: self._delete_order(id_)
            )
            btn_del.pack(fill="x")

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
