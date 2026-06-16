import pygame
import sys
import random
import os

pygame.init()

# Configuración de ventana
ANCHO, ALTO = 800, 640
VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Battleship")

FPS = 60
clock = pygame.time.Clock()

# Colores
BG = (30, 30, 50)
BLANCO = (255, 220, 80)
AZUL = (52, 152, 219)
ROJO = (231, 76, 60)
GRIS = (200, 200, 200)
OSC = (46, 59, 78)
SOMBRA = (15, 22, 34)
VERDE = (255, 186, 94)
BTN_PRIMARIO = (242, 156, 34)
BTN_HOVER = (226, 133, 12)
BTN_BORDE = (74, 42, 0)
BTN_TEXTO = (33, 19, 2)
UI_CAJA = (43, 32, 20)
UI_BORDE_ACTIVO = (255, 202, 125)
BG_TABLERO = (14, 26, 44)
BG_TABLERO_TOP = (18, 38, 63)
BG_TABLERO_BOTTOM = (8, 18, 31)
PANEL_TABLERO = (24, 44, 70)
BORDE_TABLERO = (255, 220, 80)
BORDE_TABLERO_RIVAL = (255, 186, 94)
EJES_COLOR = (250, 232, 170)
RESALTADO_TEXTO = (255, 186, 94)
GRID_COLOR = (87, 168, 196)
EJE_HUD = (178, 235, 251)
TITULO_HUD = (201, 245, 255)
AGUA_COLOR = (44, 123, 168)

# Estados
MENU = "menu"
JUEGO = "juego"
CONECTAR = "conectar"
AJUSTES = "ajustes"
CONFIG_PARTIDA = "config_partida"

estado = MENU

# Tablero
TAM = 10
CELDA = 30

tablero_jugador = [["" for _ in range(TAM)] for _ in range(TAM)]
tablero_enemigo = [["" for _ in range(TAM)] for _ in range(TAM)]
tableros_partida = [tablero_jugador, tablero_enemigo]
zonas_tableros = []
jugadores_actuales = 2
indice_tablero_objetivo = 1

# Fuente
fuente = pygame.font.SysFont("Trebuchet MS", 24)
fuente_titulo = pygame.font.SysFont("Trebuchet MS", 52, bold=True)
fuente_panel = pygame.font.SysFont("Trebuchet MS", 30, bold=True)
fuente_ejes = pygame.font.SysFont("Trebuchet MS", 14, bold=True)

# Entrada de IP (pantalla conectar)
ip_servidor = ""
ip_confirmada = ""
input_ip_rect = pygame.Rect(190, 230, 420, 46)
input_ip_activo = False
MAX_IP_CHARS = 15

# Configuracion de partida
opciones_jugadores = [2, 3, 4]
opciones_modo = ["Clasico", "Equipos", "Estrategico"]
opciones_agentes = ["Jugador", "Simple", "Reactivo","Utilidad"]

indice_jugadores = 0
indice_modo = 0
indice_agentes = 0

resumen_config = ""

# Ajustes del juego
ajuste_volumen = 60
ajuste_animaciones = True
ajuste_ayudas = True
opciones_tema = ["Soleado", "Nocturno", "Unicornios"]
indice_tema = 0
mensaje_ajustes = ""
mensaje_ajustes_timer = 0


# =========================
#  CARGA DE IMÁGENES
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")


def cargar_imagen(nombre, tamano=None):
    ruta = os.path.join(IMG_DIR, nombre)
    try:
        imagen = pygame.image.load(ruta).convert_alpha()
        if tamano:
            imagen = pygame.transform.smoothscale(imagen, tamano)
        return imagen
    except (pygame.error, FileNotFoundError):
        return None


bg_img = cargar_imagen("fondo2.png", (ANCHO, ALTO))
title_img = cargar_imagen("title.png", (480, 80))
img_boton_iniciar = cargar_imagen("Sala.png", (160, 80))
img_boton_unirse = cargar_imagen("Unirse.png", (160, 80))
img_boton_ajustes = cargar_imagen("Ajustes.png", (160, 80))
img_boton_salir = cargar_imagen("Salir.png", (160, 80))
img_casilla = cargar_imagen("agua.png", (CELDA, CELDA))
img_hit = cargar_imagen("k.png", (CELDA, CELDA))
img_miss = cargar_imagen("n.png", (CELDA, CELDA))


# =========================
# BOTONES
# =========================
class Boton:
    def __init__(self, texto, x, y, w, h, accion, imagen=None):
        self.texto = texto
        self.rect = pygame.Rect(x, y, w, h)
        self.accion = accion
        self.imagen = imagen

    def dibujar(self):
        if self.imagen:
            VENTANA.blit(self.imagen, self.rect.topleft)
        else:
            mouse_pos = pygame.mouse.get_pos()
            color_boton = BTN_HOVER if self.rect.collidepoint(mouse_pos) else BTN_PRIMARIO
            pygame.draw.rect(VENTANA, color_boton, self.rect, border_radius=12)
            pygame.draw.rect(VENTANA, BTN_BORDE, self.rect, width=2, border_radius=12)

            texto = fuente.render(self.texto, True, BTN_TEXTO)
            texto_rect = texto.get_rect(center=self.rect.center)
            VENTANA.blit(texto, texto_rect)

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.accion()


# =========================
# 🎮 ACCIONES
# =========================
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
    global estado
    estado = MENU


def salir_juego():
    pygame.quit()
    sys.exit()


def cambiar_jugadores(delta):
    global indice_jugadores
    total = len(opciones_jugadores)
    indice_jugadores = (indice_jugadores + delta) % total


def cambiar_modo(delta):
    global indice_modo
    total = len(opciones_modo)
    indice_modo = (indice_modo + delta) % total


def cambiar_agentes(delta):
    global indice_agentes
    total = len(opciones_agentes)
    indice_agentes = (indice_agentes + delta) % total


def iniciar_con_configuracion():
    global estado, resumen_config, tableros_partida, jugadores_actuales, indice_tablero_objetivo
    jugadores = opciones_jugadores[indice_jugadores]
    modo = opciones_modo[indice_modo]
    agentes = opciones_agentes[indice_agentes]
    jugadores_actuales = jugadores
    tableros_partida = [
        [["" for _ in range(TAM)] for _ in range(TAM)] for _ in range(jugadores_actuales)
    ]
    indice_tablero_objetivo = 1
    resumen_config = f"Jugadores: {jugadores} | Modo: {modo} | Agentes: {agentes}"
    estado = JUEGO


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
    tema = opciones_tema[indice_tema]
    mensaje_ajustes = (
        f"Guardado | Vol: {ajuste_volumen}% | Animaciones: {'ON' if ajuste_animaciones else 'OFF'}"
        f" | Ayudas: {'ON' if ajuste_ayudas else 'OFF'} | Tema: {tema}"
    )
    mensaje_ajustes_timer = pygame.time.get_ticks()


def cambiar_objetivo(delta):
    global indice_tablero_objetivo
    if jugadores_actuales <= 2:
        indice_tablero_objetivo = 1
        return

    total_enemigos = jugadores_actuales - 1
    indice_relativo = (indice_tablero_objetivo - 1 + delta) % total_enemigos
    indice_tablero_objetivo = indice_relativo + 1


# =========================
# MEnu
# =========================
botones_menu = [
    Boton("Iniciar Partida", 320, 210, 160, 80, crear_partida, img_boton_iniciar),
    Boton("Unirme a Partida", 320, 300, 160, 80, unirse_partida, img_boton_unirse),
    Boton("Ajustes", 320, 390, 160, 80, abrir_ajustes, img_boton_ajustes),
    Boton("Salir", 320, 480, 160, 80, salir_juego, img_boton_salir)
]

botones_navegacion = [
    Boton("Menu", 20, 20, 130, 42, volver_menu)
]

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
    Boton("-", 440, 252, 45, 38, lambda: ajustar_volumen(-5)),
    Boton("+", 495, 252, 45, 38, lambda: ajustar_volumen(5)),
    Boton("Cambiar", 435, 315, 125, 40, toggle_animaciones),
    Boton("Cambiar", 435, 375, 125, 40, toggle_ayudas),
    Boton("<", 435, 435, 45, 40, lambda: cambiar_tema(-1)),
    Boton(">", 515, 435, 45, 40, lambda: cambiar_tema(1)),
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


def dibujar_menu():
    if bg_img:
        VENTANA.blit(bg_img, (0, 0))
    else:
        VENTANA.fill(BG)

    if title_img:
        VENTANA.blit(title_img, (160, 40))
    else:
        titulo = fuente_titulo.render("BATTLESHIP", True, BLANCO)
        VENTANA.blit(titulo, (220, 140))

    for b in botones_menu:
        b.dibujar()


# =========================
# PANTALLA CONECTAR
# =========================
def dibujar_conectar():
    if bg_img:
        VENTANA.blit(bg_img, (0, 0))
    else:
        VENTANA.fill(BG)

    titulo = fuente_panel.render("Pantalla de conexion", True, BLANCO)
    titulo_rect = titulo.get_rect(center=(ANCHO // 2, 140))
    VENTANA.blit(titulo, titulo_rect)

    texto = fuente.render("IP del servidor", True, BLANCO)
    VENTANA.blit(texto, (190, 195))

    borde = UI_BORDE_ACTIVO if input_ip_activo else BTN_BORDE
    pygame.draw.rect(VENTANA, UI_CAJA, input_ip_rect, border_radius=8)
    pygame.draw.rect(VENTANA, borde, input_ip_rect, width=2, border_radius=8)

    texto_ip = fuente.render(ip_servidor or "Ej: 192.168.1.50", True, BLANCO)
    VENTANA.blit(texto_ip, (input_ip_rect.x + 12, input_ip_rect.y + 10))

    # Cursor intermitente cuando el input esta activo.
    if input_ip_activo and (pygame.time.get_ticks() // 500) % 2 == 0:
        cursor_x = input_ip_rect.x + 12 + texto_ip.get_width() + 2
        pygame.draw.line(
            VENTANA,
            UI_BORDE_ACTIVO,
            (cursor_x, input_ip_rect.y + 10),
            (cursor_x, input_ip_rect.y + input_ip_rect.height - 10),
            2,
        )

    ayuda = fuente.render("Presiona Enter para confirmar", True, BLANCO)
    VENTANA.blit(ayuda, (190, 292))

    if ip_confirmada:
        confirmacion = fuente.render(f"IP seleccionada: {ip_confirmada}", True, VERDE)
        VENTANA.blit(confirmacion, (190, 330))

    etiqueta_agentes = fuente.render("Agente:", True, BLANCO)
    VENTANA.blit(etiqueta_agentes, (190, 378))

    valor_agente = fuente.render(opciones_agentes[indice_agentes], True, VERDE)
    valor_rect = valor_agente.get_rect(center=(615, 388))
    VENTANA.blit(valor_agente, valor_rect)

    for b in botones_conectar_agentes:
        b.dibujar()

    for b in botones_navegacion:
        b.dibujar()


# =========================
# PANTALLA AJUSTES
# =========================
def dibujar_ajustes():
    if bg_img:
        VENTANA.blit(bg_img, (0, 0))
    else:
        VENTANA.fill(BG)

    titulo = fuente_panel.render("Ajustes", True, BLANCO)
    VENTANA.blit(titulo, (352, 165))

    VENTANA.blit(fuente.render("Volumen", True, BLANCO), (230, 255))
    VENTANA.blit(fuente.render("Animaciones", True, BLANCO), (230, 315))
    VENTANA.blit(fuente.render("Ayudas visuales", True, BLANCO), (230, 375))
    VENTANA.blit(fuente.render("Tema", True, BLANCO), (230, 435))

    valor_anim = "ON" if ajuste_animaciones else "OFF"
    valor_ayuda = "ON" if ajuste_ayudas else "OFF"
    valor_tema = opciones_tema[indice_tema]

    VENTANA.blit(fuente.render(f"{ajuste_volumen}%", True, VERDE), (570, 255))
    VENTANA.blit(fuente.render(valor_anim, True, VERDE), (585, 315))
    VENTANA.blit(fuente.render(valor_ayuda, True, VERDE), (585, 375))
    VENTANA.blit(fuente.render(valor_tema, True, VERDE), (570, 435))

    barra_fondo = pygame.Rect(230, 285, 190, 8)
    barra_vol = pygame.Rect(230, 285, int(1.9 * ajuste_volumen), 8)
    pygame.draw.rect(VENTANA, GRIS, barra_fondo, border_radius=5)
    pygame.draw.rect(VENTANA, AZUL, barra_vol, border_radius=5)

    if mensaje_ajustes and pygame.time.get_ticks() - mensaje_ajustes_timer < 3000:
        texto_guardado = fuente.render(mensaje_ajustes, True, VERDE)
        VENTANA.blit(texto_guardado, (115, 585))

    for b in botones_ajustes:
        b.dibujar()

    for b in botones_navegacion:
        b.dibujar()


# =========================
#  CONFIG PARTIDA
# =========================
def dibujar_config_partida():
    if bg_img:
        VENTANA.blit(bg_img, (0, 0))
    else:
        VENTANA.fill(BG)

    titulo = fuente_panel.render("Configurar Partida", True, BLANCO)
    titulo_rect = titulo.get_rect(center=(ANCHO // 2, 165))
    VENTANA.blit(titulo, titulo_rect)

    valor_jugadores = str(opciones_jugadores[indice_jugadores])
    valor_modo = opciones_modo[indice_modo]
    valor_agentes = opciones_agentes[indice_agentes]

    filas_config = [
        ("Cantidad de jugadores", valor_jugadores, 250),
        ("Modo de juego", valor_modo, 320),
        ("Agentes", valor_agentes, 390),
    ]

    for etiqueta, valor, y in filas_config:
        VENTANA.blit(fuente.render(etiqueta, True, BLANCO), (140, y + 8))
        texto_valor = fuente.render(valor, True, VERDE)
        valor_rect = texto_valor.get_rect(center=(620, y + 15))
        VENTANA.blit(texto_valor, valor_rect)

    for b in botones_config:
        b.dibujar()

    for b in botones_navegacion:
        b.dibujar()


# =========================
# TABLERO
# =========================
def dibujar_tablero(tablero, offset_x, offset_y, titulo, es_jugador=False):
    # Fondo sutil del area del tablero, estilo HUD.
    area_tablero = pygame.Rect(offset_x, offset_y, TAM * CELDA, TAM * CELDA)
    pygame.draw.rect(VENTANA, (18, 60, 96), area_tablero)
    pygame.draw.rect(VENTANA, GRID_COLOR, area_tablero, width=2)

    titulo_render = fuente_ejes.render(titulo, True, TITULO_HUD)
    titulo_rect = titulo_render.get_rect(center=(offset_x + (TAM * CELDA) // 2, offset_y - 30))
    VENTANA.blit(titulo_render, titulo_rect)

    # Ejes estilo clasico: letras arriba, numeros a la izquierda.
    for j in range(TAM):
        letra = chr(ord("A") + j)
        txt_letra = fuente_ejes.render(letra, True, EJE_HUD)
        x_letra = offset_x + j * CELDA + (CELDA - txt_letra.get_width()) // 2
        VENTANA.blit(txt_letra, (x_letra, offset_y - 18))

    for i in range(TAM):
        numero = str(i + 1)
        txt_num = fuente_ejes.render(numero, True, EJE_HUD)
        y_num = offset_y + i * CELDA + (CELDA - txt_num.get_height()) // 2
        VENTANA.blit(txt_num, (offset_x - 18, y_num))

    for i in range(TAM):
        for j in range(TAM):
            x = offset_x + j * CELDA
            y = offset_y + i * CELDA

            estado_celda = tablero[i][j]
            imagen_celda = None
            if estado_celda == "hit":
                imagen_celda = img_hit or img_casilla
            elif estado_celda == "miss":
                imagen_celda = img_miss or img_casilla

            if imagen_celda:
                VENTANA.blit(imagen_celda, (x, y))
            else:
                color = AGUA_COLOR
                if estado_celda == "hit":
                    color = ROJO
                elif estado_celda == "miss":
                    color = GRIS
                pygame.draw.rect(VENTANA, color, (x, y, CELDA, CELDA))

            pygame.draw.rect(VENTANA, GRID_COLOR, (x, y, CELDA, CELDA), 1)

    return pygame.Rect(offset_x, offset_y, TAM * CELDA, TAM * CELDA)


def obtener_layout_tableros(jugadores):
    # Layout compacto: tableros separados pero agrupados como bloque.
    x1, x2 = 170, 390
    y1, y2 = 110, 320
    if jugadores == 2:
        return [(x1, 200), (x2, 200)]
    if jugadores == 3:
        return [(x1, y1), (x2, y1), (x1, y2)]
    return [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]


def click_tablero(pos):
    if len(zonas_tableros) < 2:
        return

    zona_enemigo = zonas_tableros[1]
    x, y = pos
    if zona_enemigo.collidepoint((x, y)):
        col = (x - zona_enemigo.x) // CELDA
        fila = (y - zona_enemigo.y) // CELDA
        if 0 <= fila < TAM and 0 <= col < TAM:
            tableros_partida[indice_tablero_objetivo][fila][col] = random.choice(["hit", "miss"])


def dibujar_juego():
    global zonas_tableros

    # Vuelve al fondo original en modo tablero.
    if bg_img:
        VENTANA.blit(bg_img, (0, 0))
    else:
        VENTANA.fill(BG)

    # Encabezado HUD superior.
    cabecera = pygame.Rect(20, 16, ANCHO - 40, 42)
    pygame.draw.rect(VENTANA, (13, 37, 63), cabecera, border_radius=10)
    pygame.draw.rect(VENTANA, GRID_COLOR, cabecera, width=2, border_radius=10)
    txt_cabecera = fuente_ejes.render(
        f"BATTLESHIP COMMAND  -  TURN: 12  -  PLAYER: JUGADOR 1  -  TARGET: JUGADOR {indice_tablero_objetivo + 1}",
        True,
        TITULO_HUD,
    )
    VENTANA.blit(txt_cabecera, (30, 29))

    # Leyenda discreta.
    VENTANA.blit(fuente_ejes.render("K = impacto   N = agua", True, EJE_HUD), (34, 74))

    if resumen_config:
        info_bg = pygame.Rect(20, 602, ANCHO - 40, 28)
        pygame.draw.rect(VENTANA, (20, 40, 65), info_bg, border_radius=8)
        pygame.draw.rect(VENTANA, GRID_COLOR, info_bg, width=1, border_radius=8)
        info_config = fuente_ejes.render(resumen_config, True, TITULO_HUD)
        VENTANA.blit(info_config, (28, 610))

    # Vista compacta: siempre 2 tableros visibles (propio + objetivo).
    x_jugador, y_tableros = 80, 130
    x_objetivo = 420
    zonas_tableros = []

    zona_jugador = dibujar_tablero(tableros_partida[0], x_jugador, y_tableros, "MY FLEET", es_jugador=True)
    zonas_tableros.append(zona_jugador)

    zona_objetivo = dibujar_tablero(
        tableros_partida[indice_tablero_objetivo],
        x_objetivo,
        y_tableros,
        "ENEMY GRID",
        es_jugador=False,
    )
    zonas_tableros.append(zona_objetivo)

    if jugadores_actuales > 2:
        for b in botones_objetivo:
            b.dibujar()

    # En la pantalla de juego no se muestra el boton Menu.


# =========================
# LOOP PRINCIPAL
# =========================
while True:
    clock.tick(FPS)

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.MOUSEBUTTONDOWN:
            if estado == MENU:
                for b in botones_menu:
                    b.click(evento.pos)

            elif estado == JUEGO:
                if jugadores_actuales > 2:
                    for b in botones_objetivo:
                        b.click(evento.pos)
                click_tablero(evento.pos)

            elif estado == CONECTAR:
                for b in botones_navegacion:
                    b.click(evento.pos)
                for b in botones_conectar_agentes:
                    b.click(evento.pos)
                if input_ip_rect.collidepoint(evento.pos):
                    input_ip_activo = True
                elif not any(b.rect.collidepoint(evento.pos) for b in botones_conectar_agentes):
                    input_ip_activo = False

            elif estado == AJUSTES:
                for b in botones_ajustes:
                    b.click(evento.pos)
                for b in botones_navegacion:
                    b.click(evento.pos)

            elif estado == CONFIG_PARTIDA:
                for b in botones_config:
                    b.click(evento.pos)
                for b in botones_navegacion:
                    b.click(evento.pos)

        if evento.type == pygame.KEYDOWN and estado == CONECTAR and input_ip_activo:
            if evento.key == pygame.K_RETURN:
                ip_confirmada = ip_servidor.strip()
            elif evento.key == pygame.K_BACKSPACE:
                ip_servidor = ip_servidor[:-1]
            elif len(ip_servidor) < MAX_IP_CHARS and evento.unicode in "0123456789.":
                ip_servidor += evento.unicode

    # Dibujar según estado
    if estado == MENU:
        dibujar_menu()

    elif estado == CONECTAR:
        dibujar_conectar()

    elif estado == AJUSTES:
        dibujar_ajustes()

    elif estado == CONFIG_PARTIDA:
        dibujar_config_partida()

    elif estado == JUEGO:
        dibujar_juego()

    pygame.display.flip()