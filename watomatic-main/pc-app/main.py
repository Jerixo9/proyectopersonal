import sys
import os
import time
import argparse
import threading
import uvicorn

# Configurar encoding UTF-8 en consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Agregar el directorio raíz de pc-app al sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app as fastapi_app
from backend.database import init_db
from backend.network_utils import get_local_ip

def run_fastapi_server(host: str = "0.0.0.0", port: int = 8000):
    """Inicia el servidor FastAPI con uvicorn en segundo plano."""
    config = uvicorn.Config(
        app=fastapi_app,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

def main():
    parser = argparse.ArgumentParser(description="Sistema Automático de Toma de Pedidos con IA Local")
    parser.add_argument("--port", type=int, default=8000, help="Puerto para el servidor FastAPI (por defecto: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host de escucha (por defecto: 0.0.0.0)")
    parser.add_argument("--no-gui", action="store_true", help="Ejecutar únicamente el servidor backend en modo consola (sin GUI)")
    args = parser.parse_args()

    # Inicializar Base de Datos
    init_db()

    local_ip = get_local_ip()
    print("=" * 65)
    print("🚀 TESO - SISTEMA AUTOMÁTICO DE PEDIDOS CON IA")
    print(f"📡 Servidor Activo en: http://{local_ip}:{args.port}")
    print(f"🔗 Webhook para Android: http://{local_ip}:{args.port}/api/webhook")
    print(f"💓 Heartbeat Endpoint: http://{local_ip}:{args.port}/api/heartbeat")
    print("=" * 65)

    # Iniciar FastAPI en un hilo en segundo plano
    server_thread = threading.Thread(
        target=run_fastapi_server,
        kwargs={"host": args.host, "port": args.port},
        daemon=True
    )
    server_thread.start()

    # Si se solicitó modo sin GUI (consola)
    if args.no_gui:
        print("🖥️ Servidor corriendo en modo headless (Consola). Presiona Ctrl+C para detener.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Servidor detenido.")
            sys.exit(0)
    else:
        # Iniciar Interfaz Gráfica CustomTkinter
        from gui.app_window import MainWindow
        app_gui = MainWindow(port=args.port)
        app_gui.mainloop()

if __name__ == "__main__":
    main()
