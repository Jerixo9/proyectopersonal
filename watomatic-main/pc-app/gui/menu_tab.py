import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Dict, Any, List
from backend import database

class CategoryManagerDialog(ctk.CTkToplevel):
    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change = on_change
        
        self.title("Gestor de Categorías del Menú")
        self.geometry("480x520")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 240
        y = (self.winfo_screenheight() // 2) - 260
        self.geometry(f"480x520+{x}+{y}")
        
        self.configure(fg_color=("#1f2430", "#141721"))
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        lbl_title = ctk.CTkLabel(
            self,
            text="🏷️ Gestor de Categorías",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(pady=(18, 10))

        # Sección para agregar nueva categoría
        add_frame = ctk.CTkFrame(self, fg_color=("#222734", "#1a1e29"), corner_radius=10)
        add_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(add_frame, text="Nueva Categoría:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        row_input = ctk.CTkFrame(add_frame, fg_color="transparent")
        row_input.pack(fill="x", padx=12, pady=(0, 10))

        self.entry_new_cat = ctk.CTkEntry(row_input, placeholder_text="Ej: Postres, Combos...", height=35)
        self.entry_new_cat.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_add_cat = ctk.CTkButton(
            row_input,
            text="➕ Crear",
            width=80,
            height=35,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(weight="bold"),
            command=self._add_category
        )
        btn_add_cat.pack(side="right")

        # Lista Scrollable de Categorías
        ctk.CTkLabel(self, text="Categorías Registradas:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=22, pady=(5, 4))
        self.scroll_cats = ctk.CTkScrollableFrame(self, fg_color="transparent", height=260)
        self.scroll_cats.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        btn_close = ctk.CTkButton(
            self,
            text="Cerrar",
            height=38,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.destroy
        )
        btn_close.pack(fill="x", padx=20, pady=(0, 18))

    def _refresh_list(self):
        for w in self.scroll_cats.winfo_children():
            w.destroy()

        cats = database.get_all_categories()
        for cat in cats:
            row = ctk.CTkFrame(self.scroll_cats, fg_color=("#222734", "#1a1e29"), corner_radius=8)
            row.pack(fill="x", pady=3, padx=2)

            lbl_cat_name = ctk.CTkLabel(
                row,
                text=cat["nombre"],
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ffffff"
            )
            lbl_cat_name.pack(side="left", padx=12, pady=8)

            is_general = cat["nombre"].lower() == "general"

            btn_del = ctk.CTkButton(
                row,
                text="🗑️",
                width=30,
                height=28,
                fg_color="#991b1b" if not is_general else "#374151",
                hover_color="#7f1d1d" if not is_general else "#374151",
                state="normal" if not is_general else "disabled",
                command=lambda c_id=cat["id"], c_name=cat["nombre"]: self._delete_category(c_id, c_name)
            )
            btn_del.pack(side="right", padx=(4, 10), pady=6)

            btn_edit = ctk.CTkButton(
                row,
                text="✏️",
                width=30,
                height=28,
                fg_color="#374151",
                hover_color="#4b5563",
                command=lambda c_id=cat["id"], c_name=cat["nombre"]: self._edit_category(c_id, c_name)
            )
            btn_edit.pack(side="right", padx=(0, 4), pady=6)

    def _add_category(self):
        name = self.entry_new_cat.get().strip()
        if not name:
            return
        database.add_category(name)
        self.entry_new_cat.delete(0, "end")
        self._refresh_list()
        if self.on_change:
            self.on_change()

    def _edit_category(self, cat_id: int, current_name: str):
        dialog = ctk.CTkInputDialog(text=f"Nuevo nombre para la categoría '{current_name}':", title="Editar Categoría")
        new_name = dialog.get_input()
        if new_name and new_name.strip() and new_name.strip() != current_name:
            database.update_category(cat_id, new_name.strip())
            self._refresh_list()
            if self.on_change:
                self.on_change()

    def _delete_category(self, cat_id: int, cat_name: str):
        if messagebox.askyesno("Eliminar Categoría", f"¿Deseas eliminar la categoría '{cat_name}'?\nLos platos asociados pasarán automáticamente a la categoría 'General'."):
            database.delete_category(cat_id)
            self._refresh_list()
            if self.on_change:
                self.on_change()

class MenuItemDialog(ctk.CTkToplevel):
    def __init__(self, master, item_data: Optional[Dict[str, Any]] = None, on_save=None, **kwargs):
        super().__init__(master, **kwargs)
        self.item_data = item_data
        self.on_save = on_save
        
        is_edit = item_data is not None
        self.title("Editar Plato" if is_edit else "Agregar Nuevo Plato")
        self.geometry("450x490")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 225
        y = (self.winfo_screenheight() // 2) - 245
        self.geometry(f"450x490+{x}+{y}")
        
        self.configure(fg_color=("#1f2430", "#141721"))
        self._build_ui()

    def _build_ui(self):
        lbl_title = ctk.CTkLabel(
            self,
            text="Editar Plato del Menú" if self.item_data else "Agregar Nuevo Plato al Menú",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(pady=(20, 15))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=25)

        # Nombre
        ctk.CTkLabel(form, text="Nombre del Plato *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        self.entry_nombre = ctk.CTkEntry(form, placeholder_text="Ej: Hamburguesa Especial", height=35)
        self.entry_nombre.pack(fill="x", pady=(0, 10))
        if self.item_data:
            self.entry_nombre.insert(0, self.item_data.get("nombre", ""))

        # Precio y Categoría en fila
        row_pc = ctk.CTkFrame(form, fg_color="transparent")
        row_pc.pack(fill="x", pady=(0, 10))

        col_p = ctk.CTkFrame(row_pc, fg_color="transparent")
        col_p.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(col_p, text="Precio ($) *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        self.entry_precio = ctk.CTkEntry(col_p, placeholder_text="18000", height=35)
        self.entry_precio.pack(fill="x")
        if self.item_data:
            self.entry_precio.insert(0, str(int(self.item_data.get("precio", 0))))

        col_c = ctk.CTkFrame(row_pc, fg_color="transparent")
        col_c.pack(side="right", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(col_c, text="Categoría", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        
        # Cargar categorías dinámicas de la BD
        db_cats = database.get_all_categories()
        cat_names = [c["nombre"] for c in db_cats] if db_cats else ["Hamburguesas", "Comidas Rápidas", "Acompañamientos", "Bebidas", "Postres", "General"]

        self.combo_cat = ctk.CTkComboBox(
            col_c,
            values=cat_names,
            height=35
        )
        self.combo_cat.pack(fill="x")
        if self.item_data:
            self.combo_cat.set(self.item_data.get("categoria", "General"))
        else:
            self.combo_cat.set(cat_names[0] if cat_names else "General")

        # Ingredientes / Descripción
        ctk.CTkLabel(form, text="Ingredientes / Descripción", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(0, 2))
        self.txt_ingredientes = ctk.CTkTextbox(form, height=80)
        self.txt_ingredientes.pack(fill="x", pady=(0, 12))
        if self.item_data and self.item_data.get("ingredientes"):
            self.txt_ingredientes.insert("1.0", self.item_data.get("ingredientes"))

        # Switch Disponible
        self.sw_disponible = ctk.CTkSwitch(form, text="Disponible para la venta (La IA lo ofrecerá)")
        self.sw_disponible.pack(anchor="w", pady=(0, 15))
        if self.item_data:
            if self.item_data.get("disponible", 1):
                self.sw_disponible.select()
            else:
                self.sw_disponible.deselect()
        else:
            self.sw_disponible.select()

        # Botones
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(0, 20))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="💾 Guardar Plato",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self._save
        )
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            height=40,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.destroy
        )
        btn_cancel.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _save(self):
        nombre = self.entry_nombre.get().strip()
        precio_str = self.entry_precio.get().strip()
        ingredientes = self.txt_ingredientes.get("1.0", "end-1c").strip()
        categoria = self.combo_cat.get()
        disponible = bool(self.sw_disponible.get())

        if not nombre:
            messagebox.showwarning("Campo requerido", "Por favor ingresa el nombre del plato.")
            return

        try:
            precio = float(precio_str)
        except ValueError:
            messagebox.showwarning("Precio inválido", "Ingresa un valor numérico para el precio.")
            return

        if self.item_data:
            database.update_menu_item(
                item_id=self.item_data["id"],
                nombre=nombre,
                precio=precio,
                ingredientes=ingredientes,
                categoria=categoria,
                disponible=disponible
            )
        else:
            database.add_menu_item(
                nombre=nombre,
                precio=precio,
                ingredientes=ingredientes,
                categoria=categoria,
                disponible=disponible
            )

        if self.on_save:
            self.on_save()
        self.destroy()

class MenuTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._build_ui()
        self.refresh_menu()

    def _build_ui(self):
        # Barra Superior de Control
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(15, 10))

        btn_add = ctk.CTkButton(
            top_bar,
            text="➕ Agregar Nuevo Plato",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._open_add_dialog
        )
        btn_add.pack(side="left", padx=(0, 10))

        btn_cats = ctk.CTkButton(
            top_bar,
            text="🏷️ Categorías",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self._open_category_manager
        )
        btn_cats.pack(side="left")

        lbl_info = ctk.CTkLabel(
            top_bar,
            text="ℹ️ Los platos marcados como 'Agotado' no serán ofrecidos por la IA.",
            font=ctk.CTkFont(size=12),
            text_color="#9ca3af"
        )
        lbl_info.pack(side="left", padx=15)

        btn_refresh = ctk.CTkButton(
            top_bar,
            text="🔄 Actualizar",
            width=100,
            height=36,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.refresh_menu
        )
        btn_refresh.pack(side="right")

        # Lista de Platos con Scroll
        self.scroll_menu = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_menu.pack(fill="both", expand=True, padx=15, pady=(0, 10))

    def refresh_menu(self):
        for widget in self.scroll_menu.winfo_children():
            widget.destroy()

        items = database.get_all_menu()
        if not items:
            lbl_empty = ctk.CTkLabel(
                self.scroll_menu,
                text="No hay platos en el menú. Agrega el primero con el botón superior.",
                font=ctk.CTkFont(size=14),
                text_color="#6b7280"
            )
            lbl_empty.pack(pady=40)
            return

        # Agrupar por Categoría
        categories = {}
        for item in items:
            cat = item.get("categoria", "General")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        for cat, cat_items in categories.items():
            # Encabezado de Categoría
            cat_header = ctk.CTkLabel(
                self.scroll_menu,
                text=f"📂 {cat.upper()} ({len(cat_items)})",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#38bdf8"
            )
            cat_header.pack(anchor="w", pady=(12, 4), padx=4)

            for item in cat_items:
                self._render_menu_row(item)

    def _render_menu_row(self, item: dict):
        card = ctk.CTkFrame(self.scroll_menu, fg_color=("#222734", "#1a1e29"), corner_radius=10)
        card.pack(fill="x", pady=4, padx=2)

        # Fila principal
        main_row = ctk.CTkFrame(card, fg_color="transparent")
        main_row.pack(fill="x", padx=15, pady=10)

        # Columna Izquierda: Nombre, Precio e Ingredientes
        info_col = ctk.CTkFrame(main_row, fg_color="transparent")
        info_col.pack(side="left", fill="both", expand=True)

        title_row = ctk.CTkFrame(info_col, fg_color="transparent")
        title_row.pack(fill="x")

        lbl_name = ctk.CTkLabel(
            title_row,
            text=item["nombre"],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        )
        lbl_name.pack(side="left")

        lbl_price = ctk.CTkLabel(
            title_row,
            text=f"${item['precio']:,.0f}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#10b981"
        )
        lbl_price.pack(side="left", padx=15)

        if item.get("ingredientes"):
            lbl_ing = ctk.CTkLabel(
                info_col,
                text=item["ingredientes"],
                font=ctk.CTkFont(size=12),
                text_color="#9ca3af",
                wraplength=550,
                justify="left"
            )
            lbl_ing.pack(anchor="w", pady=(2, 0))

        # Columna Derecha: Switch Disponible y Botones
        actions_col = ctk.CTkFrame(main_row, fg_color="transparent")
        actions_col.pack(side="right", padx=(10, 0))

        is_avail = bool(item.get("disponible", 1))
        
        sw_avail = ctk.CTkSwitch(
            actions_col,
            text="Disponible" if is_avail else "Agotado",
            command=lambda i=item["id"]: self._toggle_avail(i),
            progress_color="#10b981"
        )
        if is_avail:
            sw_avail.select()
        else:
            sw_avail.deselect()
        sw_avail.pack(side="left", padx=(0, 15))

        btn_edit = ctk.CTkButton(
            actions_col,
            text="✏️",
            width=32,
            height=30,
            fg_color="#374151",
            hover_color="#4b5563",
            command=lambda it=item: self._open_edit_dialog(it)
        )
        btn_edit.pack(side="left", padx=(0, 6))

        btn_del = ctk.CTkButton(
            actions_col,
            text="🗑️",
            width=32,
            height=30,
            fg_color="#991b1b",
            hover_color="#7f1d1d",
            command=lambda i=item["id"], n=item["nombre"]: self._delete_item(i, n)
        )
        btn_del.pack(side="left")

    def _toggle_avail(self, item_id: int):
        database.toggle_menu_availability(item_id)
        self.refresh_menu()

    def _open_add_dialog(self):
        MenuItemDialog(self, item_data=None, on_save=self.refresh_menu)

    def _open_edit_dialog(self, item: dict):
        MenuItemDialog(self, item_data=item, on_save=self.refresh_menu)

    def _open_category_manager(self):
        CategoryManagerDialog(self, on_change=self.refresh_menu)

    def _delete_item(self, item_id: int, item_name: str):
        if messagebox.askyesno("Confirmar eliminación", f"¿Deseas eliminar '{item_name}' del menú?"):
            database.delete_menu_item(item_id)
            self.refresh_menu()
