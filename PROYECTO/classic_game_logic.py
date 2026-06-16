from game_logic import Tablero


class JuegoClasico:
    """Juego clásico de Battleship soportando de 2 a 4 jugadores.

    - `jugadores` es un dict {id: nombre}
    - `tableros` es un dict {id: Tablero()}
    - `turn_order` lista los ids de jugadores en orden de turno
    - `turn_index` índice dentro de `turn_order` que indica el jugador actual
    - `eliminados` conjunto de ids cuyo tablero fue hundido
    """

    barcos_requeridos = 5

    def __init__(self, nombre_jugador1, nombre_jugador2, nombre_jugador3=None, nombre_jugador4=None):
        nombres = [nombre_jugador1, nombre_jugador2]
        if nombre_jugador3:
            nombres.append(nombre_jugador3)
        if nombre_jugador4:
            nombres.append(nombre_jugador4)

        self.jugadores = {i + 1: nombres[i] for i in range(len(nombres))}
        self.tableros = {i + 1: Tablero() for i in range(len(nombres))}
        self.turn_order = list(self.jugadores.keys())
        self.turn_index = 0
        self.turno_actual = self.turn_order[self.turn_index]
        self.estado = "colocando"
        self.ganador = None
        self.historial = []
        self.eliminados = set()

    def cambiar_turno(self):
        """Avanza al siguiente jugador no eliminado en orden circular."""
        if self.estado == "terminada":
            return

        n = len(self.turn_order)
        for _ in range(n):
            self.turn_index = (self.turn_index + 1) % n
            candidato = self.turn_order[self.turn_index]
            if candidato not in self.eliminados:
                self.turno_actual = candidato
                return

    def iniciar_juego(self, force: bool = False):
        """Intento de iniciar el juego.

        Comportamiento:
        - Si algún tablero no tiene `barcos_requeridos`, devuelve False.
        - Si todos tienen los barcos requeridos y `force` es False, cambia el estado a
          `'listo'` (preparado) y devuelve False — no arranca la partida automáticamente.
        - Si `force` es True y todos tienen los barcos requeridos, cambia a `'jugando'`
          y devuelve True para indicar que la partida comenzó.
        """
        if any(len(tablero.barcos) != self.barcos_requeridos for tablero in self.tableros.values()):
            return False

        if not force:
            # Todos colocaron, pero no arrancamos automáticamente: marcamos estado 'listo'
            self.estado = "listo"
            return False

        # Forzar inicio
        self.estado = "jugando"
        self.turn_index = 0
        self.turno_actual = self.turn_order[self.turn_index]
        return True

    def disparar(self, jugador_actual, id_objetivo, fila, columna):
        """Procesa un disparo del `jugador_actual` al `id_objetivo` en (fila,columna)."""
        if jugador_actual != self.turno_actual:
            return {"resultado": "error", "mensaje": "No es tu turno"}

        if self.estado != "jugando":
            return {"resultado": "error", "mensaje": "Juego no ha iniciado"}

        if id_objetivo not in self.jugadores or id_objetivo == jugador_actual:
            return {"resultado": "error", "mensaje": "Objetivo invalido"}

        if id_objetivo in self.eliminados:
            return {"resultado": "error", "mensaje": "Objetivo ya eliminado"}

        tablero_objetivo = self.tableros[id_objetivo]
        resultado = tablero_objetivo.disparar(fila, columna)

        if resultado == "invalido":
            return {"resultado": "error", "mensaje": "Coordenadas invalidas"}

        self.historial.append(
            {
                "turno": len(self.historial) + 1,
                "jugador": jugador_actual,
                "objetivo": id_objetivo,
                "fila": fila,
                "columna": columna,
                "resultado": resultado,
            }
        )

        respuesta = {
            "resultado": resultado,
            "ganador": None,
            "objetivo_eliminado": False,
            "mensaje": f"{resultado.upper()}" if resultado in ("impacto", "agua") else "",
        }

        if tablero_objetivo.todos_hundidos():
            # marcar eliminado
            self.eliminados.add(id_objetivo)
            respuesta["objetivo_eliminado"] = True

            # comprobar si queda un solo jugador no eliminado
            vivos = [jid for jid in self.turn_order if jid not in self.eliminados]
            if len(vivos) == 1:
                self.estado = "terminada"
                self.ganador = vivos[0]
                respuesta["ganador"] = self.ganador

        # avanzar turno solo si el juego no terminó
        if self.estado != "terminada":
            self.cambiar_turno()

        return respuesta

    def obtener_jugadores_ordenados(self):
        return [(jid, self.jugadores[jid]) for jid in self.turn_order]

    @property
    def num_jugadores(self):
        return len(self.jugadores)

    def obtener_estado_juego(self):
        return {
            'estado': self.estado,
            'turno_actual': self.turno_actual,
            'num_jugadores': self.num_jugadores,
            'eliminados': list(self.eliminados),
            'historial': self.historial,
            'jugadores': self.obtener_jugadores_ordenados(),
        }

    def __str__(self):
        players = ' vs '.join(self.jugadores[jid] for jid in self.turn_order)
        return f"JuegoClasico({players}, estado={self.estado})"

