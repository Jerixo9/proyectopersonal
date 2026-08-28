import os
import re
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pedidos.db")

def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Retorna una conexión a la base de datos SQLite con row_factory como Row."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str = DB_FILE):
    """Crea las tablas necesarias si no existen y llena datos iniciales."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Tabla Menu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                ingredientes TEXT,
                categoria TEXT DEFAULT 'General',
                disponible BOOLEAN DEFAULT 1
            );
        """)

        # Tabla Metodos_Pago
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Metodos_Pago (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                activo BOOLEAN DEFAULT 1,
                pide_cambio BOOLEAN DEFAULT 0
            );
        """)

        # Tabla Categorias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            );
        """)

        # Tabla Mensajes_Contexto
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Mensajes_Contexto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente TEXT NOT NULL,
                rol TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tabla Carrito_Temporal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Carrito_Temporal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente TEXT NOT NULL,
                nombre_producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                precio_unitario REAL NOT NULL,
                notas TEXT DEFAULT '',
                ultima_actividad DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Migraciones: asegurar columnas notas y ultima_actividad en Carrito_Temporal si ya existía la tabla
        try:
            cursor.execute("ALTER TABLE Carrito_Temporal ADD COLUMN notas TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE Carrito_Temporal ADD COLUMN ultima_actividad DATETIME DEFAULT CURRENT_TIMESTAMP")
        except sqlite3.OperationalError:
            pass

        # Tabla Pedidos_Confirmados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Pedidos_Confirmados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente TEXT NOT NULL,
                resumen_pedido TEXT NOT NULL,
                notas_especiales TEXT,
                direccion TEXT NOT NULL,
                metodo_pago TEXT NOT NULL,
                cambio_de TEXT,
                total REAL DEFAULT 0,
                fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                estado TEXT DEFAULT 'Pendiente'
            );
        """)

        # Tabla Estado_Cliente (Memoria de checkout en SQLite)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Estado_Cliente (
                id_cliente TEXT PRIMARY KEY,
                direccion TEXT,
                metodo_pago TEXT,
                paga_con TEXT,
                estado TEXT DEFAULT 'ordenando'
            );
        """)

        # Configuración / Metadata de limpieza
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS App_Config (
                clave TEXT PRIMARY KEY,
                valor TEXT
            );
        """)

        # Sembrar Categorías predeterminadas si la tabla está vacía
        cursor.execute("SELECT COUNT(*) as count FROM Categorias")
        if cursor.fetchone()["count"] == 0:
            default_categories = [
                ("Hamburguesas",),
                ("Comidas Rápidas",),
                ("Acompañamientos",),
                ("Bebidas",),
                ("Postres",),
                ("General",)
            ]
            cursor.executemany(
                "INSERT OR IGNORE INTO Categorias (nombre) VALUES (?)",
                default_categories
            )

        # Sembrar Métodos de Pago predeterminados si la tabla está vacía
        cursor.execute("SELECT COUNT(*) as count FROM Metodos_Pago")
        if cursor.fetchone()["count"] == 0:
            default_payments = [
                ("Efectivo", 1, 1),
                ("Nequi", 1, 0),
                ("Transferencia Bancaria", 1, 0),
                ("Datáfono", 1, 0)
            ]
            cursor.executemany(
                "INSERT INTO Metodos_Pago (nombre, activo, pide_cambio) VALUES (?, ?, ?)",
                default_payments
            )

        # Sembrar Menú de muestra si está vacío
        cursor.execute("SELECT COUNT(*) as count FROM Menu")
        if cursor.fetchone()["count"] == 0:
            default_menu = [
                ("Hamburguesa Clásica", 18000, "Carne 150g, queso americano, lechuga, tomate, salsa de la casa", "Hamburguesas", 1),
                ("Hamburguesa Doble Carne", 24000, "Doble carne 300g, doble queso, tocineta, cebolla caramelizada", "Hamburguesas", 1),
                ("Perro Caliente Especial", 14000, "Salchicha premium, tocineta, queso gratinado, papitas crocantes", "Comidas Rápidas", 1),
                ("Pizza de peperonni", 22000, "Masa artesanal, salsa napolitana, queso mozzarella y pepperoni", "Comidas Rápidas", 1),
                ("Papas Francesas Grandes", 9000, "Papas crujientes con sal marina y salsa tártara", "Acompañamientos", 1),
                ("Gaseosa 400ml", 5000, "Coca-Cola, Sprite o Cuatro", "Bebidas", 1),
                ("Jugo Natural en Agua", 6000, "Fresa, Maracuyá o Mango", "Bebidas", 1)
            ]
            cursor.executemany(
                "INSERT INTO Menu (nombre, precio, ingredientes, categoria, disponible) VALUES (?, ?, ?, ?, ?)",
                default_menu
            )

        conn.commit()

# ==================== OPERACIONES DE CATEGORÍAS ====================

def get_all_categories(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retorna todas las categorías registradas."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Categorias ORDER BY CASE WHEN nombre = 'General' THEN 1 ELSE 0 END, nombre ASC")
        return [dict(row) for row in cursor.fetchall()]

def add_category(nombre: str, db_path: str = DB_FILE) -> int:
    """Crea una nueva categoría si no existe."""
    clean_name = nombre.strip()
    if not clean_name:
        return 0
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO Categorias (nombre) VALUES (?)",
            (clean_name,)
        )
        conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        cursor.execute("SELECT id FROM Categorias WHERE nombre = ?", (clean_name,))
        row = cursor.fetchone()
        return row["id"] if row else 0

def update_category(categoria_id: int, nuevo_nombre: str, db_path: str = DB_FILE) -> bool:
    """Actualiza el nombre de una categoría y actualiza los platos asociados en Menu."""
    clean_name = nuevo_nombre.strip()
    if not clean_name:
        return False
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM Categorias WHERE id = ?", (categoria_id,))
        old_cat = cursor.fetchone()
        if not old_cat:
            return False
        old_name = old_cat["nombre"]

        cursor.execute("UPDATE Categorias SET nombre = ? WHERE id = ?", (clean_name, categoria_id))
        cursor.execute("UPDATE Menu SET categoria = ? WHERE categoria = ?", (clean_name, old_name))
        conn.commit()
        return True

def delete_category(categoria_id: int, db_path: str = DB_FILE) -> bool:
    """Elimina una categoría y reasigna sus platos a 'General'."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM Categorias WHERE id = ?", (categoria_id,))
        old_cat = cursor.fetchone()
        if not old_cat:
            return False
        cat_name = old_cat["nombre"]
        if cat_name.lower() == "general":
            return False  # No borrar la categoría base General

        cursor.execute("DELETE FROM Categorias WHERE id = ?", (categoria_id,))
        cursor.execute("UPDATE Menu SET categoria = 'General' WHERE categoria = ?", (cat_name,))
        conn.commit()
        return True

def get_menu_grouped_by_category(db_path: str = DB_FILE, only_available: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """Retorna los platos del menú agrupados por categoría."""
    items = get_available_menu(db_path) if only_available else get_all_menu(db_path)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        cat = item.get("categoria", "General")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(item)
    return grouped

# ==================== OPERACIONES DE MENÚ ====================

def _normalize_text(text: str) -> str:
    """Normaliza texto removiendo acentos y convirtiendo a minúsculas."""
    t = text.lower()
    t = t.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ü', 'u')
    return t

def _stem_word(w: str) -> str:
    """Remueve terminaciones plurales comunes en español para mejorar coincidencias."""
    w = _normalize_text(w)
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    return w

def find_menu_item(nombre_busqueda: str, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """
    Busca un producto en el menú disponible con tolerancia a mayúsculas/minúsculas,
    acentos, plurales y coincidencias parciales.
    """
    cleaned = _normalize_text(nombre_busqueda.strip())
    if not cleaned:
        return None
        
    menu = get_available_menu(db_path)
    if not menu:
        menu = get_all_menu(db_path)
    
    # 1. Coincidencia exacta
    for item in menu:
        if _normalize_text(item["nombre"].strip()) == cleaned:
            return item
            
    # 2. Coincidencia por subcadena
    for item in menu:
        item_name = _normalize_text(item["nombre"].strip())
        if item_name in cleaned or cleaned in item_name:
            return item

    # 3. Coincidencia por palabras clave normalizadas y lematizadas
    search_words = set(_stem_word(w) for w in re.findall(r"\w+", cleaned))
    stop_words = {"de", "la", "el", "los", "las", "un", "uno", "una", "con", "sin", "en", "para", "por", "x", "ordenar", "pedir", "quiero", "dame", "favor", "porfa"}
    meaningful_search = {w for w in search_words if w not in stop_words and len(w) > 2}
    if not meaningful_search:
        meaningful_search = search_words

    best_match = None
    max_overlap = 0
    best_ratio = 0.0
    for item in menu:
        item_words = set(_stem_word(w) for w in re.findall(r"\w+", item["nombre"]))
        overlap = len(meaningful_search.intersection(item_words))
        
        ratio = overlap / len(meaningful_search) if meaningful_search else 0
        if overlap > max_overlap and ratio >= 0.6:
            max_overlap = overlap
            best_ratio = ratio
            best_match = item

    if best_match:
        return best_match
        
    return None

def get_all_menu(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Menu ORDER BY categoria, id")
        return [dict(row) for row in cursor.fetchall()]

def get_available_menu(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Menu WHERE disponible = 1 ORDER BY categoria, id")
        return [dict(row) for row in cursor.fetchall()]

def add_menu_item(nombre: str, precio: float, ingredientes: str = "", categoria: str = "General", disponible: bool = True, db_path: str = DB_FILE) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Menu (nombre, precio, ingredientes, categoria, disponible) VALUES (?, ?, ?, ?, ?)",
            (nombre, precio, ingredientes, categoria, 1 if disponible else 0)
        )
        conn.commit()
        return cursor.lastrowid

def update_menu_item(item_id: int, nombre: str, precio: float, ingredientes: str, categoria: str, disponible: bool, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Menu SET nombre = ?, precio = ?, ingredientes = ?, categoria = ?, disponible = ? WHERE id = ?",
            (nombre, precio, ingredientes, categoria, 1 if disponible else 0, item_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def toggle_menu_availability(item_id: int, disponible: Optional[bool] = None, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if disponible is None:
            cursor.execute("UPDATE Menu SET disponible = CASE WHEN disponible = 1 THEN 0 ELSE 1 END WHERE id = ?", (item_id,))
        else:
            cursor.execute("UPDATE Menu SET disponible = ? WHERE id = ?", (1 if disponible else 0, item_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_menu_item(item_id: int, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Menu WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0

def check_and_expire_session(id_cliente: str, incoming_msg: str = "", db_path: str = DB_FILE) -> bool:
    """
    Verifica si la sesión del cliente ha expirado (más de 2 horas sin actividad)
    o si el cliente envía un saludo explícito / reinicio cuando no está pagando.
    Si expira o se reinicia, vacía Carrito_Temporal y Mensajes_Contexto y retorna True.
    """
    msg_l = incoming_msg.lower().strip()
    is_greeting_or_reset = msg_l in [
        "hola", "buenas", "buenos dias", "buenos días", "buen dia", "buen día", 
        "buenas tardes", "buenas noches", "reiniciar", "/reiniciar", "reset", "/reset", 
        "limpiar", "cancelar pedido", "borrar pedido", "empezar de nuevo"
    ]
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(ultima_actividad) as last_act FROM Carrito_Temporal WHERE id_cliente = ?",
            (id_cliente,)
        )
        row = cursor.fetchone()
        last_act = row["last_act"] if row and row["last_act"] else None
        
        expired = False
        if last_act:
            try:
                if "T" in str(last_act):
                    last_dt = datetime.fromisoformat(str(last_act))
                else:
                    last_dt = datetime.strptime(str(last_act), "%Y-%m-%d %H:%M:%S")
                diff_seconds = (datetime.now() - last_dt).total_seconds()
                if diff_seconds > 7200:  # Más de 2 horas de inactividad
                    expired = True
            except Exception:
                pass
                
        has_address_or_payment = any(w in msg_l for w in ["calle", "cra", "carrera", "av", "diagonal", "transversal", "efectivo", "nequi", "transferencia", "datafono", "datáfono"])
        
        if expired or (is_greeting_or_reset and not has_address_or_payment):
            cursor.execute("DELETE FROM Carrito_Temporal WHERE id_cliente = ?", (id_cliente,))
            cursor.execute("DELETE FROM Mensajes_Contexto WHERE id_cliente = ?", (id_cliente,))
            cursor.execute("DELETE FROM Estado_Cliente WHERE id_cliente = ?", (id_cliente,))
            conn.commit()
            return True
            
        return False

def add_to_cart(
    id_cliente: str,
    nombre_producto: str,
    cantidad: int = 1,
    precio_unitario: Optional[float] = None,
    notas: str = "",
    db_path: str = DB_FILE
) -> bool:
    """
    Agrega un producto a la tabla Carrito_Temporal incluyendo notas o modificaciones y actualizando ultima_actividad.
    Si el producto con las mismas notas ya existe para este cliente, incrementa la cantidad.
    Si no se proporciona precio_unitario, busca el precio oficial en el Menú.
    """
    if cantidad <= 0:
        return False

    # Buscar información oficial en el menú si existe
    menu_item = find_menu_item(nombre_producto, db_path=db_path)
    if menu_item:
        official_name = menu_item["nombre"]
        official_price = float(menu_item["precio"])
    else:
        official_name = nombre_producto.strip()
        if precio_unitario is not None:
            official_price = float(precio_unitario)
        else:
            return False

    # Limpiar notas si es "Ninguna", "No", "-", etc.
    clean_notas = ""
    if notas and notas.strip().lower() not in ("ninguna", "ninguno", "sin modificaciones", "no", "n/a", "none", "-", ""):
        clean_notas = notas.strip()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Verificar si ya existe en el carrito con las mismas notas
        cursor.execute(
            """
            SELECT id, cantidad FROM Carrito_Temporal 
            WHERE id_cliente = ? AND LOWER(nombre_producto) = LOWER(?) AND LOWER(COALESCE(notas, '')) = LOWER(?)
            """,
            (id_cliente, official_name, clean_notas)
        )
        existing = cursor.fetchone()

        if existing:
            new_qty = existing["cantidad"] + cantidad
            cursor.execute(
                "UPDATE Carrito_Temporal SET cantidad = ?, precio_unitario = ?, notas = ?, ultima_actividad = ? WHERE id = ?",
                (new_qty, official_price, clean_notas, now_str, existing["id"])
            )
        else:
            cursor.execute(
                "INSERT INTO Carrito_Temporal (id_cliente, nombre_producto, cantidad, precio_unitario, notas, ultima_actividad) VALUES (?, ?, ?, ?, ?, ?)",
                (id_cliente, official_name, cantidad, official_price, clean_notas, now_str)
            )
        conn.commit()
        return True

def remove_from_cart(
    id_cliente: str,
    nombre_producto: str,
    cantidad: Optional[int] = None,
    db_path: str = DB_FILE
) -> bool:
    """
    Quita un producto del Carrito_Temporal y actualiza ultima_actividad.
    Si cantidad es None o >= cantidad actual, elimina el ítem por completo.
    Si cantidad < cantidad actual, decrementa la cantidad.
    """
    menu_item = find_menu_item(nombre_producto, db_path=db_path)
    search_name = menu_item["nombre"] if menu_item else nombre_producto.strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Buscar el ítem en el carrito del cliente
        cursor.execute(
            "SELECT id, cantidad FROM Carrito_Temporal WHERE id_cliente = ? AND (LOWER(nombre_producto) = LOWER(?) OR LOWER(nombre_producto) LIKE ?)",
            (id_cliente, search_name, f"%{search_name.lower()}%")
        )
        existing = cursor.fetchone()

        if not existing:
            return False

        if cantidad is not None and cantidad > 0 and existing["cantidad"] > cantidad:
            new_qty = existing["cantidad"] - cantidad
            cursor.execute(
                "UPDATE Carrito_Temporal SET cantidad = ?, ultima_actividad = ? WHERE id = ?",
                (new_qty, now_str, existing["id"])
            )
        else:
            cursor.execute(
                "DELETE FROM Carrito_Temporal WHERE id = ?",
                (existing["id"],)
            )
        conn.commit()
        return True

def get_cart(id_cliente: str, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    """Retorna los ítems en el carrito temporal para un cliente."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM Carrito_Temporal WHERE id_cliente = ? ORDER BY id ASC",
            (id_cliente,)
        )
        return [dict(row) for row in cursor.fetchall()]

def get_cart_summary_and_total(id_cliente: str, db_path: str = DB_FILE) -> Tuple[str, float, List[Dict[str, Any]]]:
    """
    Calcula el total exacto (multiplicando cantidad por precio unitario)
    y devuelve un string con el resumen del carrito (incluyendo notas), el total numérico y la lista de ítems.
    """
    items = get_cart(id_cliente, db_path=db_path)
    if not items:
        return "Carrito vacío", 0.0, []

    item_summaries = []
    total = 0.0
    for it in items:
        subtotal = it["cantidad"] * it["precio_unitario"]
        total += subtotal
        nota_str = f" ({it['notas']})" if it.get("notas") else ""
        item_summaries.append(f"{it['cantidad']}x {it['nombre_producto']}{nota_str} (${subtotal:,.0f})")

    summary_str = ", ".join(item_summaries)
    return summary_str, total, items

def clear_cart(id_cliente: str, db_path: str = DB_FILE) -> int:
    """Vacía el carrito temporal de un cliente."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carrito_Temporal WHERE id_cliente = ?", (id_cliente,))
        conn.commit()
        return cursor.rowcount

# ==================== OPERACIONES DE MÉTODOS DE PAGO ====================

def get_all_payment_methods(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Metodos_Pago ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

def get_active_payment_methods(db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Metodos_Pago WHERE activo = 1 ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

def add_payment_method(nombre: str, activo: bool = True, pide_cambio: bool = False, db_path: str = DB_FILE) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Metodos_Pago (nombre, activo, pide_cambio) VALUES (?, ?, ?)",
            (nombre, 1 if activo else 0, 1 if pide_cambio else 0)
        )
        conn.commit()
        return cursor.lastrowid

def update_payment_method(method_id: int, nombre: str, activo: bool, pide_cambio: bool, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Metodos_Pago SET nombre = ?, activo = ?, pide_cambio = ? WHERE id = ?",
            (nombre, 1 if activo else 0, 1 if pide_cambio else 0, method_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def toggle_payment_active(method_id: int, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Metodos_Pago SET activo = CASE WHEN activo = 1 THEN 0 ELSE 1 END WHERE id = ?", (method_id,))
        conn.commit()
        return cursor.rowcount > 0

def toggle_payment_pide_cambio(method_id: int, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Metodos_Pago SET pide_cambio = CASE WHEN pide_cambio = 1 THEN 0 ELSE 1 END WHERE id = ?", (method_id,))
        conn.commit()
        return cursor.rowcount > 0

def delete_payment_method(method_id: int, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Metodos_Pago WHERE id = ?", (method_id,))
        conn.commit()
        return cursor.rowcount > 0

# ==================== OPERACIONES DE MENSAJES / CONTEXTO ====================

def save_chat_message(id_cliente: str, rol: str, mensaje: str, db_path: str = DB_FILE) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Mensajes_Contexto (id_cliente, rol, mensaje, fecha_hora) VALUES (?, ?, ?, ?)",
            (id_cliente, rol, mensaje, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return cursor.lastrowid

def get_chat_history(id_cliente: str, limit: int = 15, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT rol, mensaje, fecha_hora 
            FROM Mensajes_Contexto 
            WHERE id_cliente = ? 
            ORDER BY id DESC 
            LIMIT ?
            """,
            (id_cliente, limit)
        )
        rows = cursor.fetchall()
        # Invertir para orden cronológico
        return [dict(row) for row in reversed(rows)]

def clear_client_history(id_cliente: str, db_path: str = DB_FILE) -> int:
    """Elimina los mensajes de contexto, el carrito temporal y el estado de un cliente."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Mensajes_Contexto WHERE id_cliente = ?", (id_cliente,))
        cursor.execute("DELETE FROM Carrito_Temporal WHERE id_cliente = ?", (id_cliente,))
        cursor.execute("DELETE FROM Estado_Cliente WHERE id_cliente = ?", (id_cliente,))
        conn.commit()
        return cursor.rowcount

def reset_client_session(id_cliente: str, db_path: str = DB_FILE) -> Tuple[int, int]:
    """
    Reinicia por completo la sesión del cliente:
    Elimina todos los registros de Carrito_Temporal, Mensajes_Contexto y Estado_Cliente para ese id_cliente.
    Retorna (registros_carrito_eliminados, mensajes_eliminados).
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Carrito_Temporal WHERE id_cliente = ?", (id_cliente,))
        deleted_cart = cursor.rowcount
        cursor.execute("DELETE FROM Mensajes_Contexto WHERE id_cliente = ?", (id_cliente,))
        deleted_msgs = cursor.rowcount
        cursor.execute("DELETE FROM Estado_Cliente WHERE id_cliente = ?", (id_cliente,))
        conn.commit()
        return deleted_cart, deleted_msgs

# ==================== OPERACIONES DE ESTADO DE CLIENTE (CHECKOUT) ====================

def get_client_state(id_cliente: str, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Retorna el estado de checkout del cliente o un dict con valores por defecto."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Estado_Cliente WHERE id_cliente = ?", (id_cliente,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {
            "id_cliente": id_cliente,
            "direccion": None,
            "metodo_pago": None,
            "paga_con": None,
            "estado": "ordenando"
        }

def update_client_state(
    id_cliente: str,
    direccion: Optional[str] = None,
    metodo_pago: Optional[str] = None,
    paga_con: Optional[str] = None,
    estado: Optional[str] = None,
    db_path: str = DB_FILE
) -> None:
    """Actualiza o inserta el estado de checkout del cliente."""
    current = get_client_state(id_cliente, db_path=db_path)
    new_dir = direccion if direccion is not None else current.get("direccion")
    new_met = metodo_pago if metodo_pago is not None else current.get("metodo_pago")
    new_pag = paga_con if paga_con is not None else current.get("paga_con")
    new_est = estado if estado is not None else current.get("estado", "ordenando")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Estado_Cliente (id_cliente, direccion, metodo_pago, paga_con, estado)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id_cliente) DO UPDATE SET
                direccion = excluded.direccion,
                metodo_pago = excluded.metodo_pago,
                paga_con = excluded.paga_con,
                estado = excluded.estado
            """,
            (id_cliente, new_dir, new_met, new_pag, new_est)
        )
        conn.commit()

def clear_client_state(id_cliente: str, db_path: str = DB_FILE) -> int:
    """Elimina el estado de checkout de un cliente."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Estado_Cliente WHERE id_cliente = ?", (id_cliente,))
        conn.commit()
        return cursor.rowcount

# ==================== OPERACIONES DE PEDIDOS ====================

def add_confirmed_order(
    id_cliente: str,
    resumen_pedido: str,
    notas_especiales: str,
    direccion: str,
    metodo_pago: str,
    cambio_de: str,
    total: float = 0.0,
    estado: str = "Pendiente",
    db_path: str = DB_FILE
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Pedidos_Confirmados 
            (id_cliente, resumen_pedido, notas_especiales, direccion, metodo_pago, cambio_de, total, fecha_hora, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_cliente,
                resumen_pedido,
                notas_especiales,
                direccion,
                metodo_pago,
                cambio_de,
                total,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                estado
            )
        )
        conn.commit()
        return cursor.lastrowid

def get_all_orders(status_filter: Optional[str] = None, db_path: str = DB_FILE) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if status_filter and status_filter != "Todos":
            cursor.execute("SELECT * FROM Pedidos_Confirmados WHERE estado = ? ORDER BY id DESC", (status_filter,))
        else:
            cursor.execute("SELECT * FROM Pedidos_Confirmados ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_order_by_id(order_id: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Pedidos_Confirmados WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_order_status(order_id: int, nuevo_estado: str, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Pedidos_Confirmados SET estado = ? WHERE id = ?", (nuevo_estado, order_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_order(order_id: int, db_path: str = DB_FILE) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Pedidos_Confirmados WHERE id = ?", (order_id,))
        conn.commit()
        return cursor.rowcount > 0

# ==================== ALMACENAMIENTO, MÉTRICAS Y LIMPIEZA ====================

def get_storage_stats(db_path: str = DB_FILE) -> Dict[str, Any]:
    """Obtiene métricas de tamaño de BD, conteo de registros y estadísticas."""
    size_bytes = 0
    if os.path.exists(db_path):
        size_bytes = os.path.getsize(db_path)
        
    size_kb = size_bytes / 1024.0
    size_mb = size_kb / 1024.0
    size_str = f"{size_mb:.2f} MB" if size_mb >= 1.0 else f"{size_kb:.1f} KB"

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM Mensajes_Contexto")
        total_mensajes = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM Pedidos_Confirmados")
        total_pedidos = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM Pedidos_Confirmados WHERE estado = 'Pendiente'")
        pedidos_pendientes = cursor.fetchone()["c"]

        cursor.execute("SELECT COUNT(*) as c FROM Menu")
        total_platos = cursor.fetchone()["c"]

    return {
        "db_path": db_path,
        "size_bytes": size_bytes,
        "size_formatted": size_str,
        "total_mensajes": total_mensajes,
        "total_pedidos": total_pedidos,
        "pedidos_pendientes": pedidos_pendientes,
        "total_platos": total_platos
    }

def purge_chat_messages(days_older_than: Optional[int] = None, db_path: str = DB_FILE) -> int:
    """Elimina mensajes de contexto. Si days_older_than es None o 0, elimina todos."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if days_older_than and days_older_than > 0:
            limit_date = (datetime.now() - timedelta(days=days_older_than)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("DELETE FROM Mensajes_Contexto WHERE fecha_hora < ?", (limit_date,))
        else:
            cursor.execute("DELETE FROM Mensajes_Contexto")
        deleted = cursor.rowcount
        conn.commit()
    optimize_db(db_path)
    return deleted

def purge_completed_orders(db_path: str = DB_FILE) -> int:
    """Elimina pedidos que ya hayan sido despachados o cancelados."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Pedidos_Confirmados WHERE estado IN ('Enviado', 'Despachado', 'Cancelado')")
        deleted = cursor.rowcount
        conn.commit()
    optimize_db(db_path)
    return deleted

def optimize_db(db_path: str = DB_FILE):
    """Ejecuta VACUUM para liberar espacio no utilizado."""
    try:
        with get_connection(db_path) as conn:
            conn.execute("VACUUM;")
    except Exception:
        pass
