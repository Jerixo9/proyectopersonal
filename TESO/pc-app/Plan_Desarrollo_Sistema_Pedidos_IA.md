# Plan Detallado de Desarrollo: Sistema Automático de Toma de Pedidos con IA Local (Gemma3:4b)

Este documento detalla la arquitectura, bases de datos y fases de desarrollo para construir un sistema completo de toma de pedidos usando un teléfono Android (como puente) y una PC (como cerebro y servidor local).

---

## 1. Arquitectura Tecnológica Recomendada
*   **App Móvil (Cliente/Puente):** Kotlin/Java (Modificando el código fuente de Watomatic). Actúa únicamente como receptor/emisor de mensajes.
*   **Servidor/Backend (PC):** Python con **FastAPI** (rápido, ligero y excelente para recibir las peticiones del teléfono y emitir alertas a la interfaz).
*   **Base de Datos (PC):** **SQLite**. Ideal por ser un archivo local, rápido, fácil de monitorear y gestionar.
*   **Interfaz Gráfica (PC):** **CustomTkinter** o **PyQt5** para hacer una app de escritorio moderna en Python con soporte para alertas en tiempo real.
*   **IA Local:** **Ollama** corriendo el modelo `gemma3:4b`.

---

## 2. Fase 1: Simplificación de la App Móvil (Android)
El objetivo es transformar la app actual en un "transmisor/receptor" ciego y eficiente.

1.  **Limpieza de la Interfaz (UI):**
    *   Eliminar pestañas de estadísticas, donaciones e historial.
    *   Dejar solo: Interruptor de encendido/apagado, selector de aplicaciones (WhatsApp, WA Business) y campo de configuración para la **IP del PC** (ej. `http://192.168.1.X:5000/webhook`).
2.  **Modificación del Motor de Respuesta:**
    *   Quitar la lógica interna de respuestas y menús.
    *   El servicio de notificaciones tomará el mensaje entrante y el contacto, enviándolo por POST al PC. Quedará esperando la respuesta de texto para enviarla a WhatsApp.

---

## 3. Fase 2: Diseño de la Base de Datos (SQLite en PC)
Crearemos un archivo `pedidos.db` con tablas estructuradas para gestionar el negocio, el contexto y los pagos.

1.  **Tabla `Menu`**
    *   `id`, `nombre`, `precio`, `ingredientes`, `disponible` (Boolean).
2.  **Tabla `Metodos_Pago`**
    *   `id`, `nombre`, `activo` (Boolean), `pide_cambio` (Boolean - para saber si la IA debe preguntar con cuánto pagan).
    *   *Predeterminados:* Efectivo (activo=True, pide_cambio=True), Nequi, Transferencia Bancaria, Datáfono.
3.  **Tabla `Mensajes_Contexto`**
    *   `id`, `id_cliente` (Teléfono/Nombre), `rol` (usuario/asistente), `mensaje`, `fecha_hora`. *(Para mantener la memoria de cada chat separada).*
4.  **Tabla `Pedidos_Confirmados`**
    *   `id`, `id_cliente`, `resumen_pedido` (Ej: 1 Hamburguesa combo), `notas_especiales` (Ej: Sin pepinillos), `direccion`, `metodo_pago`, `cambio_de` (Ej: Billete de 50.000), `total`, `fecha_hora`, `estado` (Pendiente, Despachado).

---

## 4. Fase 3: Backend y Lógica de Inteligencia Artificial (Python)
El script en segundo plano que coordina la comunicación y el razonamiento.

1.  **Servidor Web (FastAPI):**
    *   Recibe los mensajes del móvil.
    *   Emite eventos (WebSockets) a la Interfaz Gráfica cuando hay una alerta de nuevo pedido.
2.  **Ingeniería del Prompt (Gemma3:4b):**
    *   El servidor inyecta dinámicamente el Menú (solo lo disponible) y los Métodos de Pago activos en el *System Prompt*.
    *   **Prompt Maestro:** *"Eres el recepcionista humano de un local de comida. Eres casual, amable y muy breve (sin parecer un robot). Tu objetivo es tomar el pedido. Cuando el cliente pida, confirma si desea algo más. Luego, pide la dirección de envío y cómo desea pagar (Opciones disponibles: [MÉTODOS_BD]). Si elige Efectivo, pregúntale con cuánto va a cancelar para llevarle el cambio. Cuando tengas TODOS los datos (pedido, notas, dirección y pago), despídete y escribe exactamente al final de tu mensaje este bloque: `[NUEVO_PEDIDO] | Producto y Notas | Dirección | Método de Pago | Cambio`."*
3.  **Parseo y Alertas:**
    *   FastAPI lee la respuesta de Ollama. Si detecta la etiqueta `[NUEVO_PEDIDO]`, extrae los datos, los guarda en `Pedidos_Confirmados` y dispara una **alerta visual y sonora** a la aplicación de PC. Se limpia el símbolo `[NUEVO_PEDIDO]` antes de enviar el texto al cliente por WhatsApp.

---

## 5. Fase 4: Desarrollo de la App Gráfica de PC (Dashboard)
App de escritorio con múltiples pestañas para la gestión total.

*   **⚡ Alertas en Tiempo Real (Pop-ups):**
    *   Independiente de la pestaña en la que estés, cuando se confirme un pedido saltará una alerta grande en pantalla (y un sonido) mostrando la información del cliente, el pedido con notas, la dirección y el método de pago (ej. paga con $50.000).
*   **Pestaña 1: Monitor de Pedidos:** Lista Kanban o tabla con los pedidos entrantes para marcarlos como "En preparación" o "Enviados".
*   **Pestaña 2: Gestor de Menú:** Botones para Agregar/Editar/Eliminar y un Toggle para marcar "Agotado/Disponible".
*   **Pestaña 3: Métodos de Pago:** Panel para activar/desactivar opciones (Nequi, Efectivo, Datáfono) y agregar nuevas.
*   **Pestaña 4: Almacenamiento y Limpieza:**
    *   Muestra el tamaño actual de la base de datos (Ej: `15 MB`).
    *   Botones de limpieza manual y dropdown para configuración automática de limpieza.
*   **🔍 Barra de Estado Inferior (Footer):**
    *   Ubicada en la parte inferior de la ventana, casi pegada a la barra de tareas.
    *   **Visor de IP Local:** Un texto que muestra la IP del PC (necesaria para la app de Android) acompañado de un **botón con el ícono de un ojo** para ocultar (mostrar asteriscos `***.***.*.*`) o revelar la IP.
    *   **Estado de Conexión:** Un indicador visual con una **luz verde (Conectado)** o **roja (Desconectado)** y un texto descriptivo, para saber si la app del teléfono se está comunicando correctamente con el servidor del PC en tiempo real (basado en 'ping' o 'heartbeat' desde el celular).

---

## 6. Pasos de Acción Sugeridos (Hoja de Ruta)

1.  **Configuración de IA Local:** Instalar Ollama y descargar el modelo `gemma3:4b`. Hacer pruebas en terminal.
2.  **Modificación Móvil:** Editar Watomatic en Android Studio para volverla un simple cliente HTTP (con sistema de "heartbeat" para el estado de conexión).
3.  **Base de Datos y Backend:** Crear el esquema en SQLite (Menú, Pagos, Contexto) e implementar el servidor FastAPI.
4.  **Integración y Parseo:** Escribir la lógica en Python que detecta cuando el pedido se ha cerrado.
5.  **Desarrollo UI PC:** Crear la interfaz gráfica (CustomTkinter/PyQt5), las alertas, las pestañas de configuración y la barra de estado con la IP y la luz de conexión.
