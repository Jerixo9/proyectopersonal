import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict, Any
from backend import database

class PaymentDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_save = on_save
        
        self.title("Agregar Método de Pago")
        self.geometry("400x320")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 200
        y = (self.winfo_screenheight() // 2) - 160
        self.geometry(f"400x320+{x}+{y}")
        
        self.configure(fg_color=("#1f2430", "#141721"))
        self._build_ui()

    def _build_ui(self):
        lbl_title = ctk.CTkLabel(
            self,
            text="Nuevo Método de Pago",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(pady=(20, 15))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=25)

        ctk.CTkLabel(form, text="Nombre del Método de Pago *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        self.entry_nombre = ctk.CTkEntry(form, placeholder_text="Ej: Daviplata, Dale!, Tarjeta Débito", height=35)
        self.entry_nombre.pack(fill="x", pady=(0, 15))

        self.sw_activo = ctk.CTkSwitch(form, text="Activo (Ofrecer en WhatsApp)")
        self.sw_activo.select()
        self.sw_activo.pack(anchor="w", pady=(0, 10))

        self.sw_cambio = ctk.CTkSwitch(form, text="Pide Cambio (La IA preguntará con cuánto cancela)")
        self.sw_cambio.pack(anchor="w", pady=(0, 15))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(0, 20))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="💾 Guardar Método",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self._save
        )
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            height=38,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.destroy
        )
        btn_cancel.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _save(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Campo requerido", "Ingresa el nombre del método de pago.")
            return

        activo = bool(self.sw_activo.get())
        pide_cambio = bool(self.sw_cambio.get())

        try:
            database.add_payment_method(nombre, activo=activo, pide_cambio=pide_cambio)
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el método: {e}")

class PaymentsTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._build_ui()
        self.refresh_payments()

    def _build_ui(self):
        # Barra Superior
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(15, 10))

        btn_add = ctk.CTkButton(
            top_bar,
            text="➕ Agregar Método de Pago",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self._open_add_dialog
        )
        btn_add.pack(side="left")

        lbl_hint = ctk.CTkLabel(
            top_bar,
            text="ℹ️ La IA solo ofrecerá a los clientes las opciones que tengan el switch 'Activo' encendido.",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        lbl_hint.pack(side="left", padx=15)

        btn_refresh = ctk.CTkButton(
            top_bar,
            text="🔄 Actualizar",
            width=100,
            height=36,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.refresh_payments
        )
        btn_refresh.pack(side="right")

        # Lista de Métodos de Pago
        self.scroll_payments = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_payments.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    def refresh_payments(self):
        for widget in self.scroll_payments.winfo_children():
            widget.destroy()

        payments = database.get_all_payment_methods()
        if not payments:
            lbl_empty = ctk.CTkLabel(
                self.scroll_payments,
                text="No hay métodos de pago registrados.",
                font=ctk.CTkFont(size=14),
                text_color="#6b7280"
            )
            lbl_empty.pack(pady=40)
            return

        for p in payments:
            self._render_payment_card(p)

    def _render_payment_card(self, payment: dict):
        card = ctk.CTkFrame(self.scroll_payments, fg_color=("#222734", "#1a1e29"), corner_radius=10)
        card.pack(fill="x", pady=6, padx=2)

        main_row = ctk.CTkFrame(card, fg_color="transparent")
        main_row.pack(fill="x", padx=15, pady=12)

        # Nombre y descripción
        col_left = ctk.CTkFrame(main_row, fg_color="transparent")
        col_left.pack(side="left", fill="both", expand=True)

        lbl_name = ctk.CTkLabel(
            col_left,
            text=f"💳 {payment['nombre']}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        lbl_name.pack(anchor="w")

        pide_cambio_str = "Pregunta con cuánto cancela (Para cambio)" if payment.get("pide_cambio") else "Pago exacto / transferencia (No pregunta por cambio)"
        lbl_sub = ctk.CTkLabel(
            col_left,
            text=f"⚙️ Modo: {pide_cambio_str}",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Switches de Control
        col_right = ctk.CTkFrame(main_row, fg_color="transparent")
        col_right.pack(side="right")

        pid = payment["id"]
        is_active = bool(payment.get("activo", 1))
        is_change = bool(payment.get("pide_cambio", 0))

        sw_change = ctk.CTkSwitch(
            col_right,
            text="Pide Cambio",
            command=lambda i=pid: self._toggle_change(i),
            progress_color="#f59e0b"
        )
        if is_change:
            sw_change.select()
        else:
            sw_change.deselect()
        sw_change.pack(side="left", padx=(0, 15))

        sw_active = ctk.CTkSwitch(
            col_right,
            text="Activo" if is_active else "Inactivo",
            command=lambda i=pid: self._toggle_active(i),
            progress_color="#10b981"
        )
        if is_active:
            sw_active.select()
        else:
            sw_active.deselect()
        sw_active.pack(side="left", padx=(0, 15))

        # Permitir eliminar métodos si no son predeterminados principales o con confirmación
        btn_del = ctk.CTkButton(
            col_right,
            text="🗑️",
            width=32,
            height=30,
            fg_color="#991b1b",
            hover_color="#7f1d1d",
            command=lambda i=pid, n=payment["nombre"]: self._delete_payment(i, n)
        )
        btn_del.pack(side="left")

    def _toggle_active(self, method_id: int):
        database.toggle_payment_active(method_id)
        self.refresh_payments()

    def _toggle_change(self, method_id: int):
        database.toggle_payment_pide_cambio(method_id)
        self.refresh_payments()

    def _open_add_dialog(self):
        PaymentDialog(self, on_save=self.refresh_payments)

    def _delete_payment(self, method_id: int, name: str):
        if messagebox.askyesno("Confirmar eliminación", f"¿Deseas eliminar el método '{name}'?"):
            database.delete_payment_method(method_id)
            self.refresh_payments()
