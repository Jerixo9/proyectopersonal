import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from backend import database
from backend import network_utils
from backend.ai_service import AIService
from backend.sound_player import play_order_alert_sound

# Inicializar Base de Datos al cargar
database.init_db()

# Instancia global de IA Service
ai_engine = AIService()

# Estado de Conexión del Teléfono (Heartbeat)
heartbeat_state = {
    "last_ping_time": 0.0,
    "device_name": "No conectado",
    "package_name": "",
    "ip": ""
}

# Callbacks para la Interfaz Gráfica (CustomTkinter)
ui_event_callbacks: List[Callable[[str, Any], None]] = []

def register_ui_callback(callback: Callable[[str, Any], None]):
    """Registra una función para recibir eventos de backend (nuevos pedidos, pings, etc.)."""
    if callback not in ui_event_callbacks:
        ui_event_callbacks.append(callback)

def unregister_ui_callback(callback: Callable[[str, Any], None]):
    if callback in ui_event_callbacks:
        ui_event_callbacks.remove(callback)

def notify_ui(event_type: str, data: Any = None):
    """Emite un evento síncrono a los oyentes de la GUI."""
    for cb in list(ui_event_callbacks):
        try:
            cb(event_type, data)
        except Exception:
            pass

def is_phone_connected(threshold_seconds: int = 35) -> bool:
    """Indica si el teléfono ha emitido un heartbeat en los últimos X segundos."""
    if heartbeat_state["last_ping_time"] == 0.0:
        return False
    return (time.time() - heartbeat_state["last_ping_time"]) <= threshold_seconds

def get_seconds_since_last_ping() -> Optional[int]:
    if heartbeat_state["last_ping_time"] == 0.0:
        return None
    return int(time.time() - heartbeat_state["last_ping_time"])

# Creación de FastAPI App
app = FastAPI(
    title="Sistema Automático de Toma de Pedidos IA",
    description="Servidor local para recepción de mensajes WhatsApp, IA local Llama 3.1 y gestión de pedidos.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para validación
class WebhookRequest(BaseModel):
    sender: str
    message: str
    package: Optional[str] = "com.whatsapp"

class HeartbeatRequest(BaseModel):
    device_name: Optional[str] = "Android Phone"
    package: Optional[str] = "com.whatsapp"
    status: Optional[str] = "active"

class CategoryRequest(BaseModel):
    nombre: str

class MenuItemRequest(BaseModel):
    nombre: str
    precio: float
    ingredientes: Optional[str] = ""
    categoria: Optional[str] = "General"
    disponible: Optional[bool] = True

class PaymentMethodRequest(BaseModel):
    nombre: str
    activo: Optional[bool] = True
    pide_cambio: Optional[bool] = False

class UpdateOrderStatusRequest(BaseModel):
    estado: str

class PurgeRequest(BaseModel):
    days: Optional[int] = 0

# ==================== ENDPOINTS PRINCIPALES ====================

@app.get("/")
def read_root():
    return {
        "app": "Sistema de Pedidos IA Local",
        "status": "online",
        "phone_connected": is_phone_connected(),
        "local_ip": network_utils.get_local_ip()
    }

@app.post("/api/heartbeat")
def receive_heartbeat(req: HeartbeatRequest):
    """Recibe el ping periódico de la app móvil Android."""
    heartbeat_state["last_ping_time"] = time.time()
    heartbeat_state["device_name"] = req.device_name or "Android"
    heartbeat_state["package_name"] = req.package or "com.whatsapp"
    
    notify_ui("heartbeat", {
        "status": "connected",
        "device": heartbeat_state["device_name"],
        "timestamp": heartbeat_state["last_ping_time"]
    })
    
    return {
        "status": "ok",
        "received_at": datetime.now().isoformat(),
        "phone_connected": True
    }

@app.post("/api/webhook")
def receive_incoming_message(req: WebhookRequest, background_tasks: BackgroundTasks):
    """
    Recibe el mensaje entrante desde la app Android (Watomatic).
    Procesa con la IA (Ollama / Gemma 3:4B), guarda contexto, detecta pedidos y retorna réplica.
    """
    sender = req.sender.strip()
    message = req.message.strip()
    
    if not sender or not message:
        raise HTTPException(status_code=400, detail="Sender y message no pueden estar vacíos.")

    # Procesar con motor de IA
    clean_reply, new_order = ai_engine.process_incoming_message(
        id_cliente=sender,
        incoming_msg=message
    )

    # Si se cerró un pedido
    if new_order:
        # Sonido de alerta
        background_tasks.add_task(play_order_alert_sound)
        # Notificar a la UI para disparar el Pop-up emergente y refrescar la lista
        notify_ui("new_order", new_order)
    else:
        notify_ui("chat_message", {
            "id_cliente": sender,
            "user_message": message,
            "reply": clean_reply
        })

    return {
        "status": "success",
        "reply": clean_reply,
        "order_created": new_order is not None,
        "order": new_order
    }

@app.get("/api/status")
def get_system_status():
    """Retorna el estado general de la app, red, conexión del teléfono e IA."""
    local_ip = network_utils.get_local_ip()
    phone_online = is_phone_connected()
    ollama_info = ai_engine.check_ollama_status()
    db_stats = database.get_storage_stats()

    return {
        "server_online": True,
        "local_ip": local_ip,
        "local_url": f"http://{local_ip}:8000",
        "phone_connected": phone_online,
        "phone_seconds_since_ping": get_seconds_since_last_ping(),
        "phone_device": heartbeat_state["device_name"],
        "ollama": ollama_info,
        "stats": db_stats
    }

# ==================== ENDPOINTS DE CATEGORÍAS ====================

@app.get("/api/categories")
def list_categories():
    return database.get_all_categories()

@app.post("/api/categories")
def create_category(cat: CategoryRequest):
    cat_id = database.add_category(cat.nombre)
    if not cat_id:
        raise HTTPException(status_code=400, detail="Nombre de categoría inválido")
    notify_ui("categories_updated")
    return {"id": cat_id, "message": "Categoría agregada con éxito"}

@app.put("/api/categories/{cat_id}")
def update_category(cat_id: int, cat: CategoryRequest):
    success = database.update_category(cat_id, cat.nombre)
    if not success:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    notify_ui("categories_updated")
    notify_ui("menu_updated")
    return {"message": "Categoría actualizada con éxito"}

@app.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int):
    success = database.delete_category(cat_id)
    if not success:
        raise HTTPException(status_code=400, detail="No se pudo eliminar la categoría (General es obligatoria)")
    notify_ui("categories_updated")
    notify_ui("menu_updated")
    return {"message": "Categoría eliminada y platos reasignados a General"}

# ==================== ENDPOINTS DE MENÚ ====================

@app.get("/api/menu")
def list_menu():
    return database.get_all_menu()

@app.post("/api/menu")
def create_menu_item(item: MenuItemRequest):
    item_id = database.add_menu_item(
        nombre=item.nombre,
        precio=item.precio,
        ingredientes=item.ingredientes or "",
        categoria=item.categoria or "General",
        disponible=item.disponible if item.disponible is not None else True
    )
    notify_ui("menu_updated")
    return {"id": item_id, "message": "Plato agregado con éxito"}

@app.put("/api/menu/{item_id}")
def update_menu_item(item_id: int, item: MenuItemRequest):
    success = database.update_menu_item(
        item_id=item_id,
        nombre=item.nombre,
        precio=item.precio,
        ingredientes=item.ingredientes or "",
        categoria=item.categoria or "General",
        disponible=item.disponible if item.disponible is not None else True
    )
    if not success:
        raise HTTPException(status_code=404, detail="Plato no encontrado")
    notify_ui("menu_updated")
    return {"message": "Plato actualizado con éxito"}

@app.patch("/api/menu/{item_id}/toggle")
def toggle_menu(item_id: int):
    success = database.toggle_menu_availability(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plato no encontrado")
    notify_ui("menu_updated")
    return {"message": "Disponibilidad cambiada"}

@app.delete("/api/menu/{item_id}")
def delete_menu(item_id: int):
    success = database.delete_menu_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plato no encontrado")
    notify_ui("menu_updated")
    return {"message": "Plato eliminado"}

# ==================== ENDPOINTS DE MÉTODOS DE PAGO ====================

@app.get("/api/payments")
def list_payments():
    return database.get_all_payment_methods()

@app.post("/api/payments")
def create_payment_method(item: PaymentMethodRequest):
    pid = database.add_payment_method(
        nombre=item.nombre,
        activo=item.activo if item.activo is not None else True,
        pide_cambio=item.pide_cambio if item.pide_cambio is not None else False
    )
    notify_ui("payments_updated")
    return {"id": pid, "message": "Método de pago agregado"}

@app.patch("/api/payments/{method_id}/toggle-active")
def toggle_payment_active(method_id: int):
    success = database.toggle_payment_active(method_id)
    if not success:
        raise HTTPException(status_code=404, detail="Método no encontrado")
    notify_ui("payments_updated")
    return {"message": "Estado activo cambiado"}

@app.patch("/api/payments/{method_id}/toggle-change")
def toggle_payment_change(method_id: int):
    success = database.toggle_payment_pide_cambio(method_id)
    if not success:
        raise HTTPException(status_code=404, detail="Método no encontrado")
    notify_ui("payments_updated")
    return {"message": "Opción pide cambio cambiada"}

@app.delete("/api/payments/{method_id}")
def delete_payment(method_id: int):
    success = database.delete_payment_method(method_id)
    if not success:
        raise HTTPException(status_code=404, detail="Método no encontrado")
    notify_ui("payments_updated")
    return {"message": "Método eliminado"}

# ==================== ENDPOINTS DE PEDIDOS ====================

@app.get("/api/orders")
def list_orders(status: Optional[str] = None):
    return database.get_all_orders(status_filter=status)

@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, req: UpdateOrderStatusRequest):
    success = database.update_order_status(order_id, req.estado)
    if not success:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    notify_ui("orders_updated")
    return {"message": f"Estado actualizado a {req.estado}"}

@app.delete("/api/orders/{order_id}")
def delete_order(order_id: int):
    success = database.delete_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    notify_ui("orders_updated")
    return {"message": "Pedido eliminado"}

# ==================== ENDPOINTS DE ALMACENAMIENTO ====================

@app.get("/api/storage")
def get_storage():
    return database.get_storage_stats()

@app.post("/api/storage/purge-messages")
def purge_messages(req: PurgeRequest):
    deleted = database.purge_chat_messages(days_older_than=req.days)
    notify_ui("storage_updated")
    return {"deleted_messages": deleted, "message": "Mensajes purgados con éxito"}

@app.post("/api/storage/purge-orders")
def purge_orders():
    deleted = database.purge_completed_orders()
    notify_ui("storage_updated")
    notify_ui("orders_updated")
    return {"deleted_orders": deleted, "message": "Pedidos completados eliminados"}

@app.post("/api/storage/vacuum")
def vacuum_database():
    database.optimize_db()
    notify_ui("storage_updated")
    return {"message": "Base de datos optimizada con VACUUM"}
