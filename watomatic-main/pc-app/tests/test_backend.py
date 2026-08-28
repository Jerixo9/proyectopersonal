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

