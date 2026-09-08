import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict, Any
import os
from PIL import Image

from gui.footer_bar import FooterBar
from gui.orders_tab import OrdersTab
from gui.menu_tab import MenuTab
from gui.payments_tab import PaymentsTab
from gui.storage_tab import StorageTab
from gui.settings_tab import SettingsTab
from gui.popup_alert import OrderAlertPopup
from backend import app as backend_app

class MainWindow(ctk.CTk):
    def __init__(self, port: int = 8000):
        super().__init__()
        self.port = port

        # Configuración de apariencia
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("TESO - Sistema de Pedidos")
        self.geometry("1120x740")
        self.minsize(980, 640)
        self.configure(fg_color="#131314") # Dark background based on reference

        self.active_popup: Optional[OrderAlertPopup] = None
        self.frames = {}

        self._build_ui()
        self._setup_backend_listener()
        self._start_periodic_updater()

    def _build_ui(self):
        # Configurar layout de grid (2 filas, 2 columnas)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # Set Window Icon
        icon_path = os.path.join(os.path.dirname(__file__), "..", "tesoiconoapp.png")
        if os.path.exists(icon_path):
            try:
                # CustomTkinter iconphoto support
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(False, img)
            except Exception:
                pass

        # 1. Sidebar (Izquierda)
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1A1B1E")
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        # Cargar imágenes de nav activa
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
        def load_nav_img(name):
            try:
                img_path = os.path.join(assets_dir, name)
                img = Image.open(img_path)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(180, 40))
            except:
                return None
        self.nav_imgs = {
            "orders": load_nav_img("nav_orders_active.png"),
            "menu": load_nav_img("nav_menu_active.png"),
            "payments": load_nav_img("nav_payments_active.png"),
            "storage": load_nav_img("nav_storage_active.png"),
            "settings": load_nav_img("nav_settings_active.png")
        }

        # Logo / Titulo
        if os.path.exists(icon_path):
            img = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(50, 50))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="", image=img)
            self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
            
            self.title_label = ctk.CTkLabel(self.sidebar_frame, text="TESO", font=ctk.CTkFont(size=22, weight="bold"))
            self.title_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        else:
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TESO", font=ctk.CTkFont(size=24, weight="bold"))
            self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))

        # Botones de navegación de la Sidebar
        self.btn_orders = self._create_nav_button("📋 Dashboard", self.show_orders_tab, row=2, key="orders")
        self.btn_menu = self._create_nav_button("🍔 Menú", self.show_menu_tab, row=3, key="menu")
        self.btn_payments = self._create_nav_button("💳 Pagos", self.show_payments_tab, row=4, key="payments")
        self.btn_storage = self._create_nav_button("💾 Datos", self.show_storage_tab, row=5, key="storage")
        self.btn_settings = self._create_nav_button("⚙️ Configuración", self.show_settings_tab, row=6, key="settings")

        # Footer movido a la fila 1, que ocupe todo el ancho
        self.footer = FooterBar(self, port=self.port)
        self.footer.grid(row=1, column=0, columnspan=2, sticky="ew")

        # 2. Área de Contenido Principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#131314")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Inicializar Pestañas (Frames)
        self.frames["orders"] = OrdersTab(self.main_frame)
        self.frames["menu"] = MenuTab(self.main_frame)
        self.frames["payments"] = PaymentsTab(self.main_frame)
        self.frames["storage"] = StorageTab(self.main_frame)
        self.frames["settings"] = SettingsTab(self.main_frame)

        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        # Seleccionar por defecto
        self.show_orders_tab()

    def _create_nav_button(self, text, command, row, key):
        btn = ctk.CTkButton(
            self.sidebar_frame, 
            text=text, 
            fg_color="transparent", 
            text_color="#A0A0A0",
            hover_color="#1E1F20", 
            anchor="w", 
            corner_radius=20,
            command=command,
            font=ctk.CTkFont(size=14),
            width=180,
            height=40
        )
        btn.grid(row=row, column=0, padx=20, pady=5)
        # Store metadata for active/inactive toggling
        btn.nav_key = key
        btn.orig_text = text
        return btn

    def _reset_nav_buttons(self):
        for btn in [self.btn_orders, self.btn_menu, self.btn_payments, self.btn_storage, self.btn_settings]:
            btn.configure(fg_color="transparent", text=btn.orig_text, image="")

    def _set_active_nav_button(self, button):
        self._reset_nav_buttons()
        # Active color is the brand gradient image
        img = self.nav_imgs.get(button.nav_key)
        if img:
            button.configure(text="", image=img, fg_color="transparent")
        else:
            button.configure(fg_color="#374151", text_color="#E3E3E3")

    def show_orders_tab(self):
        self.frames["orders"].tkraise()
        self._set_active_nav_button(self.btn_orders)

    def show_menu_tab(self):
        self.frames["menu"].tkraise()
        self._set_active_nav_button(self.btn_menu)

    def show_payments_tab(self):
        self.frames["payments"].tkraise()
        self._set_active_nav_button(self.btn_payments)

    def show_storage_tab(self):
        self.frames["storage"].tkraise()
        self._set_active_nav_button(self.btn_storage)

    def show_settings_tab(self):
        self.frames["settings"].tkraise()
        self._set_active_nav_button(self.btn_settings)

    def _setup_backend_listener(self):
        backend_app.register_ui_callback(self._on_backend_event)

    def _on_backend_event(self, event_type: str, data: Any):
        self.after(0, lambda: self._handle_event_in_main_thread(event_type, data))

    def _handle_event_in_main_thread(self, event_type: str, data: Any):
        if event_type == "new_order":
            if self.active_popup is None or not self.active_popup.winfo_exists():
                self.active_popup = OrderAlertPopup(
                    self,
                    order_data=data,
                    on_action=self.frames["orders"].refresh_orders
                )
            self.frames["orders"].refresh_orders()
            self.frames["storage"].refresh_stats()

        elif event_type == "heartbeat":
            self.footer.update_connection_state()

        elif event_type == "orders_updated":
            self.frames["orders"].refresh_orders()
            self.frames["storage"].refresh_stats()

        elif event_type == "menu_updated":
            self.frames["menu"].refresh_menu()

        elif event_type == "payments_updated":
            self.frames["payments"].refresh_payments()

        elif event_type == "storage_updated":
            self.frames["storage"].refresh_stats()

    def _start_periodic_updater(self):
        self.footer.update_connection_state()
        self.after(1000, self._start_periodic_updater)

    def destroy(self):
        backend_app.unregister_ui_callback(self._on_backend_event)
        super().destroy()
