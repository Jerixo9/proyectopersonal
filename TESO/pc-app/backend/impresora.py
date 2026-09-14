import os
import datetime
import traceback

# Creamos una carpeta para guardar las facturas si no existe
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKETS_DIR = os.path.join(BASE_DIR, "facturas")
if not os.path.exists(TICKETS_DIR):
    os.makedirs(TICKETS_DIR)

def imprimir_ticket_simulado(id_pedido: int, id_cliente: str, resumen_items: str, notas_especiales: str, direccion: str, metodo_pago: str, cambio_de: str, total: float):
    """
    Genera un archivo de texto con formato de ticket de 80mm y lo abre en pantalla.
    """
    fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # 1. Damos formato visual al ticket (Ancho típico de impresora térmica)
    ticket_texto = f"""
================================
         RESTAURANTE OTTO
       Ticket de Preparacion
================================
Fecha: {fecha_actual}
Pedido #: {id_pedido}
Cliente: {id_cliente}
--------------------------------
PRODUCTOS:
{resumen_items.replace(', ', '\n')}
"""
    if notas_especiales and str(notas_especiales).strip().lower() != "ninguna":
        ticket_texto += f"""--------------------------------
NOTAS ESPECIALES:
{notas_especiales.replace('; ', '\n')}
"""

    ticket_texto += f"""--------------------------------
TOTAL A PAGAR: ${total:,.0f} COP
MEDIO DE PAGO: {metodo_pago}
CAMBIO DE: {cambio_de}
DIRECCION: {direccion}
================================
      *** FIN DE PEDIDO ***
"""

    # 2. Guardamos el archivo .txt
    nombre_archivo = f"ticket_{id_pedido}.txt"
    ruta_archivo = os.path.join(TICKETS_DIR, nombre_archivo)
    
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write(ticket_texto)

    # 3. EL SIMULADOR: Hacemos que Windows abra el archivo automáticamente (como si saliera papel)
    try:
        os.startfile(os.path.abspath(ruta_archivo))
        print(f"\n[IMPRESORA] Ticket #{id_pedido} generado en pantalla en {ruta_archivo}.")
    except Exception as e:
        print(f"[IMPRESORA] Error al simular impresión: {e}")
        traceback.print_exc()
