import re
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import traceback
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from backend import database

logger = logging.getLogger("AIService")

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"

class AIService:
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.simulation_mode = False
        self._cached_status = None
        self._last_status_check = 0.0
        
        # Robust connection: Session with retries
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        
        # Lock to prevent overloading Ollama with concurrent requests
        self.llm_lock = threading.Lock()

    def check_ollama_status(self, force: bool = False) -> Dict[str, Any]:
        """Comprueba si el servidor de Ollama está activo y si el modelo está descargado."""
        import time
        now = time.time()
        if not force and self._cached_status and (now - self._last_status_check < 3.0):
            return self._cached_status

        try:
            res = self.session.get(f"{self.ollama_url}/api/tags", timeout=0.4)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                found_model = next((m for m in models if self.model in m), None)
                has_model = bool(found_model)
                status = {
                    "online": True,
                    "available_models": models,
                    "has_target_model": has_model,
                    "target_model": found_model if found_model else self.model
                }
                self._cached_status = status
                self._last_status_check = now
                return status
        except Exception:
            pass
            
        status = {
            "online": False,
            "available_models": [],
            "has_target_model": False,
            "target_model": self.model
        }
        self._cached_status = status
        self._last_status_check = now
        return status

    def format_menu_display(self, db_path: str = database.DB_FILE) -> str:
        """
        Formatea el menú completo desde SQLite con categorías, precios e ingredientes
        de forma visualmente atractiva para WhatsApp.
        """
        grouped_menu = database.get_menu_grouped_by_category(db_path, only_available=True)
        if not grouped_menu:
            return "No hay productos disponibles en este momento."
        
        blocks = []
        for cat, items in grouped_menu.items():
            lines = [f"*{cat.upper()}*"]
            for item in items:
                ing = f" ({item['ingredientes']})" if item.get('ingredientes') else ""
                lines.append(f"- {item['nombre']}: ${item['precio']:,.0f} COP{ing}")
                if item.get("tiene_combo"):
                    lines.append(f"  └ En combo ({item.get('desc_combo', '')}): ${item.get('precio_combo', 0):,.0f} COP")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def format_out_of_stock_display(self, db_path: str = database.DB_FILE) -> str:
        """Formatea la lista de productos que normalmente venden pero que hoy están agotados."""
        grouped_menu = database.get_menu_grouped_by_category(db_path, only_available=False)
        out_of_stock = []
        for cat, items in grouped_menu.items():
            for item in items:
                if not item["disponible"]:
                    out_of_stock.append(item["nombre"])
        if not out_of_stock:
            return "Ninguno"
        return ", ".join(out_of_stock)

    def format_cart_display(self, id_cliente: Optional[str], db_path: str = database.DB_FILE) -> str:
        """
        Formatea el resumen del carrito actual del cliente y el total a pagar calculado por Python.
        """
        if not id_cliente:
            return "Carrito vacío ($0 COP)"
        
        items = database.get_cart(id_cliente, db_path=db_path)
        if not items:
            return "Carrito vacío ($0 COP)"
        
        lines = []
        total = 0.0
        for it in items:
            subtotal = it["cantidad"] * it["precio_unitario"]
            total += subtotal
            nota_str = f" ({it['notas']})" if it.get("notas") else ""
            lines.append(f"- {it['cantidad']}x {it['nombre_producto']}{nota_str} (${subtotal:,.0f} COP)")
        
        lines.append(f"Total a pagar (Subtotal): ${total:,.0f} COP")
        
        # Añadir domicilio si está activo
        dom_activo = database.get_config("domicilio_activo", "0", db_path=db_path) == "1"
        if dom_activo:
            try:
                dom_precio = float(database.get_config("domicilio_precio", "0", db_path=db_path))
                if dom_precio > 0:
                    lines.append(f"- Domicilio: ${dom_precio:,.0f} COP")
                    total += dom_precio
            except ValueError:
                pass
        
        lines.append(f"TOTAL FINAL (Incluye domicilio si aplica): ${total:,.0f} COP")
        return "\n".join(lines)

    def build_system_prompt(self, id_cliente: Optional[str] = None, db_path: str = database.DB_FILE) -> str:
        """
        System Prompt Único y Autónomo para la IA.
        La IA tiene control conversacional total y emite etiquetas de acción al final de su mensaje.
        """
        menu_completo = self.format_menu_display(db_path)
        menu_agotado = self.format_out_of_stock_display(db_path)
        carrito_actual = self.format_cart_display(id_cliente, db_path)
        _, total_cuenta, _ = database.get_cart_summary_and_total(id_cliente, db_path) if id_cliente else ("", 0.0, [])
        
        # Obtener métodos de pago dinámicamente
        all_pms = database.get_all_payment_methods(db_path)
        pm_names = [pm["nombre"] for pm in all_pms if pm["activo"]]
        pm_agotados = [pm["nombre"] for pm in all_pms if not pm["activo"]]
        pm_change = [pm["nombre"] for pm in all_pms if pm["activo"] and pm["pide_cambio"]]
        
        pm_str = ", ".join(pm_names) if pm_names else "Efectivo"
        pm_change_str = ", ".join(pm_change) if pm_change else "Efectivo"
        pm_agotados_str = ", ".join(pm_agotados) if pm_agotados else "Ninguno"

        dom_activo = database.get_config("domicilio_activo", "0", db_path) == "1"
        if dom_activo:
            try:
                dom_precio = float(database.get_config("domicilio_precio", "0", db_path))
            except ValueError:
                dom_precio = 0.0
            ejemplo_cierre = f'''Tú: "Perfecto. Aquí tienes el resumen de tu pedido:
- 1x Hamburguesa Clásica (sin cebolla) ($18,000 COP)
- Domicilio (${dom_precio:,.0f} COP)
El total final es de ${18000 + dom_precio:,.0f} COP. ¿A qué dirección te enviamos el pedido?"'''
        else:
            ejemplo_cierre = '''Tú: "Perfecto. Aquí tienes el resumen de tu pedido:
- 1x Hamburguesa Clásica (sin cebolla) ($18,000 COP)
El total final es de $18,000 COP. ¿A qué dirección te enviamos el pedido?"'''

        menu_format = database.get_config("menu_format", "texto", db_path)
        menu_link = database.get_config("menu_link", "", db_path)
        
        if menu_format == "link" and menu_link.strip():
            regla_mostrar_menu = f"""9. MOSTRAR MENÚ: Si el cliente pide ver el menú, envíale únicamente el siguiente enlace: {menu_link}. Adicionalmente, si hay productos en la LISTA DE AGOTADOS, menciónalos brevemente diciendo algo como "Por el momento no tenemos disponible: [productos]". Si no hay productos agotados (la lista dice "Ninguno"), no menciones nada sobre agotados."""
        else:
            regla_mostrar_menu = """9. MOSTRAR MENÚ: Si el cliente pide ver el menú, NUNCA lo resumas ni envíes solo las categorías. Debes enviarlo COMPLETO, exactamente con los mismos nombres, precios e ingredientes como se muestra en la sección MENÚ DISPONIBLE HOY."""

        system_prompt = f"""Eres un empleado serio que toma pedidos por WhatsApp de forma concisa y normal, sin adornos.

REGLAS DE COMPORTAMIENTO (¡CRÍTICO!):
1. TONO: Actúa como una persona normal y seria. NO uses signos de exclamación. NO seas excesivamente complaciente ni ofrezcas comentarios innecesarios. NUNCA ofrezcas ingredientes si el cliente no los pide. NUNCA escribas "[0 COP]" al final de tus mensajes.
2. PRECIOS: Los precios son FIJOS. NUNCA restes ni sumes dinero por tu cuenta.
3. INGREDIENTES: Si piden quitar un ingrediente que el plato no tiene, aclárale amablemente que no trae eso originalmente y tómale el pedido.
4. DIRECCIÓN Y PAGO: NUNCA pidas todo de una vez. Cuando el cliente termine de pedir, envíale un DESGLOSE DETALLADO de todo lo que pidió (ítem por ítem con su valor, INCLUYENDO SIEMPRE LAS NOTAS o modificaciones de cada producto, y el valor del Domicilio si aplica) y el TOTAL FINAL, y a continuación pídele su dirección. Luego de la dirección, pregunta método de pago.
   - Métodos ACEPTADOS hoy: {pm_str}. 
   - Métodos DESACTIVADOS hoy: {pm_agotados_str}.
   Si elige un método DESACTIVADO o que no existe, dile que no está disponible hoy. 
   - Métodos que REQUIEREN CAMBIO: {pm_change_str}. Si elige uno de estos, pregúntale con cuánto paga. ¡OJO! Debes verificar que el monto con el que va a pagar sea MAYOR O IGUAL al total de la cuenta. Si es menor (ej. la cuenta es $9000 y te dice que paga con "5"), dile que el monto es insuficiente. Si elige un método que NO requiere cambio, simplemente dile que el domiciliario recibirá el pago en su casa.
5. CONFIRMACIÓN FINAL: Solo cuando el cliente te haya dado 1) Su dirección real 2) El método de pago real y 3) Con cuánto paga (solo si el método requiere cambio, si no requiere asume N/A), emites la etiqueta final de NUEVO_PEDIDO.
6. PRODUCTOS DEL MENÚ: SOLO PUEDES AGREGAR PRODUCTOS QUE ESTÉN EN EL MENÚ DISPONIBLE. Si el cliente pide algo que está en PRODUCTOS AGOTADOS, dile que de momento no tienen eso y que para mañana lo van a conseguir. Si pide algo que no está ni en disponibles ni agotados, dile que no venden ese tipo de cosas. NUNCA inventes productos ni asumas sustituciones (ej. si piden el "Producto A" y no lo tienes, no asumas que quieren el "Producto B").
7. CIERRE DE PEDIDO: Si el cliente intenta cerrar el pedido (ej. dice "nada más") pero el carrito está vacío (Total: $0 COP), NO pidas dirección. Dile al cliente que su carrito está vacío y pregúntale qué desea agregar. Si NO está vacío, envíale el desglose detallado con el domicilio y el total antes de pedir la dirección.
8. LISTA DE AGOTADOS: NUNCA leas la lista entera de productos agotados al cliente ni se la envíes de forma proactiva. Solo úsala para saber qué responder si te piden un producto en específico que está en esa lista.
10. COMBOS: Si un cliente pide un producto que tiene disponible una versión 'en combo', pero no especifica si lo quiere sencillo o en combo, DEBES preguntarle y confirmar cuál de los dos prefiere antes de agregarlo al pedido.
{regla_mostrar_menu}

=== MENÚ DISPONIBLE HOY ===
{menu_completo}

=== PRODUCTOS AGOTADOS ===
{menu_agotado}

ESTADO DEL PEDIDO DEL CLIENTE:
- Productos en el carrito: {carrito_actual}
- Total: ${total_cuenta:,.0f} COP

REGLAS DE ETIQUETAS SECRETAS:
Debes colocar las etiquetas al final de tu mensaje de forma invisible para el usuario. (Nota: NO escribas la palabra "OBLIGATORIO" en tus mensajes, solo imprime la etiqueta).
- Para agregar CADA producto: [AGREGAR: Nombre EXACTO del Producto según el Menú | Cantidad | Notas o Ninguna] (SOLO emite esta etiqueta UNA vez en el momento en que te lo piden. NUNCA la repitas en mensajes siguientes).
- Para cerrar el pedido al final de la charla: [NUEVO_PEDIDO: Dirección Real | Metodo de Pago Real | Monto Real o N/A]

EJEMPLOS DE CONVERSACIÓN (¡IMÍTALOS EXACTAMENTE!):

Cliente: "dame el Plato 1 sin cebolla y el Agotado 5"
Tú: "Perfecto te anoto el Plato 1 sin cebolla. Sobre el Agotado 5, de momento no lo tenemos y para mañana lo vamos a conseguir. ¿Deseas pedir algo más? [AGREGAR: Plato 1 | 1 | sin cebolla]"

Cliente: "y dame un carro"
Tú: "No vendemos carros. Solo tenemos lo que está en nuestro menú. ¿Deseas pedir algo más?"

Cliente: "dame una Hamburguesa Clásica" (Asumiendo que tiene opción en combo)
Tú: "¿La Hamburguesa Clásica la deseas sencilla o en combo?"

Cliente: "en combo"
Tú: "Perfecto. ¿Deseas pedir algo más? [AGREGAR: Hamburguesa Clásica | 1 | en combo]"

Cliente: "eso seria todo"
{ejemplo_cierre}

Cliente: "a la [Dirección que dio el cliente]"
Tú: "Anotado. ¿Cómo prefieres pagar? Tenemos {pm_str}."

Cliente: "en efectivo" (Asumiendo que Efectivo es un método que requiere cambio)
Tú: "¿Con cuánto vas a pagar para enviarte el cambio exacto?"

Cliente: "con [Monto que dio el cliente]"
Tú: "Listo. Tu pedido va en camino a la [Dirección que dio el cliente] y te llevaremos cambio de [Monto que dio el cliente]. Que lo disfrutes. [NUEVO_PEDIDO: [Dirección que dio el cliente] | Efectivo | [Monto que dio el cliente]]"

Cliente: "transferencia" (Asumiendo que Transferencia es un método que NO requiere cambio)
Tú: "Listo. Tu pedido va en camino a la [Dirección que dio el cliente]. El pago lo realizarás cuando el domiciliario llegue a tu casa y recibas el pedido. Que lo disfrutes. [NUEVO_PEDIDO: [Dirección que dio el cliente] | Transferencia | N/A]"
"""
        return system_prompt

    # Alias de compatibilidad
    build_extraction_prompt = build_system_prompt
    build_human_generation_prompt = build_system_prompt

    def evaluate_fast_rules(
        self,
        incoming_msg: str,
        id_cliente: str,
        db_path: str = database.DB_FILE
    ) -> Optional[Tuple[str, Optional[Dict[str, Any]]]]:
        """
        Enrutador rápido de comandos directos del sistema:
        - Reinicio explícito de sesión ("reiniciar", "/reset", etc.).
        """
        msg_clean = incoming_msg.strip().lower()

        # Reinicio / Reset explícito
        if msg_clean in ["reiniciar", "/reiniciar", "reset", "/reset", "limpiar", "cancelar pedido", "borrar pedido", "empezar de nuevo"]:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [DEBUG] -> Detectado comando de reinicio para {id_cliente}")
            database.reset_client_session(id_cliente, db_path=db_path)
            return "Sesión y carrito reiniciados correctamente. Hola. ¿En qué te puedo colaborar hoy?", None

        return None

    def process_incoming_message(
        self,
        id_cliente: str,
        incoming_msg: str,
        db_path: str = database.DB_FILE
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Arquitectura de Pase Único con IA Autónoma:
        1. Carga contexto e historial de SQLite.
        2. La IA genera la respuesta conversacional completa y emite etiquetas [AGREGAR:...], [QUITAR:...], [NUEVO_PEDIDO:...].
        3. Python ejecuta silenciosamente las acciones en la base de datos y limpia el texto final.
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"\n[{ts}] --- [NUEVO MENSAJE RECIBIDO] ---")
        print(f"[{ts}] Cliente ID: {id_cliente}")
        print(f"[{ts}] Mensaje: '{incoming_msg}'")

        try:
            # 1. Verificar expiración de sesión por inactividad (> 2 horas)
            database.check_and_expire_session(id_cliente, incoming_msg, db_path=db_path)

            # 2. Enrutador rápido para comandos de reinicio
            fast_result = self.evaluate_fast_rules(incoming_msg, id_cliente, db_path=db_path)
            if fast_result is not None:
                reply_text, order_data = fast_result
                database.save_chat_message(id_cliente, "user", incoming_msg, db_path=db_path)
                database.save_chat_message(id_cliente, "assistant", reply_text, db_path=db_path)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] [DEBUG] -> Respuesta de reinicio entregada.")
                return reply_text, order_data

            # 3. Guardar mensaje del usuario
            database.save_chat_message(id_cliente, "user", incoming_msg, db_path=db_path)

            # 4. Invocación autónoma de la IA (Ollama o simulación offline)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [DEBUG] 1. Llamando a la IA con contexto completo...")
            raw_response = self._call_autonomous_llm(incoming_msg, id_cliente, db_path=db_path)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [DEBUG] 2. Respuesta raw de la IA: '{raw_response}'")

            # 5. Ejecutar acciones en SQLite a partir de las etiquetas emitidas
            saved_order_data = self._process_action_tags(raw_response, id_cliente, incoming_msg, db_path=db_path)

            # 6. Limpiar etiquetas para presentar al cliente
            clean_reply = self.clean_reply_text(raw_response)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [DEBUG] 3. Respuesta final al cliente: '{clean_reply}'")

            # 7. Guardar respuesta del asistente (con etiquetas para que la IA recuerde sus acciones)
            database.save_chat_message(id_cliente, "assistant", raw_response, db_path=db_path)

            return clean_reply, saved_order_data

        except Exception as e:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [ERROR CRÍTICO EN PROCESS_INCOMING_MESSAGE]:")
            traceback.print_exc()
            error_reply = "Disculpa, tuve un pequeño problema técnico al procesar tu mensaje. ¿Me repites qué deseas ordenar?"
            try:
                database.save_chat_message(id_cliente, "assistant", error_reply, db_path=db_path)
            except Exception:
                pass
            return error_reply, None

    def _call_autonomous_llm(
        self,
        incoming_msg: str,
        id_cliente: str,
        db_path: str = database.DB_FILE
    ) -> str:
        """Llama a Ollama en modo conversacional directo."""
        ollama_status = self.check_ollama_status()
        if ollama_status["online"] and not self.simulation_mode:
            system_prompt = self.build_system_prompt(id_cliente=id_cliente, db_path=db_path)
            history = database.get_chat_history(id_cliente, limit=8, db_path=db_path)
            
            messages = [{"role": "system", "content": system_prompt}]
            # Excluir el último mensaje ya guardado para evitar duplicados en messages
            for h in history[:-1]:
                messages.append({"role": h["rol"], "content": h["mensaje"]})
            messages.append({"role": "user", "content": incoming_msg})

            payload = {
                "model": ollama_status.get("target_model", self.model),
                "messages": messages,
                "stream": False,
                "keep_alive": "60m",
                "options": {
                    "temperature": 0.15,
                    "top_p": 0.9
                }
            }

            try:
                # El timeout se incrementa a 600s (10 minutos) para evitar caidas de conexion con modelos pesados
                with self.llm_lock:
                    res = self.session.post(f"{self.ollama_url}/api/chat", json=payload, timeout=600)
                if res.status_code == 200:
                    resp_json = res.json()
                    content = resp_json.get("message", {}).get("content", "").strip()
                    if content:
                        return content
            except Exception as e:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] Error en llamada a Ollama: {e}")
                logger.warning(f"Error en llamada a Ollama: {e}")

        # Fallback genérico si la IA no está disponible o el modo simulación (offline) está activo
        return "Disculpa, en este momento mi sistema de inteligencia artificial se encuentra fuera de servicio. Por favor, verifica que el motor de IA local esté encendido e intenta nuevamente."
    def _process_action_tags(
        self,
        raw_text: str,
        id_cliente: str,
        incoming_msg: str = "",
        db_path: str = database.DB_FILE
    ) -> Optional[Dict[str, Any]]:
        """Interpreta las etiquetas emitidas por la IA y ejecuta las operaciones SQL silenciosas."""
        # 1. Procesar AGREGAR (resiliente a corchetes o negritas de la IA)
        tags_agregar = re.findall(r'(?:\[|\*\*?)?\s*AGREGAR:\s*([^\|]+)\|\s*(\d+)\s*\|\s*([^\]\*]+)(?:\]|\*\*?)?', raw_text, flags=re.IGNORECASE)
        for prod_name, cant_str, notas_str in tags_agregar:
            prod_name = prod_name.strip()
            # Safeguard: ignorar si la IA imprimió la plantilla literal
            if "nombre exacto" in prod_name.lower() or "nombre del producto" in prod_name.lower():
                continue
                
            cant = int(cant_str.strip())
            notas = notas_str.strip()
            if notas.lower() in ("ninguna", "ninguno", "sin modificaciones", "n/a", ""):
                notas = ""
            menu_item = database.find_menu_item(prod_name, db_path=db_path)
            if menu_item:
                database.add_to_cart(
                    id_cliente=id_cliente,
                    nombre_producto=menu_item["nombre"],
                    cantidad=cant,
                    notas=notas,
                    db_path=db_path
                )
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] [DEBUG SQL] Agregado al carrito: {cant}x {menu_item['nombre']} ({notas})")

        # 2. Procesar QUITAR
        tags_quitar = re.findall(r'(?:\[|\*\*?)?\s*QUITAR:\s*([^\|]+)\|\s*([^\]\*]+)(?:\]|\*\*?)?', raw_text, flags=re.IGNORECASE)
        for prod_name, cant_str in tags_quitar:
            prod_name = prod_name.strip()
            cant = int(cant_str.strip())
            database.remove_from_cart(id_cliente, prod_name, cantidad=cant, db_path=db_path)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{ts}] [DEBUG SQL] Retirado del carrito: {cant}x {prod_name}")

        # 3. Procesar NUEVO_PEDIDO
        saved_order_data = None
        tag_pedido = re.search(r'(?:\[|\*\*?)?\s*NUEVO_PEDIDO:\s*([^\|]+)\|\s*([^\|]+)\|\s*([^\]\*]+)(?:\]|\*\*?)?', raw_text, flags=re.IGNORECASE)
        if tag_pedido:
            dir_envio, metodo, paga_con = tag_pedido.groups()
            dir_envio = dir_envio.strip()
            metodo = metodo.strip()
            paga_con = paga_con.strip()
            
            # Safeguard crítico: si la IA escupe la plantilla literal, se ignora
            if "direcci" in dir_envio.lower() or "monto" in paga_con.lower() or "método" in metodo.lower() or "metodo" in metodo.lower():
                return None
            
            cart_summary, cart_total, cart_items = database.get_cart_summary_and_total(id_cliente, db_path)
            if cart_items:
                cart_notes = [f"{it['nombre_producto']}: {it['notas']}" for it in cart_items if it.get("notas")]
                notas_final = "; ".join(cart_notes)
                cambio_final = paga_con if paga_con and paga_con.lower() != "n/a" else "Exacto / N/A"
                
                order_id = database.add_confirmed_order(
                    id_cliente=id_cliente,
                    resumen_pedido=cart_summary,
                    notas_especiales=notas_final,
                    direccion=dir_envio,
                    metodo_pago=metodo,
                    cambio_de=cambio_final,
                    total=cart_total,
                    estado="Pendiente",
                    db_path=db_path
                )
                saved_order_data = {
                    "id": order_id,
                    "id_cliente": id_cliente,
                    "resumen_pedido": cart_summary,
                    "notas_especiales": notas_final,
                    "direccion": dir_envio,
                    "metodo_pago": metodo,
                    "cambio_de": cambio_final,
                    "total": cart_total,
                    "estado": "Pendiente"
                }
                database.clear_cart(id_cliente, db_path)
                database.clear_client_state(id_cliente, db_path)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                print(f"[{ts}] [DEBUG SQL] Pedido confirmado creado #{order_id} para {dir_envio}")
                
                # Impresión Automática
                if database.get_config("impresora_activa", "0", db_path) == "1" and database.get_config("impresora_automatica", "0", db_path) == "1":
                    try:
                        from backend.impresora import imprimir_ticket_simulado
                        imprimir_ticket_simulado(
                            order_id,
                            id_cliente,
                            cart_summary,
                            notas_final,
                            dir_envio,
                            metodo,
                            cambio_final,
                            cart_total
                        )
                    except Exception as e:
                        print(f"[{ts}] [ERROR IMPRESORA] No se pudo imprimir automáticamente: {e}")

        return saved_order_data

    def clean_reply_text(self, text: str, id_cliente: Optional[str] = None, db_path: str = database.DB_FILE) -> str:
        """Limpia las etiquetas de acción del texto visible eliminando hasta el corchete de cierre."""
        cleaned = re.sub(r'(?:\[|\*\*?)?(?:AGREGAR|QUITAR|NUEVO_PEDIDO|VERIFICAR):[^\]\n]*(?:\]|\*\*?)?', '', text, flags=re.IGNORECASE)
        # Limpiar cosas alucinadas como [0 COP] o [CARRITO_VACÍO]
        cleaned = re.sub(r'\[\s*\d+\s*COP\s*\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[\s*CARRITO_VAC[ÍI]O\s*\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[\s*CARTEL\s+VAC[ÍI]O\s*\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[\s*OBLIGATORIO\s*\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^(?:Tú|Tu|Asistente|Bot):\s*', '', cleaned, flags=re.IGNORECASE).strip(' "\'\n')
        return cleaned.strip()

    # Compatibilidad con métodos de versiones previas para tests
    def generate_human_reply(self, *args, **kwargs) -> str:
        fallback = kwargs.get("fallback_reply", "Hola, ¿en qué te puedo colaborar hoy?")
        return fallback

    def _simulate_json_extraction(self, *args, **kwargs) -> Dict[str, Any]:
        return {"intencion": "pedir", "items_confirmados": []}

    def _process_extracted_json(self, *args, **kwargs) -> Tuple[str, None]:
        return "Hola, ¿en qué te puedo colaborar hoy?", None
