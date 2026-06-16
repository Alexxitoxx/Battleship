import pygame
import sys
import random
import os
import threading
import asyncio
import queue
import json

import websockets

# ── Importar agentes (mismo directorio) ─────────────────────
from simple_agent       import AgenteSimple
from reactive_agent     import AgenteReactivo
from deliberative_agent import AgenteDeliberativo

pygame.init()

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN VENTANA
# ─────────────────────────────────────────────────────────────
ANCHO, ALTO = 800, 640
VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Battleship")
FPS = 60
clock = pygame.time.Clock()

# ─────────────────────────────────────────────────────────────
# COLORES
# ─────────────────────────────────────────────────────────────
BG            = (30, 30, 50)
BLANCO        = (255, 220, 80)
AZUL          = (52, 152, 219)
ROJO          = (231, 76, 60)
GRIS          = (200, 200, 200)
OSC           = (46, 59, 78)
VERDE         = (255, 186, 94)
BTN_PRIMARIO  = (242, 156, 34)
BTN_HOVER     = (226, 133, 12)
BTN_BORDE     = (74, 42, 0)
BTN_TEXTO     = (33, 19, 2)
UI_CAJA       = (43, 32, 20)
UI_BORDE_ACTIVO = (255, 202, 125)
AGUA_COLOR    = (44, 123, 168)
BARCO_COLOR   = (30, 80, 130)      # color de mis barcos en tablero propio
GRID_COLOR    = (87, 168, 196)
EJE_HUD       = (178, 235, 251)
TITULO_HUD    = (201, 245, 255)
COLOR_MI_TURNO    = (80, 220, 80)
COLOR_TURNO_OTRO  = (180, 180, 180)
COLOR_GANADOR     = (255, 215, 0)
COLOR_PERDEDOR    = (200, 60, 60)

# ─────────────────────────────────────────────────────────────
# ESTADOS
# ─────────────────────────────────────────────────────────────
MENU          = "menu"
JUEGO         = "juego"
CONECTAR      = "conectar"
AJUSTES       = "ajustes"
CONFIG_PARTIDA = "config_partida"
estado        = MENU

# ─────────────────────────────────────────────────────────────
# TABLERO
# ─────────────────────────────────────────────────────────────
TAM   = 10
CELDA = 30

tablero_jugador  = [["" for _ in range(TAM)] for _ in range(TAM)]
tablero_enemigo  = [["" for _ in range(TAM)] for _ in range(TAM)]
tableros_partida = [tablero_jugador, tablero_enemigo]
zonas_tableros   = []
jugadores_actuales       = 2
indice_tablero_objetivo  = 1

# Barcos fijos para auto-colocar (mismo que --auto en client.py)
BARCOS_AUTO = [
    (4, 0, 0, True),
    (3, 2, 0, True),
    (3, 4, 0, True),
    (2, 6, 0, True),
    (2, 8, 0, True),
]

# ─────────────────────────────────────────────────────────────
# FUENTES
# ─────────────────────────────────────────────────────────────
fuente        = pygame.font.SysFont("Trebuchet MS", 24)
fuente_titulo = pygame.font.SysFont("Trebuchet MS", 52, bold=True)
fuente_panel  = pygame.font.SysFont("Trebuchet MS", 30, bold=True)
fuente_ejes   = pygame.font.SysFont("Trebuchet MS", 14, bold=True)
fuente_hud    = pygame.font.SysFont("Trebuchet MS", 16, bold=True)

# ─────────────────────────────────────────────────────────────
# ENTRADA DE IP
# ─────────────────────────────────────────────────────────────
ip_servidor    = "10.100.91.112"
ip_confirmada  = "10.100.91.112"
input_ip_rect  = pygame.Rect(190, 230, 420, 46)
input_ip_activo = False
MAX_IP_CHARS   = 15
PUERTO         = 5000          # puerto del servidor

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PARTIDA
# ─────────────────────────────────────────────────────────────
opciones_jugadores = [2, 3, 4]
opciones_modo      = ["clasico", "extra"]
opciones_agentes   = ["Simple", "Reactivo", "Deliberativo", "Mixto"]

indice_jugadores = 2      # default 4 jugadores (índice 2)
indice_modo      = 0
indice_agentes   = 3      # default Mixto

resumen_config   = ""

# ─────────────────────────────────────────────────────────────
# AJUSTES
# ─────────────────────────────────────────────────────────────
ajuste_volumen     = 60
ajuste_animaciones = True
ajuste_ayudas      = True
opciones_tema      = ["Soleado", "Nocturno", "Unicornios"]
indice_tema        = 0
mensaje_ajustes    = ""
mensaje_ajustes_timer = 0

# ─────────────────────────────────────────────────────────────
# IMÁGENES
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR  = os.path.join(BASE_DIR, "img")

def cargar_imagen(nombre, tamano=None):
    ruta = os.path.join(IMG_DIR, nombre)
    try:
        img = pygame.image.load(ruta).convert_alpha()
        if tamano:
            img = pygame.transform.smoothscale(img, tamano)
        return img
    except (pygame.error, FileNotFoundError):
        return None

bg_img          = cargar_imagen("fondo2.png",  (ANCHO, ALTO))
title_img       = cargar_imagen("title.png",   (480, 80))
img_boton_iniciar = cargar_imagen("Sala.png",  (160, 80))
img_boton_unirse  = cargar_imagen("Unirse.png",(160, 80))
img_boton_ajustes = cargar_imagen("Ajustes.png",(160,80))
img_boton_salir   = cargar_imagen("Salir.png", (160, 80))
img_casilla  = cargar_imagen("agua.png", (CELDA, CELDA))
img_hit      = cargar_imagen("k.png",    (CELDA, CELDA))
img_miss     = cargar_imagen("n.png",    (CELDA, CELDA))

# ─────────────────────────────────────────────────────────────
# ESTADO DE RED  (nuevo)
# ─────────────────────────────────────────────────────────────
cola_entrada    = queue.Queue()   # server → pygame
cola_salida     = queue.Queue()   # pygame → server
mi_id_srv       = None            # player ID asignado por el servidor
turno_srv       = None            # de quién es el turno ahora
es_mi_turno     = False
conectado       = False
eliminados_srv  = set()           # player IDs eliminados
mensaje_hud     = "Configurando partida..."
ganador_srv     = None
hilo_red        = None

# ─────────────────────────────────────────────────────────────
# BOTONES
# ─────────────────────────────────────────────────────────────
class Boton:
    def __init__(self, texto, x, y, w, h, accion, imagen=None):
        self.texto  = texto
        self.rect   = pygame.Rect(x, y, w, h)
        self.accion = accion
        self.imagen = imagen

    def dibujar(self):
        if self.imagen:
            VENTANA.blit(self.imagen, self.rect.topleft)
        else:
            col = BTN_HOVER if self.rect.collidepoint(pygame.mouse.get_pos()) else BTN_PRIMARIO
            pygame.draw.rect(VENTANA, col, self.rect, border_radius=12)
            pygame.draw.rect(VENTANA, BTN_BORDE, self.rect, width=2, border_radius=12)
            t = fuente.render(self.texto, True, BTN_TEXTO)
            VENTANA.blit(t, t.get_rect(center=self.rect.center))

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.accion()


# ─────────────────────────────────────────────────────────────
# ACCIONES UI
# ─────────────────────────────────────────────────────────────
def crear_partida():
    global estado
    estado = CONFIG_PARTIDA

def unirse_partida():
    global estado, input_ip_activo
    estado = CONECTAR
    input_ip_activo = True

def abrir_ajustes():
    global estado
    estado = AJUSTES

def volver_menu():
    global estado, conectado, ganador_srv
    estado = MENU
    conectado = False
    ganador_srv = None

def salir_juego():
    pygame.quit()
    sys.exit()

def cambiar_jugadores(delta):
    global indice_jugadores
    indice_jugadores = (indice_jugadores + delta) % len(opciones_jugadores)

def cambiar_modo(delta):
    global indice_modo
    indice_modo = (indice_modo + delta) % len(opciones_modo)

def cambiar_agentes(delta):
    global indice_agentes
    indice_agentes = (indice_agentes + delta) % len(opciones_agentes)

def cambiar_objetivo(delta):
    global indice_tablero_objetivo
    if jugadores_actuales <= 2:
        indice_tablero_objetivo = 1
        return
    vivos_enemigos = [j for j in range(1, jugadores_actuales + 1)
                      if j != mi_id_srv and j not in eliminados_srv]
    if not vivos_enemigos:
        return
    # Encontrar índice actual en la lista de vivos
    if indice_tablero_objetivo in vivos_enemigos:
        idx = vivos_enemigos.index(indice_tablero_objetivo)
    else:
        idx = 0
    idx = (idx + delta) % len(vivos_enemigos)
    indice_tablero_objetivo = vivos_enemigos[idx]

def ajustar_volumen(delta):
    global ajuste_volumen
    ajuste_volumen = max(0, min(100, ajuste_volumen + delta))

def cambiar_tema(delta):
    global indice_tema
    indice_tema = (indice_tema + delta) % len(opciones_tema)

def toggle_animaciones():
    global ajuste_animaciones
    ajuste_animaciones = not ajuste_animaciones

def toggle_ayudas():
    global ajuste_ayudas
    ajuste_ayudas = not ajuste_ayudas

def guardar_ajustes():
    global mensaje_ajustes, mensaje_ajustes_timer
    mensaje_ajustes = (f"Guardado | Vol:{ajuste_volumen}% | "
                       f"Anim:{'ON' if ajuste_animaciones else 'OFF'}")
    mensaje_ajustes_timer = pygame.time.get_ticks()

# ─────────────────────────────────────────────────────────────
# INICIAR PARTIDA  (punto de integración principal)
# ─────────────────────────────────────────────────────────────
def iniciar_con_configuracion():
    global estado, resumen_config, tableros_partida, jugadores_actuales
    global indice_tablero_objetivo, hilo_red, mensaje_hud, conectado
    global mi_id_srv, turno_srv, es_mi_turno, eliminados_srv, ganador_srv

    jugadores         = opciones_jugadores[indice_jugadores]
    modo              = opciones_modo[indice_modo]
    tipo_agente       = opciones_agentes[indice_agentes]
    jugadores_actuales = jugadores

    # Reiniciar estado de red
    mi_id_srv      = None
    turno_srv      = None
    es_mi_turno    = False
    conectado      = False
    eliminados_srv = set()
    ganador_srv    = None
    mensaje_hud    = "Conectando al servidor..."

    # Limpiar cola de entrada
    while not cola_entrada.empty():
        try: cola_entrada.get_nowait()
        except: pass

    # Inicializar tableros (índice 0 = humano, 1..N = enemigos)
    tableros_partida = [
        [["" for _ in range(TAM)] for _ in range(TAM)]
        for _ in range(jugadores)
    ]
    # Marcar mis barcos en el tablero propio
    for tam, f, c, h in BARCOS_AUTO:
        for i in range(tam):
            ff = f if h else f + i
            cc = c + i if h else c
            tableros_partida[0][ff][cc] = "barco"

    indice_tablero_objetivo = 2 if mi_id_srv == 1 else 2   # por defecto apuntar a J2
    resumen_config = f"Jugadores: {jugadores} | Modo: {modo} | Agentes: {tipo_agente}"
    estado = JUEGO

    # Lanzar hilo de red
    hilo_red = threading.Thread(
        target=_hilo_asyncio,
        args=(ip_confirmada, PUERTO, jugadores, modo, tipo_agente),
        daemon=True,
    )
    hilo_red.start()

# ─────────────────────────────────────────────────────────────
# HILO ASYNCIO + CLIENTE HUMANO
# ─────────────────────────────────────────────────────────────
def _hilo_asyncio(ip, puerto, num_jugadores, modo, tipo_agente):
    """Corre el event loop de asyncio en un hilo separado."""
    url = f"ws://{ip}:{puerto}"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_arrancar_todo(url, num_jugadores, modo, tipo_agente))
    except Exception as e:
        cola_entrada.put({'tipo': '_error_red', 'mensaje': str(e)})
    finally:
        loop.close()


async def _arrancar_todo(url, num_jugadores, modo, tipo_agente):
    """Lanza el cliente humano y los agentes IA de forma concurrente."""

    # Agentes según cantidad de jugadores y tipo seleccionado
    def crear_agente(nombre, idx):
        if tipo_agente == "Simple":
            return AgenteSimple(url=url, nombre=nombre)
        elif tipo_agente == "Reactivo":
            return AgenteReactivo(url=url, nombre=nombre)
        elif tipo_agente == "Deliberativo":
            return AgenteDeliberativo(url=url, nombre=nombre)
        else:  # Mixto
            tipos = [AgenteSimple, AgenteReactivo, AgenteDeliberativo]
            return tipos[idx % 3](url=url, nombre=nombre)

    nombres_agentes = ["IA-Simple", "IA-Reactivo", "IA-Deliberativo"]
    agentes = [crear_agente(nombres_agentes[i], i) for i in range(num_jugadores - 1)]
    nombres_todos = ["Humano"] + [a.nombre for a in agentes]

    # El humano crea la partida
    tarea_humano = asyncio.create_task(
        _cliente_humano(url, nombres_todos, modo, num_jugadores)
    )

    # Los agentes se unen con delay escalonado
    tareas_agentes = []
    for i, agente in enumerate(agentes):
        await asyncio.sleep(0.7 + i * 0.5)
        tareas_agentes.append(asyncio.create_task(agente.run()))

    await asyncio.gather(tarea_humano, *tareas_agentes)


async def _cliente_humano(url, nombres, modo, num_jugadores):
    """
    Manejador WebSocket del jugador humano.
    Lee acciones de cola_salida y manda resultados a cola_entrada.
    """
    global mi_id_srv, turno_srv, es_mi_turno, conectado, mensaje_hud

    try:
        ws = await websockets.connect(url)
    except Exception as e:
        cola_entrada.put({'tipo': '_error_red', 'mensaje': f'No se pudo conectar: {e}'})
        return

    cola_entrada.put({'tipo': '_conectado'})

    # Crear la partida
    await ws.send(json.dumps({
        'accion':    'crear_juego',
        'nombre_j1': nombres[0],
        'nombre_j2': nombres[1] if len(nombres) > 1 else None,
        'nombre_j3': nombres[2] if len(nombres) > 2 else None,
        'nombre_j4': nombres[3] if len(nombres) > 3 else None,
        'modo':      modo,
    }))
    await asyncio.sleep(0.3)

    # Unirse como jugador 1
    await ws.send(json.dumps({'accion': 'unirse_juego', 'nombre_jugador': nombres[0]}))
    await asyncio.sleep(0.3)

    # Colocar barcos automáticamente
    for tam, f, c, h in BARCOS_AUTO:
        await ws.send(json.dumps({
            'accion': 'colocar_barco', 'tamaño': tam,
            'fila': f, 'columna': c, 'horizontal': h,
        }))
        await asyncio.sleep(0.1)

    # Correr receptor y emisor de forma concurrente
    async def recibir():
        global mi_id_srv
        async for msg in ws:
            datos = json.loads(msg)
            tipo  = datos.get('tipo')

            if tipo == 'jugador_unido':
                jid = datos.get('tu_jugador_id')
                if jid:
                    mi_id_srv = jid

            elif tipo == 'juego_listo':
                await asyncio.sleep(0.3)
                await ws.send(json.dumps({'accion': 'iniciar'}))

            elif tipo == 'juego_iniciado':
                await ws.send(json.dumps({'accion': 'obtener_estado'}))
                cola_entrada.put(datos)

            elif tipo in ('resultado_disparo', 'estado_juego'):
                cola_entrada.put(datos)

            elif tipo == 'error':
                cola_entrada.put(datos)

    async def enviar():
        while True:
            try:
                msg = cola_salida.get_nowait()
                await ws.send(json.dumps(msg))
            except queue.Empty:
                await asyncio.sleep(0.05)

    await asyncio.gather(recibir(), enviar())


# ─────────────────────────────────────────────────────────────
# PROCESAR COLA DE ENTRADA (llamado desde el loop pygame)
# ─────────────────────────────────────────────────────────────
def procesar_cola_red():
    global mi_id_srv, turno_srv, es_mi_turno, conectado
    global mensaje_hud, eliminados_srv, ganador_srv, indice_tablero_objetivo

    while True:
        try:
            datos = cola_entrada.get_nowait()
        except queue.Empty:
            break

        tipo = datos.get('tipo')

        if tipo == '_conectado':
            conectado = True
            mensaje_hud = "Conectado. Colocando barcos..."

        elif tipo == '_error_red':
            mensaje_hud = f"ERROR: {datos.get('mensaje', 'desconocido')}"

        elif tipo == 'error':
            mensaje_hud = f"Servidor: {datos.get('mensaje', '')}"

        elif tipo == 'juego_iniciado':
            turno_srv   = datos.get('turno_actual')
            es_mi_turno = (turno_srv == mi_id_srv)
            _actualizar_hud()

        elif tipo == 'estado_juego':
            est = datos.get('estado', {})
            eliminados_srv = set(est.get('eliminados', []))
            # Apuntar al primer rival vivo por defecto
            for jid in range(1, jugadores_actuales + 1):
                if jid != mi_id_srv and jid not in eliminados_srv:
                    indice_tablero_objetivo = jid
                    break

        elif tipo == 'resultado_disparo':
            atacante  = datos.get('atacante')
            objetivo  = datos.get('objetivo')
            fila      = datos.get('fila')
            col       = datos.get('columna')
            resultado = datos.get('resultado')
            elim      = datos.get('objetivo_eliminado', False)

            valor = "hit" if resultado == "impacto" else "miss"

            if atacante == mi_id_srv:
                # Yo disparé: actualizar tablero del enemigo
                idx = objetivo - 1
                if 0 <= idx < len(tableros_partida):
                    tableros_partida[idx][fila][col] = valor

            if objetivo == mi_id_srv:
                # Me dispararon: actualizar mi tablero propio
                tableros_partida[0][fila][col] = valor

            if elim:
                eliminados_srv.add(objetivo)
                # Si el objetivo que miraba fue eliminado, cambiar objetivo
                if indice_tablero_objetivo == objetivo:
                    cambiar_objetivo(1)

            ganador = datos.get('ganador')
            if ganador:
                ganador_srv = ganador
                if ganador == mi_id_srv:
                    mensaje_hud = "🏆 ¡GANASTE!"
                else:
                    nombre = f"Jugador {ganador}"
                    mensaje_hud = f"Ganó {nombre}"
            else:
                turno_srv   = datos.get('turno_actual')
                es_mi_turno = (turno_srv == mi_id_srv)
                _actualizar_hud()


def _actualizar_hud():
    global mensaje_hud
    if ganador_srv:
        return
    if mi_id_srv in eliminados_srv:
        mensaje_hud = "Eliminado — mirando partida"
    elif es_mi_turno:
        obj = indice_tablero_objetivo
        mensaje_hud = f"¡TU TURNO! → Apuntando a J{obj}. Haz click en el tablero enemigo."
    else:
        mensaje_hud = f"Esperando... turno de J{turno_srv}"


# ─────────────────────────────────────────────────────────────
# CLICK EN TABLERO (ahora envía disparo real)
# ─────────────────────────────────────────────────────────────
def click_tablero(pos):
    global es_mi_turno
    if not es_mi_turno or not conectado or ganador_srv:
        return
    if mi_id_srv in eliminados_srv:
        return
    if len(zonas_tableros) < 2:
        return

    zona_enemigo = zonas_tableros[1]
    if zona_enemigo.collidepoint(pos):
        col  = (pos[0] - zona_enemigo.x) // CELDA
        fila = (pos[1] - zona_enemigo.y) // CELDA
        if 0 <= fila < TAM and 0 <= col < TAM:
            idx = indice_tablero_objetivo - 1
            if 0 <= idx < len(tableros_partida):
                if tableros_partida[idx][fila][col] == "":
                    cola_salida.put({
                        'accion':   'disparar',
                        'objetivo': indice_tablero_objetivo,
                        'fila':     fila,
                        'columna':  col,
                    })
                    es_mi_turno = False
                    global mensaje_hud
                    mensaje_hud = "Disparo enviado, esperando resultado..."


# ─────────────────────────────────────────────────────────────
# BOTONES
# ─────────────────────────────────────────────────────────────
botones_menu = [
    Boton("Iniciar Partida", 320, 210, 160, 80, crear_partida,  img_boton_iniciar),
    Boton("Unirme a Partida",320, 300, 160, 80, unirse_partida, img_boton_unirse),
    Boton("Ajustes",         320, 390, 160, 80, abrir_ajustes,  img_boton_ajustes),
    Boton("Salir",           320, 480, 160, 80, salir_juego,    img_boton_salir),
]
botones_navegacion = [Boton("Menú", 20, 20, 130, 42, volver_menu)]
botones_config = [
    Boton("<", 430, 245, 45, 45, lambda: cambiar_jugadores(-1)),
    Boton(">", 510, 245, 45, 45, lambda: cambiar_jugadores(1)),
    Boton("<", 430, 315, 45, 45, lambda: cambiar_modo(-1)),
    Boton(">", 510, 315, 45, 45, lambda: cambiar_modo(1)),
    Boton("<", 430, 385, 45, 45, lambda: cambiar_agentes(-1)),
    Boton(">", 510, 385, 45, 45, lambda: cambiar_agentes(1)),
    Boton("Iniciar", 300, 470, 200, 56, iniciar_con_configuracion),
]
botones_ajustes = [
    Boton("-",       440, 252, 45, 38, lambda: ajustar_volumen(-5)),
    Boton("+",       495, 252, 45, 38, lambda: ajustar_volumen(5)),
    Boton("Cambiar", 435, 315, 125, 40, toggle_animaciones),
    Boton("Cambiar", 435, 375, 125, 40, toggle_ayudas),
    Boton("<",       435, 435, 45, 40, lambda: cambiar_tema(-1)),
    Boton(">",       515, 435, 45, 40, lambda: cambiar_tema(1)),
    Boton("Guardar", 300, 505, 200, 50, guardar_ajustes),
]
botones_conectar_agentes = [
    Boton("<", 430, 368, 45, 40, lambda: cambiar_agentes(-1)),
    Boton(">", 510, 368, 45, 40, lambda: cambiar_agentes(1)),
]
botones_objetivo = [
    Boton("<", 650, 72, 34, 28, lambda: cambiar_objetivo(-1)),
    Boton(">", 690, 72, 34, 28, lambda: cambiar_objetivo(1)),
]

# ─────────────────────────────────────────────────────────────
# DIBUJO: MENÚ
# ─────────────────────────────────────────────────────────────
def dibujar_menu():
    if bg_img: VENTANA.blit(bg_img, (0, 0))
    else: VENTANA.fill(BG)
    if title_img: VENTANA.blit(title_img, (160, 40))
    else:
        t = fuente_titulo.render("BATTLESHIP", True, BLANCO)
        VENTANA.blit(t, (220, 140))
    for b in botones_menu: b.dibujar()

# ─────────────────────────────────────────────────────────────
# DIBUJO: CONECTAR
# ─────────────────────────────────────────────────────────────
def dibujar_conectar():
    if bg_img: VENTANA.blit(bg_img, (0, 0))
    else: VENTANA.fill(BG)
    VENTANA.blit(fuente_panel.render("Pantalla de conexión", True, BLANCO),
                 fuente_panel.render("Pantalla de conexión", True, BLANCO).get_rect(center=(ANCHO//2, 140)))
    VENTANA.blit(fuente.render("IP del servidor", True, BLANCO), (190, 195))
    borde = UI_BORDE_ACTIVO if input_ip_activo else BTN_BORDE
    pygame.draw.rect(VENTANA, UI_CAJA, input_ip_rect, border_radius=8)
    pygame.draw.rect(VENTANA, borde,   input_ip_rect, width=2, border_radius=8)
    t_ip = fuente.render(ip_servidor or "Ej: 192.168.1.50", True, BLANCO)
    VENTANA.blit(t_ip, (input_ip_rect.x + 12, input_ip_rect.y + 10))
    if input_ip_activo and (pygame.time.get_ticks() // 500) % 2 == 0:
        cx = input_ip_rect.x + 12 + t_ip.get_width() + 2
        pygame.draw.line(VENTANA, UI_BORDE_ACTIVO,
                         (cx, input_ip_rect.y + 10),
                         (cx, input_ip_rect.y + input_ip_rect.height - 10), 2)
    VENTANA.blit(fuente.render("Presiona Enter para confirmar", True, BLANCO), (190, 292))
    if ip_confirmada:
        VENTANA.blit(fuente.render(f"IP: {ip_confirmada}", True, VERDE), (190, 330))
    VENTANA.blit(fuente.render("Agente:", True, BLANCO), (190, 378))
    va = fuente.render(opciones_agentes[indice_agentes], True, VERDE)
    VENTANA.blit(va, va.get_rect(center=(615, 388)))
    for b in botones_conectar_agentes: b.dibujar()
    for b in botones_navegacion: b.dibujar()

# ─────────────────────────────────────────────────────────────
# DIBUJO: AJUSTES
# ─────────────────────────────────────────────────────────────
def dibujar_ajustes():
    if bg_img: VENTANA.blit(bg_img, (0, 0))
    else: VENTANA.fill(BG)
    VENTANA.blit(fuente_panel.render("Ajustes", True, BLANCO), (352, 165))
    for txt, y in [("Volumen",255),("Animaciones",315),("Ayudas visuales",375),("Tema",435)]:
        VENTANA.blit(fuente.render(txt, True, BLANCO), (230, y))
    for val, y in [(f"{ajuste_volumen}%",255),
                   ("ON" if ajuste_animaciones else "OFF",315),
                   ("ON" if ajuste_ayudas else "OFF",375),
                   (opciones_tema[indice_tema],435)]:
        VENTANA.blit(fuente.render(val, True, VERDE), (570, y))
    barra_v = pygame.Rect(230, 285, int(1.9*ajuste_volumen), 8)
    pygame.draw.rect(VENTANA, GRIS, pygame.Rect(230,285,190,8), border_radius=5)
    pygame.draw.rect(VENTANA, AZUL, barra_v, border_radius=5)
    if mensaje_ajustes and pygame.time.get_ticks()-mensaje_ajustes_timer < 3000:
        VENTANA.blit(fuente.render(mensaje_ajustes, True, VERDE), (115, 585))
    for b in botones_ajustes: b.dibujar()
    for b in botones_navegacion: b.dibujar()

# ─────────────────────────────────────────────────────────────
# DIBUJO: CONFIG PARTIDA
# ─────────────────────────────────────────────────────────────
def dibujar_config_partida():
    if bg_img: VENTANA.blit(bg_img, (0, 0))
    else: VENTANA.fill(BG)
    t = fuente_panel.render("Configurar Partida", True, BLANCO)
    VENTANA.blit(t, t.get_rect(center=(ANCHO//2, 165)))
    filas = [
        ("Cantidad de jugadores", str(opciones_jugadores[indice_jugadores]), 250),
        ("Modo de juego",         opciones_modo[indice_modo],                320),
        ("Tipo de agentes",       opciones_agentes[indice_agentes],          390),
    ]
    for etiq, val, y in filas:
        VENTANA.blit(fuente.render(etiq, True, BLANCO), (140, y+8))
        tv = fuente.render(val, True, VERDE)
        VENTANA.blit(tv, tv.get_rect(center=(620, y+15)))
    for b in botones_config: b.dibujar()
    for b in botones_navegacion: b.dibujar()

# ─────────────────────────────────────────────────────────────
# DIBUJO: TABLERO
# ─────────────────────────────────────────────────────────────
def dibujar_tablero(tablero, offset_x, offset_y, titulo, es_jugador=False):
    area = pygame.Rect(offset_x, offset_y, TAM*CELDA, TAM*CELDA)
    pygame.draw.rect(VENTANA, (18, 60, 96), area)
    pygame.draw.rect(VENTANA, GRID_COLOR,   area, width=2)

    t = fuente_ejes.render(titulo, True, TITULO_HUD)
    VENTANA.blit(t, t.get_rect(center=(offset_x + TAM*CELDA//2, offset_y - 30)))

    for j in range(TAM):
        letra = fuente_ejes.render(chr(ord("A")+j), True, EJE_HUD)
        VENTANA.blit(letra, (offset_x + j*CELDA + (CELDA-letra.get_width())//2, offset_y-18))
    for i in range(TAM):
        num = fuente_ejes.render(str(i+1), True, EJE_HUD)
        VENTANA.blit(num, (offset_x-18, offset_y + i*CELDA + (CELDA-num.get_height())//2))

    for i in range(TAM):
        for j in range(TAM):
            x = offset_x + j*CELDA
            y = offset_y + i*CELDA
            celda = tablero[i][j]

            if celda == "hit":
                if img_hit: VENTANA.blit(img_hit, (x, y))
                else: pygame.draw.rect(VENTANA, ROJO, (x, y, CELDA, CELDA))
            elif celda == "miss":
                if img_miss: VENTANA.blit(img_miss, (x, y))
                else: pygame.draw.rect(VENTANA, GRIS, (x, y, CELDA, CELDA))
            elif celda == "barco":
                pygame.draw.rect(VENTANA, BARCO_COLOR, (x, y, CELDA, CELDA))
            else:
                if img_casilla: VENTANA.blit(img_casilla, (x, y))
                else: pygame.draw.rect(VENTANA, AGUA_COLOR, (x, y, CELDA, CELDA))

            pygame.draw.rect(VENTANA, GRID_COLOR, (x, y, CELDA, CELDA), 1)

    return pygame.Rect(offset_x, offset_y, TAM*CELDA, TAM*CELDA)

# ─────────────────────────────────────────────────────────────
# DIBUJO: JUEGO
# ─────────────────────────────────────────────────────────────
def dibujar_juego():
    global zonas_tableros

    if bg_img: VENTANA.blit(bg_img, (0, 0))
    else: VENTANA.fill(BG)

    # ── HUD superior ──────────────────────────────────────────
    cabecera = pygame.Rect(20, 16, ANCHO-40, 42)
    pygame.draw.rect(VENTANA, (13, 37, 63), cabecera, border_radius=10)
    pygame.draw.rect(VENTANA, GRID_COLOR,   cabecera, width=2, border_radius=10)

    jid_txt  = f"J{mi_id_srv}" if mi_id_srv else "?"
    turno_txt = f"J{turno_srv}" if turno_srv else "?"
    obj_txt  = f"J{indice_tablero_objetivo}"
    hud_txt  = f"BATTLESHIP  •  TURNO: {turno_txt}  •  TÚ: {jid_txt}  •  OBJETIVO: {obj_txt}"
    t_hud = fuente_ejes.render(hud_txt, True, TITULO_HUD)
    VENTANA.blit(t_hud, (30, 29))

    # ── Barra de estado (turno / espera / ganador) ────────────
    color_msg = (COLOR_MI_TURNO if es_mi_turno
                 else COLOR_GANADOR if ganador_srv
                 else COLOR_TURNO_OTRO)
    barra_msg = pygame.Rect(20, 64, ANCHO-40, 26)
    pygame.draw.rect(VENTANA, (10, 25, 45), barra_msg, border_radius=6)
    pygame.draw.rect(VENTANA, color_msg,    barra_msg, width=1, border_radius=6)
    t_msg = fuente_ejes.render(mensaje_hud, True, color_msg)
    VENTANA.blit(t_msg, t_msg.get_rect(center=barra_msg.center))

    # ── Tableros ──────────────────────────────────────────────
    x_jugador, x_objetivo, y_tableros = 80, 420, 130
    zonas_tableros = []

    # Tablero propio
    zona_j = dibujar_tablero(tableros_partida[0], x_jugador, y_tableros,
                              f"MI FLOTA (J{mi_id_srv or '?'})", es_jugador=True)
    zonas_tableros.append(zona_j)

    # Tablero objetivo (del enemigo seleccionado)
    idx_obj = indice_tablero_objetivo - 1
    if 0 <= idx_obj < len(tableros_partida):
        tablero_obj = tableros_partida[idx_obj]
    else:
        tablero_obj = [[""] * TAM for _ in range(TAM)]

    eliminado_str = " [ELIMINADO]" if indice_tablero_objetivo in eliminados_srv else ""
    zona_e = dibujar_tablero(tablero_obj, x_objetivo, y_tableros,
                              f"ENEMIGO J{indice_tablero_objetivo}{eliminado_str}")
    zonas_tableros.append(zona_e)

    # Botones cambiar objetivo (3-4 jugadores)
    if jugadores_actuales > 2:
        for b in botones_objetivo: b.dibujar()

    # ── Resumen config ────────────────────────────────────────
    if resumen_config:
        info_bg = pygame.Rect(20, 602, ANCHO-40, 28)
        pygame.draw.rect(VENTANA, (20, 40, 65), info_bg, border_radius=8)
        VENTANA.blit(fuente_ejes.render(resumen_config, True, TITULO_HUD), (28, 610))

    # ── Leyenda ───────────────────────────────────────────────
    VENTANA.blit(fuente_ejes.render("K=impacto  N=agua  ■=mi barco", True, EJE_HUD), (34, 96))

    # ── Botón volver al menú en pantalla de fin ───────────────
    if ganador_srv:
        for b in botones_navegacion: b.dibujar()


# ─────────────────────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────
while True:
    clock.tick(FPS)

    # Procesar eventos de red cada frame
    if estado == JUEGO:
        procesar_cola_red()

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.MOUSEBUTTONDOWN:
            if estado == MENU:
                for b in botones_menu: b.click(evento.pos)

            elif estado == JUEGO:
                if jugadores_actuales > 2:
                    for b in botones_objetivo: b.click(evento.pos)
                click_tablero(evento.pos)
                if ganador_srv:
                    for b in botones_navegacion: b.click(evento.pos)

            elif estado == CONECTAR:
                for b in botones_navegacion: b.click(evento.pos)
                for b in botones_conectar_agentes: b.click(evento.pos)
                input_ip_activo = input_ip_rect.collidepoint(evento.pos)

            elif estado == AJUSTES:
                for b in botones_ajustes: b.click(evento.pos)
                for b in botones_navegacion: b.click(evento.pos)

            elif estado == CONFIG_PARTIDA:
                for b in botones_config: b.click(evento.pos)
                for b in botones_navegacion: b.click(evento.pos)

        if evento.type == pygame.KEYDOWN and estado == CONECTAR and input_ip_activo:
            if evento.key == pygame.K_RETURN:
                ip_confirmada = ip_servidor.strip()
            elif evento.key == pygame.K_BACKSPACE:
                ip_servidor = ip_servidor[:-1]
            elif len(ip_servidor) < MAX_IP_CHARS and evento.unicode in "0123456789.":
                ip_servidor += evento.unicode

    # ── Renderizar según estado ───────────────────────────────
    if   estado == MENU:          dibujar_menu()
    elif estado == CONECTAR:      dibujar_conectar()
    elif estado == AJUSTES:       dibujar_ajustes()
    elif estado == CONFIG_PARTIDA: dibujar_config_partida()
    elif estado == JUEGO:         dibujar_juego()

    pygame.display.flip()
