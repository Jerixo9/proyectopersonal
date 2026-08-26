import re
import json
import logging
import requests
import traceback
from typing import Dict, Any, List, Optional, Tuple
from backend import database

logger = logging.getLogger("AIService")

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"

class AIService:
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_URL, model: str = DEFAULT_MODEL):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.simulation_mode = False
        self._cached_status = None
        self._last_status_check = 0.0

    def check_ollama_status(self, force: bool = False) -> Dict[str, Any]:
        """Comprueba si el servidor de Ollama está activo y si el modelo está descargado."""
        import time
        now = time.time()
        if not force and self._cached_status and (now - self._last_status_check < 3.0):
            return self._cached_status

        try:
            res = requests.get(f"{self.ollama_url}/api/tags", timeout=0.4)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                has_model = any(self.model in m for m in models)
                status = {
                    "online": True,
                    "available_models": models,
                    "has_target_model": has_model,
                    "target_model": self.model
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
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

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
        
        lines.append(f"Total a pagar: ${total:,.0f} COP")
        return "\n".join(lines)

    def build_system_prompt(self, id_cliente: Optional[str] = None, db_path: str = database.DB_FILE) -> str:
        """
        System Prompt Único y Autónomo para la IA.
        La IA tiene control conversacional total y emite etiquetas de acción al final de su mensaje.
        """
        menu_completo = self.format_menu_display(db_path)
        carrito_actual = self.format_cart_display(id_cliente, db_path)
        _, total_cuenta, _ = database.get_cart_summary_and_total(id_cliente, db_path) if id_cliente else ("", 0.0, [])

        system_prompt = f"""Eres quien atiende el WhatsApp de nuestro restaurante. Eres una persona real: amable, concisa, directa y hablas con naturalidad (cero respuestas de contestadora automática).

MENÚ DEL LOCAL:
{menu_completo}

ESTADO DEL PEDIDO DEL CLIENTE:
- Productos en el carrito: {carrito_actual}
- Total: ${total_cuenta:,.0f} COP

REGLAS DE ATENCIÓN:
1. Si piden ver el menú, muéstralo completo y ordenado.
2. Si piden algo que NO está en el menú (ej. chorizo, salmón, pescado, empanadas, bagre, tilapia), diles con naturalidad que no manejas ese producto y recuérdales qué vendes. NUNCA asumas que un producto es una dirección.
3. Si piden productos del menú (incluso con lenguaje informal como "unas papas" o "un perro sin salsa"), confírmalos de forma breve y añade al final de tu respuesta la etiqueta correspondiente.
4. Si el cliente dice que no desea nada más ("eso es todo", "nada más"), dale el total y pídele su dirección y método de pago (Efectivo, Nequi, Transferencia o Datáfono).
5. Solo cuando el cliente te dé la dirección y método de pago, confirma el pedido y emite la etiqueta [NUEVO_PEDIDO:...].

SISTEMA DE ETIQUETAS (Colócalas SIEMPRE al final de tu mensaje si aplica):
- Para agregar: [AGREGAR: Nombre Exacto del Menú | Cantidad | Notas o Ninguna]
- Para quitar: [QUITAR: Nombre Exacto del Menú | Cantidad]
- Para cerrar pedido: [NUEVO_PEDIDO: Dirección | Método de Pago | Monto con que paga o N/A]
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
            print(f"[DEBUG] -> Detectado comando de reinicio para {id_cliente}")
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
        print(f"\n--- [NUEVO MENSAJE RECIBIDO] ---")
        print(f"Cliente ID: {id_cliente}")
        print(f"Mensaje: '{incoming_msg}'")

        try:
            # 1. Verificar expiración de sesión por inactividad (> 2 horas)
            database.check_and_expire_session(id_cliente, incoming_msg, db_path=db_path)

            # 2. Enrutador rápido para comandos de reinicio
            fast_result = self.evaluate_fast_rules(incoming_msg, id_cliente, db_path=db_path)
            if fast_result is not None:
                reply_text, order_data = fast_result
                database.save_chat_message(id_cliente, "user", incoming_msg, db_path=db_path)
                database.save_chat_message(id_cliente, "assistant", reply_text, db_path=db_path)
                print(f"[DEBUG] -> Respuesta de reinicio entregada.")
                return reply_text, order_data

            # 3. Guardar mensaje del usuario
            database.save_chat_message(id_cliente, "user", incoming_msg, db_path=db_path)

            # 4. Invocación autónoma de la IA (Ollama o simulación offline)
            print(f"[DEBUG] 1. Llamando a la IA con contexto completo...")
            raw_response = self._call_autonomous_llm(incoming_msg, id_cliente, db_path=db_path)
            print(f"[DEBUG] 2. Respuesta raw de la IA: '{raw_response}'")

            # 5. Ejecutar acciones en SQLite a partir de las etiquetas emitidas
            saved_order_data = self._process_action_tags(raw_response, id_cliente, incoming_msg, db_path=db_path)

            # 6. Limpiar etiquetas para presentar al cliente
            clean_reply = self.clean_reply_text(raw_response)
            print(f"[DEBUG] 3. Respuesta final al cliente: '{clean_reply}'")

            # 7. Guardar respuesta del asistente
            database.save_chat_message(id_cliente, "assistant", clean_reply, db_path=db_path)

            return clean_reply, saved_order_data

        except Exception as e:
            print("[ERROR CRÍTICO EN PROCESS_INCOMING_MESSAGE]:")
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
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.25,
                    "top_p": 0.9
                }
            }

            try:
                res = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=35)
                if res.status_code == 200:
                    resp_json = res.json()
                    content = resp_json.get("message", {}).get("content", "").strip()
                    if content:
                        return content
            except Exception as e:
                logger.warning(f"Error en llamada a Ollama: {e}")

        # Simulación offline / fallback autónomo
        return self._simulate_autonomous_response(incoming_msg, id_cliente, db_path=db_path)

    def _process_action_tags(
        self,
        raw_text: str,
        id_cliente: str,
        incoming_msg: str = "",
        db_path: str = database.DB_FILE
    ) -> Optional[Dict[str, Any]]:
        """Interpreta las etiquetas emitidas por la IA y ejecuta las operaciones SQL silenciosas."""
        # 1. Procesar AGREGAR: [AGREGAR: Nombre Exacto | Cantidad | Notas]
        tags_agregar = re.findall(r'\[AGREGAR:\s*(.*?)\s*\|\s*(\d+)\s*\|\s*(.*?)\]', raw_text, flags=re.IGNORECASE)
        for prod_name, cant_str, notas_str in tags_agregar:
            prod_name = prod_name.strip()
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
                print(f"[DEBUG SQL] Agregado al carrito: {cant}x {menu_item['nombre']} ({notas})")

        # 2. Procesar QUITAR: [QUITAR: Nombre Exacto | Cantidad]
        tags_quitar = re.findall(r'\[QUITAR:\s*(.*?)\s*\|\s*(\d+)\]', raw_text, flags=re.IGNORECASE)
        for prod_name, cant_str in tags_quitar:
            prod_name = prod_name.strip()
            cant = int(cant_str.strip())
            database.remove_from_cart(id_cliente, prod_name, cantidad=cant, db_path=db_path)
            print(f"[DEBUG SQL] Retirado del carrito: {cant}x {prod_name}")

        # 3. Procesar NUEVO_PEDIDO: [NUEVO_PEDIDO: Dirección | Método de Pago | Monto con que paga o N/A]
        saved_order_data = None
        tag_pedido = re.search(r'\[NUEVO_PEDIDO:\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\]', raw_text, flags=re.IGNORECASE)
        if tag_pedido:
            dir_envio, metodo, paga_con = tag_pedido.groups()
            dir_envio = dir_envio.strip()
            metodo = metodo.strip()
            paga_con = paga_con.strip()
            
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
                print(f"[DEBUG SQL] Pedido confirmado creado #{order_id} para {dir_envio}")

        return saved_order_data

    def clean_reply_text(self, text: str, id_cliente: Optional[str] = None, db_path: str = database.DB_FILE) -> str:
        """Limpia las etiquetas de acción [AGREGAR:...], [QUITAR:...], [NUEVO_PEDIDO:...] del texto visible."""
        cleaned = re.sub(r'\[(?:AGREGAR|QUITAR|NUEVO_PEDIDO):.*?\]', '', text, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'^(?:Tú|Tu|Asistente|Bot):\s*', '', cleaned, flags=re.IGNORECASE).strip(' "\'\n')
        return cleaned

    def _simulate_autonomous_response(
        self,
        incoming_msg: str,
        id_cliente: str,
        db_path: str = database.DB_FILE
    ) -> str:
        """
        Simulador offline de la IA para pruebas y ejecución determinista sin conexión a Ollama.
        Interpreta intenciones en lenguaje natural y emite las etiquetas de acción correspondientes.
        """
        msg_l = incoming_msg.lower().strip()
        menu = database.get_available_menu(db_path)
        cart = database.get_cart(id_cliente, db_path)
        cart_display = self.format_cart_display(id_cliente, db_path)
        _, cart_total, _ = database.get_cart_summary_and_total(id_cliente, db_path)

        # 1. Saludos simples
        if msg_l in ["hola", "buenas", "buenos dias", "buenos días", "buen dia", "buen día", "buenas tardes", "buenas noches", "hey", "hola amigo"]:
            return "Hola. ¿En qué te puedo colaborar hoy?"

        # 2. Petición explícita de menú
        if any(w in msg_l for w in ["menu", "menú", "carta", "la carta", "que tienen", "qué tienen", "ver menu", "ver menú", "dame el menu", "muestrame el menu", "muéstrame el menú"]):
            menu_display = self.format_menu_display(db_path)
            return f"Claro, aquí tienes nuestro menú:\n\n{menu_display}\n\n¿Qué te gustaría ordenar?"

        # 3. Preguntas de identidad / casual
        if any(w in msg_l for w in ["quien eres", "quién eres", "con quien hablo", "con quién hablo", "como te fue", "cómo te fue"]):
            return "Hola, soy el encargado de tomar los pedidos acá en el local por WhatsApp. ¿En qué te puedo colaborar hoy?"

        # 4. Quitar productos
        is_quitar = any(w in msg_l for w in ["quita", "quitar", "elimina", "eliminar", "borra", "borrar", "menos"])
        if is_quitar:
            for it in menu:
                if it["nombre"].lower() in msg_l or any(word in msg_l for word in it["nombre"].lower().split() if len(word) > 4):
                    qty = 1
                    qty_m = re.search(r"(\d+)", msg_l)
                    if qty_m:
                        qty = int(qty_m.group(1))
                    return f"Listo, he retirado {qty} {it['nombre']} de tu orden.\n\n[QUITAR: {it['nombre']} | {qty}]"

        # 5. Detección de combinaciones ambiguas / dudosas
        if "sancocho de hamburguesa" in msg_l:
            return "Disculpa, no te entendí bien. ¿Te refieres a nuestra Hamburguesa Clásica o buscas sancocho?"
        if "empanada de pizza" in msg_l:
            if "perro" in msg_l:
                item_perro = database.find_menu_item("Perro Caliente Especial", db_path=db_path)
                return f"Listo, agrego 1x Perro Caliente Especial a tu orden. Respecto a lo demás: ¿Te refieres a nuestra Pizza de peperonni o buscas empanadas? [AGREGAR: {item_perro['nombre']} | 1 | Ninguna]"
            return "Disculpa, no te entendí bien. ¿Te refieres a nuestra Pizza de peperonni o buscas empanadas?"
        if "bandeja de gaseosa" in msg_l:
            return "Disculpa, no te entendí bien. ¿Te refieres a pedir una Gaseosa 400ml o qué presentación buscas?"

        # 6. Agregar productos del menú (con mapeo semántico inteligente y orden de aparición)
        found_matches = []
        
        if "pizza" in msg_l:
            pos = msg_l.find("pizza")
            item_p = database.find_menu_item("Pizza de peperonni", db_path=db_path)
            if item_p:
                found_matches.append((pos, f"[AGREGAR: {item_p['nombre']} | 1 | Ninguna]", f"1x {item_p['nombre']}"))

        if "perro" in msg_l:
            pos = msg_l.find("perro")
            item_perro = database.find_menu_item("Perro Caliente Especial", db_path=db_path)
            if item_perro:
                notas = "sin queso" if "sin queso" in msg_l else "Ninguna"
                nota_txt = f" ({notas})" if notas != "Ninguna" else ""
                found_matches.append((pos, f"[AGREGAR: {item_perro['nombre']} | 1 | {notas}]", f"1x {item_perro['nombre']}{nota_txt}"))

        if "hamburguesa" in msg_l:
            pos = msg_l.find("hamburguesa")
            h_name = "Hamburguesa Doble Carne" if "doble" in msg_l else "Hamburguesa Clásica"
            item_h = database.find_menu_item(h_name, db_path=db_path)
            if item_h:
                qty = 1
                qty_m = re.search(r"(\d+)\s*(?:hamburguesa|de)", msg_l)
                if qty_m:
                    qty = int(qty_m.group(1))
                notas = "sin cebolla" if "sin cebolla" in msg_l else ("sin queso" if "sin queso" in msg_l else "Ninguna")
                nota_txt = f" ({notas})" if notas != "Ninguna" else ""
                found_matches.append((pos, f"[AGREGAR: {item_h['nombre']} | {qty} | {notas}]", f"{qty}x {item_h['nombre']}{nota_txt}"))

        if "papa" in msg_l and not ("tomate" in msg_l or "paquete" in msg_l):
            pos = msg_l.find("papa")
            item_papas = database.find_menu_item("Papas Francesas Grandes", db_path=db_path)
            if item_papas:
                found_matches.append((pos, f"[AGREGAR: {item_papas['nombre']} | 1 | Ninguna]", f"1x {item_papas['nombre']}"))

        if "gaseosa" in msg_l or "coca" in msg_l:
            pos = msg_l.find("gaseosa") if "gaseosa" in msg_l else msg_l.find("coca")
            item_g = database.find_menu_item("Gaseosa 400ml", db_path=db_path)
            if item_g:
                found_matches.append((pos, f"[AGREGAR: {item_g['nombre']} | 1 | Ninguna]", f"1x {item_g['nombre']}"))

        # Detectar si hay productos no disponibles (Pescados, bagre, chorizo, tilapia, salmón, empanadas, etc.)
        known_unavailable = ["chorizo", "bagre", "tilapia", "salmon", "salmón", "pescado", "mojarra", "camarones", "bocachico", "sancocho", "empanadas", "empanada", "sushi", "tacos", "taco", "arepas", "papas de tomate", "papas de paquete"]
        detected_unavail = None
        for unavail in known_unavailable:
            if unavail in msg_l:
                detected_unavail = unavail
                break

        # Combinación: Válidos + No disponibles
        if found_matches and detected_unavail:
            found_matches.sort(key=lambda x: x[0])
            tag_str = " ".join([m[1] for m in found_matches])
            desc_str = " y ".join([m[2] for m in found_matches])
            return f"Listo, agrego {desc_str} a tu orden. Por el momento no manejamos {detected_unavail}. ¿Deseas agregar algo más del menú? {tag_str}"

        # Solo No disponible
        if detected_unavail:
            return f"No amigo, {detected_unavail} no te manejamos por acá, solo comidas rápidas como hamburguesas, pizzas y perros calientes. ¿Te provoca algo de nuestro menú?"

        # 8. Flujo de Checkout / Finalizar / Dirección y Pago
        has_address = any(w in msg_l for w in ["calle", "cra", "carrera", "diagonal", "transversal", "av", "apto", "#"])
        detected_payment = "Efectivo" if "efectivo" in msg_l else ("Nequi" if "nequi" in msg_l else ("Transferencia" if "transferencia" in msg_l else ("Datáfono" if "datafono" in msg_l or "datáfono" in msg_l else None)))
        paga_con = "Paga con 50.000" if "50" in msg_l else "N/A"

        # Mensaje compuesto: Producto + Dirección + Pago
        if found_matches and has_address and detected_payment:
            found_matches.sort(key=lambda x: x[0])
            tag_add_str = " ".join([m[1] for m in found_matches])
            return f"Listo, tu pedido ha sido confirmado y está en preparación para ser enviado a {incoming_msg}. ¡Muchas gracias por tu compra! {tag_add_str} [NUEVO_PEDIDO: {incoming_msg} | {detected_payment} | {paga_con}]"

        if found_matches:
            found_matches.sort(key=lambda x: x[0])
            tag_str = " ".join([m[1] for m in found_matches])
            desc_str = " y ".join([m[2] for m in found_matches])
            return f"Listo, agrego {desc_str} a tu orden. ¿Deseas agregar algo más? {tag_str}"

        # 9. Ver carrito / Cuánto es
        if any(w in msg_l for w in ["mi pedido", "mi orden", "carrito", "cuanto es", "cuánto es", "la cuenta"]):
            return f"Hasta el momento tu pedido es este:\n\n{cart_display}\n\n¿Deseas agregar algo más o confirmamos el pedido?"

        # 10. Checkout directo
        if has_address and detected_payment:
            return f"Listo, tu pedido ha sido confirmado y está en preparación para ser enviado a {incoming_msg}. ¡Muchas gracias por tu compra! [NUEVO_PEDIDO: {incoming_msg} | {detected_payment} | {paga_con}]"

        if has_address:
            database.update_client_state(id_cliente=id_cliente, direccion=incoming_msg, db_path=db_path)
            return f"Excelente, anotada tu dirección ({incoming_msg}). ¿Qué método de pago usarás (Efectivo, Nequi, Transferencia o Datáfono)?"

        client_st = database.get_client_state(id_cliente, db_path)
        saved_dir = client_st.get("direccion")
        saved_metodo = client_st.get("metodo_pago")
        effective_payment = detected_payment or saved_metodo
        if effective_payment and saved_dir:
            if effective_payment == "Efectivo" and paga_con == "N/A" and not saved_metodo:
                database.update_client_state(id_cliente=id_cliente, metodo_pago="Efectivo", db_path=db_path)
                return "¿Con cuánto vas a cancelar para llevarte el cambio exacto?"
            return f"Listo, tu pedido ha sido confirmado y está en preparación para ser enviado a {saved_dir}. ¡Muchas gracias por tu compra! [NUEVO_PEDIDO: {saved_dir} | {effective_payment} | {paga_con}]"

        if any(w in msg_l for w in ["eso seria", "eso sería", "nada mas", "nada más", "eso es todo", "solo eso", "no mas", "no más", "ya", "confirmar"]):
            return f"Hasta el momento tu pedido es este:\n\n{cart_display}\n\nPor favor indícame tu dirección de entrega y qué método de pago usarás (Efectivo, Nequi, Transferencia o Datáfono)."

        # Fallback conversacional
        return "Hola, cuéntame en qué te podemos colaborar hoy con nuestro menú."

    # Compatibilidad con métodos de versiones previas para tests
    def generate_human_reply(self, *args, **kwargs) -> str:
        fallback = kwargs.get("fallback_reply", "Hola, ¿en qué te puedo colaborar hoy?")
        return fallback

    def _simulate_json_extraction(self, *args, **kwargs) -> Dict[str, Any]:
        return {"intencion": "pedir", "items_confirmados": []}

    def _process_extracted_json(self, *args, **kwargs) -> Tuple[str, None]:
        return "Hola, ¿en qué te puedo colaborar hoy?", None
