import unittest
import os
import tempfile
import sys

# Agregar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from backend import database
from backend import network_utils
from backend.ai_service import AIService
from fastapi.testclient import TestClient
from backend.app import app, is_phone_connected, heartbeat_state, ai_engine

class TestSistemaPedidos(unittest.TestCase):
    def setUp(self):
        # Crear base de datos temporal
        temp_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_fd)
        database.init_db(self.temp_db_path)
        self.ai = AIService()
        self.ai.simulation_mode = True
        ai_engine.simulation_mode = True

    def tearDown(self):
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_database_initialization(self):
        menu = database.get_all_menu(self.temp_db_path)
        self.assertGreater(len(menu), 0)
        
        payments = database.get_all_payment_methods(self.temp_db_path)
        self.assertGreater(len(payments), 0)
        
        categories = database.get_all_categories(self.temp_db_path)
        self.assertGreater(len(categories), 0)
        self.assertTrue(any(c["nombre"] == "Hamburguesas" for c in categories))
        
        # Verificar Efectivo pide_cambio = 1
        efectivo = next((p for p in payments if p["nombre"] == "Efectivo"), None)
        self.assertIsNotNone(efectivo)
        self.assertEqual(efectivo["pide_cambio"], 1)

    def test_categories_crud(self):
        # 1. Agregar categoría
        cat_id = database.add_category("Postres Gourmet", self.temp_db_path)
        self.assertGreater(cat_id, 0)
        
        # 2. Agregar plato en esa categoría
        item_id = database.add_menu_item("Brownie con Helado", 12000, "Chocolate y vainilla", "Postres Gourmet", True, self.temp_db_path)
        self.assertGreater(item_id, 0)
        
        # 3. Actualizar nombre de categoría y verificar que el plato se actualice
        database.update_category(cat_id, "Dulces y Postres", self.temp_db_path)
        item = next(m for m in database.get_all_menu(self.temp_db_path) if m["id"] == item_id)
        self.assertEqual(item["categoria"], "Dulces y Postres")
        
        # 4. Eliminar categoría y verificar reasignación a 'General'
        database.delete_category(cat_id, self.temp_db_path)
        item_after = next(m for m in database.get_all_menu(self.temp_db_path) if m["id"] == item_id)
        self.assertEqual(item_after["categoria"], "General")

    def test_menu_crud(self):
        item_id = database.add_menu_item("Pizza Personal", 14000, "Queso y pepperoni", "Pizzas", True, self.temp_db_path)
        self.assertGreater(item_id, 0)
        
        database.toggle_menu_availability(item_id, db_path=self.temp_db_path)
        avail_menu = database.get_available_menu(self.temp_db_path)
        self.assertFalse(any(m["id"] == item_id for m in avail_menu))
        
        deleted = database.delete_menu_item(item_id, self.temp_db_path)
        self.assertTrue(deleted)

    def test_payment_crud(self):
        pid = database.add_payment_method("Daviplata", True, False, self.temp_db_path)
        self.assertGreater(pid, 0)
        
        database.toggle_payment_active(pid, self.temp_db_path)
        active_payments = database.get_active_payment_methods(self.temp_db_path)
        self.assertFalse(any(p["id"] == pid for p in active_payments))

    def test_cart_operations_and_math(self):
        client_id = "573001234567"
        
        # 1. Carrito vacío inicialmente
        summary, total, items = database.get_cart_summary_and_total(client_id, self.temp_db_path)
        self.assertEqual(total, 0.0)
        self.assertEqual(len(items), 0)
        
        # 2. Agregar 2 Hamburguesas Clásicas ($18,000 c/u = $36,000)
        ok1 = database.add_to_cart(client_id, "Hamburguesa Clásica", 2, db_path=self.temp_db_path)
        self.assertTrue(ok1)
        
        # 3. Agregar 1 Papas Francesas Grandes ($9,000)
        ok2 = database.add_to_cart(client_id, "papas francesas", 1, db_path=self.temp_db_path)
        self.assertTrue(ok2)
        
        summary, total, items = database.get_cart_summary_and_total(client_id, self.temp_db_path)
        self.assertEqual(len(items), 2)
        self.assertEqual(total, 45000.0)
        self.assertIn("Hamburguesa Clásica", summary)
        self.assertIn("Papas Francesas Grandes", summary)
        
        # 4. Incrementar cantidad de Hamburguesas (+1 -> 3 total = $54,000 + $9,000 = $63,000)
        database.add_to_cart(client_id, "Hamburguesa Clásica", 1, db_path=self.temp_db_path)
        _, total_inc, _ = database.get_cart_summary_and_total(client_id, self.temp_db_path)
        self.assertEqual(total_inc, 63000.0)
        
        # 5. Quitar 1 Hamburguesa (queda 2 -> total = $45,000)
        ok_rem1 = database.remove_from_cart(client_id, "Hamburguesa Clásica", 1, db_path=self.temp_db_path)
        self.assertTrue(ok_rem1)
        _, total_rem, _ = database.get_cart_summary_and_total(client_id, self.temp_db_path)
        self.assertEqual(total_rem, 45000.0)
        
        # 6. Quitar Papas por completo
        ok_rem2 = database.remove_from_cart(client_id, "Papas Francesas Grandes", None, db_path=self.temp_db_path)
        self.assertTrue(ok_rem2)
        _, total_after_papas, items_after_papas = database.get_cart_summary_and_total(client_id, self.temp_db_path)
        self.assertEqual(len(items_after_papas), 1)
        self.assertEqual(total_after_papas, 36000.0)
        
        # 7. Vaciar carrito
        cleared = database.clear_cart(client_id, self.temp_db_path)
        self.assertEqual(cleared, 1)
        _, total_empty, items_empty = database.get_cart_summary_and_total(client_id, self.temp_db_path)
        self.assertEqual(total_empty, 0.0)
        self.assertEqual(len(items_empty), 0)

    def test_ai_system_prompt_building(self):
        prompt = self.ai.build_system_prompt(id_cliente="573001234567", db_path=self.temp_db_path)
        
        # Verificar secciones del prompt autónomo
        self.assertIn("Eres quien atiende el WhatsApp de nuestro restaurante", prompt)
        self.assertIn("MENÚ DEL LOCAL:", prompt)
        self.assertIn("ESTADO DEL PEDIDO DEL CLIENTE:", prompt)
        self.assertIn("REGLAS DE ATENCIÓN:", prompt)
        self.assertIn("SISTEMA DE ETIQUETAS", prompt)
        self.assertIn("[AGREGAR:", prompt)
        self.assertIn("[QUITAR:", prompt)
        self.assertIn("[NUEVO_PEDIDO:", prompt)
        
        # Verificar inyección de productos del menú
        self.assertIn("Hamburguesa Clásica", prompt)
        self.assertIn("Papas Francesas Grandes", prompt)

    def test_chorizo_and_unavailable_food_handling(self):
        client_id = "57311993355"
        reply, order = self.ai.process_incoming_message(
            client_id,
            "me das un chorizo porfavor",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order)
        self.assertTrue("chorizo" in reply and ("no te manejamos" in reply or "no manejamos" in reply))
        self.assertNotIn("anotada tu dirección", reply)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_informal_compound_order_mapping(self):
        client_id = "57300998877"
        reply, order = self.ai.process_incoming_message(
            client_id,
            "unas papas y un perro sin queso",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order)
        self.assertIn("Papas Francesas Grandes", reply)
        self.assertIn("Perro Caliente Especial", reply)
        
        cart_items = database.get_cart(client_id, self.temp_db_path)
        self.assertEqual(len(cart_items), 2)
        names = [it["nombre_producto"] for it in cart_items]
        self.assertIn("Papas Francesas Grandes", names)
        self.assertIn("Perro Caliente Especial", names)

    def test_casual_chat_and_bocachico_natural_flow(self):
        client_id = "57311445566"
        
        # 1. Charla casual ("hola, ¿cómo te fue hoy?")
        reply1, order1 = self.ai.process_incoming_message(
            client_id,
            "hola, ¿cómo te fue hoy?",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order1)
        self.assertIn("Hola", reply1)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

        # 2. Pide producto fuera de carta como bocachico
        reply2, order2 = self.ai.process_incoming_message(
            client_id,
            "tienen bocachico frito?",
            db_path=self.temp_db_path
        )
        self.assertTrue("bocachico" in reply2 and ("no te manejamos" in reply2 or "no manejamos" in reply2))
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_salmon_and_identity_question(self):
        client_id = "57322334455"
        
        # 1. Pregunta sobre quién es el interlocutor ("¿quién eres?")
        reply_id, order_id = self.ai.process_incoming_message(
            client_id,
            "¿quién eres?",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order_id)
        self.assertIn("encargado de tomar los pedidos", reply_id)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

        # 2. Pide salmón ahumado (producto no existente)
        reply_sal, order_sal = self.ai.process_incoming_message(
            client_id,
            "quiero un salmón ahumado",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order_sal)
        self.assertTrue("salmón" in reply_sal or "salmon" in reply_sal)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_ambiguous_items_clarification_handling(self):
        client_id = "57311776655"
        
        # 1. Combinación absurda / ambigua ("sancocho de hamburguesa")
        reply1, order1 = self.ai.process_incoming_message(
            client_id,
            "Quiero un sancocho de hamburguesa",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order1)
        self.assertIn("Disculpa, no te entendí bien.", reply1)
        self.assertIn("¿Te refieres a nuestra Hamburguesa Clásica o buscas sancocho?", reply1)
        # El carrito debe permanecer limpio (0 items)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

        # 2. Ítem válido + combinación ambigua ("1 Perro Caliente Especial y una empanada de pizza")
        reply2, order2 = self.ai.process_incoming_message(
            client_id,
            "Quiero 1 Perro Caliente Especial y una empanada de pizza",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order2)
        self.assertIn("Listo, agrego 1x Perro Caliente Especial a tu orden.", reply2)
        self.assertIn("Respecto a lo demás:", reply2)
        self.assertIn("¿Te refieres a nuestra Pizza de peperonni o buscas empanadas?", reply2)
        # Solo se agrega el perro caliente
        cart_items = database.get_cart(client_id, self.temp_db_path)
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0]["nombre_producto"], "Perro Caliente Especial")

        # 3. Presentación no convencional ("bandeja de gaseosa")
        client_id2 = "57311776699"
        reply3, order3 = self.ai.process_incoming_message(
            client_id2,
            "Tráeme una bandeja de gaseosa",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order3)
        self.assertIn("Disculpa, no te entendí bien.", reply3)
        self.assertIn("Gaseosa", reply3)
        self.assertEqual(len(database.get_cart(client_id2, self.temp_db_path)), 0)

    def test_negation_rejection_and_incompatible_variants(self):
        client_id = "57311882233"
        
        # 1. Rechazo de sugerencia con variante incompatible ("no unas papas de tomate")
        reply1, order1 = self.ai.process_incoming_message(
            client_id,
            "no unas papas de tomate",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order1)
        self.assertTrue("papas de tomate" in reply1 and ("no te manejamos" in reply1 or "no manejamos" in reply1))
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

        # 2. Petición explícita de variante incompatible ("no, quiero unas papas de paquete")
        client_id2 = "57311882244"
        reply2, order2 = self.ai.process_incoming_message(
            client_id2,
            "no, quiero unas papas de paquete",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order2)
        self.assertTrue("papas de paquete" in reply2 and ("no te manejamos" in reply2 or "no manejamos" in reply2))
        self.assertEqual(len(database.get_cart(client_id2, self.temp_db_path)), 0)

    def test_unavailable_product_handling_and_no_cart_loop(self):
        client_id = "57311559988"
        
        # 1. El cliente pide un producto que no existe en el menú
        reply1, order1 = self.ai.process_incoming_message(
            client_id,
            "Quiero pedir 2 empanadas",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order1)
        self.assertTrue("empanadas" in reply1 and ("no te manejamos" in reply1 or "no manejamos" in reply1))
        self.assertNotIn("Total a pagar:", reply1)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

        # 2. El cliente pide un producto válido Y un producto no disponible en la misma frase
        reply2, order2 = self.ai.process_incoming_message(
            client_id,
            "Quiero 1 Hamburguesa Clásica y 2 empanadas",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order2)
        self.assertIn("Listo, agrego 1x Hamburguesa Clásica a tu orden. Por el momento no manejamos empanadas. ¿Deseas agregar algo más del menú?", reply2)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 1)

        # 3. El cliente pregunta por la empanada ignorada ("¿y mi empanada?")
        reply3, order3 = self.ai.process_incoming_message(
            client_id,
            "¿y mi empanada?",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order3)
        self.assertTrue("empanada" in reply3 and ("no te manejamos" in reply3 or "no manejamos" in reply3))
        self.assertNotIn("Total a pagar:", reply3)
        # El carrito previo (la hamburguesa) se mantiene intacto
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 1)

    def test_tilapia_and_unavailable_food_handling(self):
        client_id = "57311993344"
        
        # 1. El cliente pide tilapia frita tras el menú
        reply_tilapia, order_tilapia = self.ai.process_incoming_message(
            client_id,
            "quiero una tilapia frita",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order_tilapia)
        self.assertTrue("tilapia" in reply_tilapia and ("no te manejamos" in reply_tilapia or "no manejamos" in reply_tilapia))
        self.assertNotIn("Hola. ¿En qué te puedo colaborar hoy?", reply_tilapia)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_fast_rules_routing_greetings_menu_and_cart(self):
        client_id = "573112233445"
        
        # 1. Saludo simple
        reply_greet, order_greet = self.ai.process_incoming_message(client_id, "Hola", db_path=self.temp_db_path)
        self.assertEqual(reply_greet, "Hola. ¿En qué te puedo colaborar hoy?")
        self.assertIsNone(order_greet)

        reply_greet2, _ = self.ai.process_incoming_message(client_id, "Buenos días", db_path=self.temp_db_path)
        self.assertEqual(reply_greet2, "Hola. ¿En qué te puedo colaborar hoy?")

        # 2. Petición de menú
        reply_menu, order_menu = self.ai.process_incoming_message(client_id, "menú", db_path=self.temp_db_path)
        self.assertIn("Claro, aquí tienes nuestro menú:", reply_menu)
        self.assertIn("HAMBURGUESAS", reply_menu)
        self.assertIn("Hamburguesa Clásica: $18,000 COP", reply_menu)
        self.assertIn("¿Qué te gustaría ordenar?", reply_menu)
        self.assertIsNone(order_menu)

        reply_menu2, _ = self.ai.process_incoming_message(client_id, "¿Qué tienen para comer?", db_path=self.temp_db_path)
        self.assertIn("Claro, aquí tienes nuestro menú:", reply_menu2)

        # 3. Consulta de carrito
        database.add_to_cart(client_id, "Hamburguesa Clásica", 1, notas="Sin cebolla", db_path=self.temp_db_path)
        reply_cart, order_cart = self.ai.process_incoming_message(client_id, "mi pedido", db_path=self.temp_db_path)
        self.assertIn("Hasta el momento tu pedido es este:", reply_cart)
        self.assertIn("1x Hamburguesa Clásica (Sin cebolla)", reply_cart)
        self.assertIn("Total a pagar: $18,000 COP", reply_cart)
        self.assertIn("¿Deseas agregar algo más o confirmamos el pedido?", reply_cart)
        self.assertIsNone(order_cart)

        reply_cart2, _ = self.ai.process_incoming_message(client_id, "¿Cuánto es?", db_path=self.temp_db_path)
        self.assertIn("Hasta el momento tu pedido es este:", reply_cart2)
        self.assertIn("$18,000 COP", reply_cart2)

    def test_session_inactivity_expiration_2_hours(self):
        client_id = "57388877766"
        database.add_to_cart(client_id, "Hamburguesa Clásica", 1, db_path=self.temp_db_path)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 1)

        # Simular inactividad de más de 2 horas (3 horas atrás)
        old_time = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        with database.get_connection(self.temp_db_path) as conn:
            conn.cursor().execute("UPDATE Carrito_Temporal SET ultima_actividad = ? WHERE id_cliente = ?", (old_time, client_id))
            conn.commit()

        # Al recibir un nuevo mensaje, la sesión expirada debe limpiarse automáticamente
        expired = database.check_and_expire_session(client_id, "Hola", db_path=self.temp_db_path)
        self.assertTrue(expired)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_reset_client_session_clears_cart_and_messages(self):
        client_id = "57399911122"
        database.add_to_cart(client_id, "Hamburguesa Clásica", 2, notas="Sin cebolla", db_path=self.temp_db_path)
        database.save_chat_message(client_id, "user", "Hola, quiero pedir", self.temp_db_path)
        database.save_chat_message(client_id, "assistant", "Listo, ¿algo más?", self.temp_db_path)
        
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 1)
        self.assertEqual(len(database.get_chat_history(client_id, limit=10, db_path=self.temp_db_path)), 2)
        
        deleted_cart, deleted_msgs = database.reset_client_session(client_id, self.temp_db_path)
        self.assertEqual(deleted_cart, 1)
        self.assertEqual(deleted_msgs, 2)
        
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)
        self.assertEqual(len(database.get_chat_history(client_id, limit=10, db_path=self.temp_db_path)), 0)
        
        # Flujo con comando "reiniciar"
        database.add_to_cart(client_id, "Papas Francesas Grandes", 1, db_path=self.temp_db_path)
        reply, order = self.ai.process_incoming_message(client_id, "reiniciar", db_path=self.temp_db_path)
        self.assertIn("reiniciados correctamente", reply)
        self.assertIsNone(order)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_multi_item_order_in_single_message_with_notes(self):
        client_id = "57311990011"
        
        # Pedir 2 productos con notas
        reply, order = self.ai.process_incoming_message(
            client_id,
            "Quiero ordenar 2 Hamburguesas Clásicas sin queso y 1 Papas Francesas Grandes",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order)
        self.assertIn("2x Hamburguesa Clásica", reply)
        self.assertIn("1x Papas Francesas Grandes", reply)
        
        # Verificar almacenamiento en SQLite
        cart_items = database.get_cart(client_id, self.temp_db_path)
        self.assertEqual(len(cart_items), 2)
        hamburguesa = next(it for it in cart_items if it["nombre_producto"] == "Hamburguesa Clásica")
        papas = next(it for it in cart_items if it["nombre_producto"] == "Papas Francesas Grandes")
        self.assertEqual(hamburguesa["cantidad"], 2)
        self.assertEqual(papas["cantidad"], 1)

    def test_remove_item_from_cart_flow(self):
        client_id = "57311990022"
        database.add_to_cart(client_id, "Hamburguesa Clásica", 2, db_path=self.temp_db_path)
        database.add_to_cart(client_id, "Papas Francesas Grandes", 1, db_path=self.temp_db_path)
        
        reply, order = self.ai.process_incoming_message(
            client_id,
            "Quita 1 Hamburguesa Clásica de mi pedido",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order)
        self.assertIn("retirado", reply.lower())
        
        cart_items = database.get_cart(client_id, self.temp_db_path)
        hamburguesa = next(it for it in cart_items if it["nombre_producto"] == "Hamburguesa Clásica")
        self.assertEqual(hamburguesa["cantidad"], 1)

    def test_direct_action_tag_processing(self):
        client_id = "57311990033"
        # 1. Agregar con etiquetas directas de la IA
        raw_add = "Listo, agrego 2x Hamburguesa Clásica (sin cebolla) y 1x Papas Francesas Grandes a tu orden. ¿Deseas algo más? [AGREGAR: Hamburguesa Clásica | 2 | sin cebolla] [AGREGAR: Papas Francesas Grandes | 1 | Ninguna]"
        order_add = self.ai._process_action_tags(raw_add, client_id, db_path=self.temp_db_path)
        clean_add = self.ai.clean_reply_text(raw_add)
        self.assertIsNone(order_add)
        self.assertNotIn("[AGREGAR:", clean_add)
        self.assertIn("Listo, agrego 2x Hamburguesa Clásica", clean_add)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 2)

        # 2. Quitar con etiquetas directas
        raw_rem = "Listo, he retirado 1 Papas Francesas Grandes de tu orden. [QUITAR: Papas Francesas Grandes | 1]"
        order_rem = self.ai._process_action_tags(raw_rem, client_id, db_path=self.temp_db_path)
        clean_rem = self.ai.clean_reply_text(raw_rem)
        self.assertIsNone(order_rem)
        self.assertNotIn("[QUITAR:", clean_rem)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 1)

        # 3. Finalizar y crear pedido con etiquetas directas
        raw_fin = "Listo, tu pedido ha sido confirmado. [NUEVO_PEDIDO: Carrera 7 # 45-10 Apto 201 | Nequi | N/A]"
        order_fin = self.ai._process_action_tags(raw_fin, client_id, db_path=self.temp_db_path)
        clean_fin = self.ai.clean_reply_text(raw_fin)
        self.assertIsNotNone(order_fin)
        self.assertNotIn("[NUEVO_PEDIDO:", clean_fin)
        self.assertEqual(order_fin["direccion"], "Carrera 7 # 45-10 Apto 201")
        self.assertEqual(order_fin["metodo_pago"], "Nequi")
        self.assertEqual(order_fin["total"], 36000.0)
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)

    def test_network_utils(self):
        ip = network_utils.get_local_ip()
        self.assertTrue(len(ip) > 0)
        masked = network_utils.mask_ip(f"{ip}:8000")
        self.assertIn("***", masked)
        self.assertTrue(masked.endswith(":8000"))

    def test_storage_purge_and_vacuum(self):
        database.save_chat_message("3001112233", "user", "Hola", self.temp_db_path)
        database.save_chat_message("3001112233", "assistant", "Hola, te ayudo?", self.temp_db_path)
        
        stats = database.get_storage_stats(self.temp_db_path)
        self.assertEqual(stats["total_mensajes"], 2)
        
        purged = database.purge_chat_messages(days_older_than=0, db_path=self.temp_db_path)
        self.assertEqual(purged, 2)
        
        stats_after = database.get_storage_stats(self.temp_db_path)
        self.assertEqual(stats_after["total_mensajes"], 0)

    def test_full_flow_cart_and_order_confirmation_with_notes(self):
        client_id = "3158889900"
        
        # Mensaje 1: Agregar producto (confirmación corta)
        reply1, order1 = self.ai.process_incoming_message(
            client_id,
            "Quiero ordenar 2 Hamburguesas Clásicas sin cebolla",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order1)
        self.assertIn("Listo, agrego 2x Hamburguesa Clásica (sin cebolla) a tu orden. ¿Deseas agregar algo más?", reply1)
        
        # Verificar que el carrito en SQLite tenga las 2 hamburguesas
        cart_items = database.get_cart(client_id, self.temp_db_path)
        self.assertEqual(len(cart_items), 1)
        self.assertEqual(cart_items[0]["cantidad"], 2)
        self.assertEqual(cart_items[0]["precio_unitario"], 18000.0)

        # Mensaje 2: Confirmar y cerrar pedido en un solo turno con dirección y pago
        reply2, order2 = self.ai.process_incoming_message(
            client_id,
            "Por favor enviar a Calle 45 # 10-20, pago en efectivo con 50000",
            db_path=self.temp_db_path
        )
        self.assertIsNotNone(order2)
        self.assertIn("Listo, tu pedido ha sido confirmado", reply2)
        self.assertEqual(order2["total"], 36000.0)
        self.assertIn("Hamburguesa Clásica", order2["resumen_pedido"])
        self.assertIn("sin cebolla", order2["notas_especiales"])
        
        # Verificar que el carrito temporal fue vaciado después de confirmar
        cart_after = database.get_cart(client_id, self.temp_db_path)
        self.assertEqual(len(cart_after), 0)

    def test_step_by_step_checkout_state_machine_with_sqlite_memory(self):
        client_id = "3179988112"
        
        # Turno 1: Pedir múltiples productos compuestos
        reply1, order1 = self.ai.process_incoming_message(
            client_id,
            "Quiero una pizza de peperonni y un perro caliente especial sin queso",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order1)
        self.assertTrue("Pizza de peperonni" in reply1 and "Perro Caliente Especial" in reply1)
        
        # Turno 2: El cliente dice "eso seria todo" (Finalizar checkout paso 1)
        reply2, order2 = self.ai.process_incoming_message(
            client_id,
            "Eso sería todo",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order2)
        self.assertIn("Hasta el momento tu pedido es este:", reply2)
        self.assertIn("Total a pagar: $36,000 COP", reply2)
        self.assertIn("Por favor indícame tu dirección de entrega y qué método de pago usarás", reply2)
        
        # Turno 3: El cliente envía solo la dirección
        reply3, order3 = self.ai.process_incoming_message(
            client_id,
            "Calle 15 # 8-30 Apto 402",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order3)
        self.assertIn("Excelente, anotada tu dirección (Calle 15 # 8-30 Apto 402). ¿Qué método de pago usarás", reply3)
        
        # Turno 4: El cliente envía solo el método de pago ("Efectivo")
        reply4, order4 = self.ai.process_incoming_message(
            client_id,
            "Efectivo",
            db_path=self.temp_db_path
        )
        self.assertIsNone(order4)
        self.assertIn("¿Con cuánto vas a cancelar para llevarte el cambio exacto?", reply4)
        
        # Turno 5: El cliente envía con cuánto paga
        reply5, order5 = self.ai.process_incoming_message(
            client_id,
            "Pago con 50.000",
            db_path=self.temp_db_path
        )
        self.assertIsNotNone(order5)
        self.assertIn("Listo, tu pedido ha sido confirmado y está en preparación para ser enviado a Calle 15 # 8-30 Apto 402. ¡Muchas gracias por tu compra!", reply5)
        self.assertEqual(order5["total"], 36000.0)
        self.assertEqual(order5["metodo_pago"], "Efectivo")
        self.assertEqual(order5["cambio_de"], "Paga con 50.000")
        
        # Verificar limpieza de SQLite
        self.assertEqual(len(database.get_cart(client_id, self.temp_db_path)), 0)
        self.assertIsNone(database.get_client_state(client_id, self.temp_db_path)["direccion"])

    def test_fastapi_endpoints_including_categories(self):
        client = TestClient(app)
        
        # 1. Root
        r_root = client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertEqual(r_root.json()["status"], "online")
        
        # 2. Categories
        r_cats = client.get("/api/categories")
        self.assertEqual(r_cats.status_code, 200)
        self.assertGreater(len(r_cats.json()), 0)

        r_new_cat = client.post("/api/categories", json={"nombre": "Bebidas Especiales"})
        self.assertEqual(r_new_cat.status_code, 200)
        cat_id = r_new_cat.json()["id"]

        r_up_cat = client.put(f"/api/categories/{cat_id}", json={"nombre": "Bebidas Premium"})
        self.assertEqual(r_up_cat.status_code, 200)

        r_del_cat = client.delete(f"/api/categories/{cat_id}")
        self.assertEqual(r_del_cat.status_code, 200)

        # 3. Heartbeat
        r_hb = client.post("/api/heartbeat", json={"device_name": "Test Xiaomi", "package": "com.whatsapp"})
        self.assertEqual(r_hb.status_code, 200)
        self.assertTrue(is_phone_connected())
        
        # 4. Webhook - Mensaje inicial
        r_wh1 = client.post("/api/webhook", json={"sender": "3109998877", "message": "Hola, qué tienen en el menú?"})
        self.assertEqual(r_wh1.status_code, 200)
        self.assertIn("reply", r_wh1.json())
        self.assertFalse(r_wh1.json()["order_created"])

        # 5. Webhook - Cierre de pedido
        r_wh2 = client.post(
            "/api/webhook",
            json={"sender": "3109998877", "message": "Por favor una Hamburguesa Clásica a la Calle 100 # 15-20, pago en efectivo con 50000"}
        )
        self.assertEqual(r_wh2.status_code, 200)
        data2 = r_wh2.json()
        self.assertTrue(data2["order_created"])
        self.assertIsNotNone(data2["order"])
        self.assertEqual(data2["order"]["metodo_pago"], "Efectivo")
        
        # 6. Orders list
        r_orders = client.get("/api/orders")
        self.assertEqual(r_orders.status_code, 200)
        self.assertGreater(len(r_orders.json()), 0)

if __name__ == "__main__":
    unittest.main()

