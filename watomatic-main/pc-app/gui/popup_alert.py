import customtkinter as ctk
from typing import Dict, Any, Optional, Callable
from backend import database

class OrderAlertPopup(ctk.CTkToplevel):
    def __init__(self, master, order_data: Dict[str, Any], on_action: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.order_data = order_data
        self.on_action = on_action
        
        self.title("🔔 ¡NUEVO PEDIDO ENTRANTE!")
        self.geometry("520x620")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        # Centrar ventana
        self.update_idletasks()
        width = 520
        height = 620
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.configure(fg_color=("#181b22", "#0f1117"))
        self._build_ui()

    def _build_ui(self):
        # Header Banner
        header = ctk.CTkFrame(self, fg_color="#ea580c", height=70, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        
        lbl_bell = ctk.CTkLabel(
            header,
            text="⚡ ¡NUEVO PEDIDO CONFIRMADO!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        lbl_bell.pack(pady=(12, 2))
        
        lbl_time = ctk.CTkLabel(
            header,
            text=f"Recibido por WhatsApp • ID #{self.order_data.get('id', 'N/A')}",
            font=ctk.CTkFont(size=12),
            text_color="#ffedd5"
        )
        lbl_time.pack(pady=(0, 8))

        # Main Card Content
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. Cliente
        self._create_field_card(
            content,
            title="👤 CLIENTE / CONTACTO",
            value=str(self.order_data.get("id_cliente", "Cliente Desconocido")),
            accent_color="#38bdf8"
        )

        # 2. Productos y Notas
        resumen = self.order_data.get("resumen_pedido", "Sin especificar")
        notas = self.order_data.get("notas_especiales", "")
        prod_val = f"{resumen}\n📝 Notas: {notas}" if notas else resumen
        self._create_field_card(
            content,
            title="🍔 PRODUCTOS ORDENADOS",
            value=prod_val,
            accent_color="#f59e0b"
        )

        # 3. Dirección de Entrega
        self._create_field_card(
            content,
            title="📍 DIRECCIÓN DE ENTREGA",
            value=str(self.order_data.get("direccion", "No especificada")),
            accent_color="#10b981"
        )

        # 4. Método de Pago y Cambio
        metodo = self.order_data.get("metodo_pago", "Efectivo")
        cambio = self.order_data.get("cambio_de", "Exacto")
        total = self.order_data.get("total", 0.0)
        
        pago_str = f"Forma de Pago: {metodo}\n💵 Detalle de Pago: {cambio}"
        if total > 0:
            pago_str += f"\n💰 Total Estimado: ${total:,.0f}"

        self._create_field_card(
            content,
            title="💳 PAGO Y CAMBIO",
            value=pago_str,
            accent_color="#a855f7"
        )

        # Botones de Acción
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.pack(fill="x", padx=20, pady=(0, 20))

        btn_prepare = ctk.CTkButton(
            actions_frame,
            text="👨‍🍳 Enviar a Cocina (En preparación)",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self.action_send_to_kitchen
        )
        btn_prepare.pack(fill="x", pady=(0, 8))

        btn_dismiss = ctk.CTkButton(
            actions_frame,
            text="Aceptar y Cerrar Alerta",
            height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.destroy
        )
        btn_dismiss.pack(fill="x")

    def _create_field_card(self, parent, title: str, value: str, accent_color: str):
        card = ctk.CTkFrame(parent, fg_color=("#222734", "#1a1e29"), corner_radius=10)
        card.pack(fill="x", pady=6)

        lbl_t = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=accent_color
        )
        lbl_t.pack(anchor="w", padx=14, pady=(10, 2))

        lbl_v = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=14),
            text_color="#f3f4f6",
            justify="left",
            wraplength=440
        )
        lbl_v.pack(anchor="w", padx=14, pady=(0, 10))

    def action_send_to_kitchen(self):
        order_id = self.order_data.get("id")
        if order_id:
            database.update_order_status(order_id, "En preparación")
            if self.on_action:
                self.on_action()
        self.destroy()
