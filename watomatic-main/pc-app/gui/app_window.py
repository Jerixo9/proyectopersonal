import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict, Any

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

        self.title("Sistema Automático de Toma de Pedidos IA (Llama 3.1)")
        self.geometry("1120x740")
        self.minsize(980, 640)
        self.configure(fg_color=("#13161f", "#0c0e14"))

        self.active_popup: Optional[OrderAlertPopup] = None

        self._build_ui()
        self._setup_backend_listener()
        self._start_periodic_updater()

    def _build_ui(self):
        # 1. Header Superior
        header_frame = ctk.CTkFrame(self, height=55, corner_radius=0, fg_color=("#1a1e29", "#13161f"))
        header_frame.pack(fill="x", side="top")

        lbl_app_logo = ctk.CTkLabel(
            header_frame,
            text="🍔 SISTEMA DE PEDIDOS IA",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#ffffff"
        )
        lbl_app_logo.pack(side="left", padx=20, pady=12)

        lbl_sub = ctk.CTkLabel(
            header_frame,
            text="Llama 3.1 Local • Watomatic Android Bridge",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        lbl_sub.pack(side="left", padx=5, pady=12)

        # 2. Barra Inferior (Footer)
        self.footer = FooterBar(self, port=self.port)
        self.footer.pack(fill="x", side="bottom")

        # 3. Contenedor de Pestañas
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color=("#1a1e29", "#11141c"),
            segmented_button_selected_color="#6366f1",
            segmented_button_selected_hover_color="#4f46e5",
            segmented_button_unselected_color="#222734",
            segmented_button_unselected_hover_color="#374151"
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(5, 5))

        # Crear Pestañas
        self.tab_orders_holder = self.tabview.add("📋 Monitor de Pedidos")
        self.tab_menu_holder = self.tabview.add("🍔 Gestor de Menú")
        self.tab_payments_holder = self.tabview.add("💳 Métodos de Pago")
        self.tab_storage_holder = self.tabview.add("💾 Almacenamiento & Limpieza")
        self.tab_settings_holder = self.tabview.add("⚙️ Configuración & IA")

        # Instanciar Vistas dentro de las Pestañas
        self.orders_tab = OrdersTab(self.tab_orders_holder)
        self.orders_tab.pack(fill="both", expand=True)

        self.menu_tab = MenuTab(self.tab_menu_holder)
        self.menu_tab.pack(fill="both", expand=True)

        self.payments_tab = PaymentsTab(self.tab_payments_holder)
        self.payments_tab.pack(fill="both", expand=True)

        self.storage_tab = StorageTab(self.tab_storage_holder)
        self.storage_tab.pack(fill="both", expand=True)

        self.settings_tab = SettingsTab(self.tab_settings_holder)
        self.settings_tab.pack(fill="both", expand=True)

    def _setup_backend_listener(self):
        """Registra callback en backend_app para recibir eventos de webhook e IA en tiempo real."""
        backend_app.register_ui_callback(self._on_backend_event)

    def _on_backend_event(self, event_type: str, data: Any):
        # Programar ejecución en el hilo principal de Tkinter
        self.after(0, lambda: self._handle_event_in_main_thread(event_type, data))

    def _handle_event_in_main_thread(self, event_type: str, data: Any):
        if event_type == "new_order":
            # Disparar Pop-up de Alerta
            if self.active_popup is None or not self.active_popup.winfo_exists():
                self.active_popup = OrderAlertPopup(
                    self,
                    order_data=data,
                    on_action=self.orders_tab.refresh_orders
                )
            # Refrescar vista de pedidos y almacenamiento
            self.orders_tab.refresh_orders()
            self.storage_tab.refresh_stats()

        elif event_type == "heartbeat":
            self.footer.update_connection_state()

        elif event_type == "orders_updated":
            self.orders_tab.refresh_orders()
            self.storage_tab.refresh_stats()

        elif event_type == "menu_updated":
            self.menu_tab.refresh_menu()

        elif event_type == "payments_updated":
            self.payments_tab.refresh_payments()

        elif event_type == "storage_updated":
            self.storage_tab.refresh_stats()

    def _start_periodic_updater(self):
        """Revisa cada segundo el estado del heartbeat y la conexión del móvil."""
        self.footer.update_connection_state()
        self.after(1000, self._start_periodic_updater)

    def destroy(self):
        backend_app.unregister_ui_callback(self._on_backend_event)
        super().destroy()
