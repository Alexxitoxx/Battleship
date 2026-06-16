import asyncio
import websockets
import json
import random

class AgenteBase:
    BARCOS = [4, 3, 3, 2, 2]

    def __init__(self, url="ws://localhost:8765", nombre="Agente"):
        self.url                 = url
        self.nombre              = nombre
        self.websocket           = None
        self.mi_id               = None
        self.jugadores_vivos     = []
        self.tableros_observados = {}  # {rival_id: [[0/2/3]*10]*10}
        self.turno_actual        = None
        self.estado              = "esperando"
        self._es_creador         = False

    # ── Los 3 métodos que cada agente sobreescribe ──────────
    def colocar_barcos(self) -> list:
        raise NotImplementedError

    def elegir_objetivo(self) -> int:
        raise NotImplementedError

    def elegir_disparo(self, tablero: list) -> tuple:
        # tablero[f][c]: 0=libre, 2=impacto, 3=agua
        raise NotImplementedError

    def on_resultado_propio(self, objetivo, fila, col, resultado, objetivo_eliminado):
        pass  # opcional: para agentes que aprenden o llevan estado

    # ── Helpers ─────────────────────────────────────────────
    def celdas_libres(self, tablero):
        return [(f, c) for f in range(10) for c in range(10) if tablero[f][c] == 0]

    def rivales_vivos(self):
        return [j for j in self.jugadores_vivos if j != self.mi_id]

    def _tablero_de(self, rival_id):
        if rival_id not in self.tableros_observados:
            self.tableros_observados[rival_id] = [[0]*10 for _ in range(10)]
        return self.tableros_observados[rival_id]

    def _colocar_aleatorio(self):
        ocupadas, resultado = set(), []
        for tamaño in self.BARCOS:
            for _ in range(2000):
                h = random.choice([True, False])
                f = random.randint(0, 9 if h else 10 - tamaño)
                c = random.randint(0, 10 - tamaño if h else 9)
                pos = [(f, c+i) if h else (f+i, c) for i in range(tamaño)]
                if not any(p in ocupadas for p in pos):
                    resultado.append((tamaño, pos[0][0], pos[0][1], h))
                    ocupadas.update(pos)
                    break
        return resultado

    async def _enviar(self, msg):
        await self.websocket.send(json.dumps(msg))

    async def _hacer_disparo(self):
        if not self.rivales_vivos():
            return
        objetivo  = self.elegir_objetivo()
        fila, col = self.elegir_disparo(self._tablero_de(objetivo))
        print(f"[{self.nombre}] → J{objetivo} ({fila},{col})")
        await self._enviar({'accion':'disparar','objetivo':objetivo,'fila':fila,'columna':col})

    # ── Loop de eventos ─────────────────────────────────────
    async def _loop_eventos(self):
        async for msg in self.websocket:
            datos = json.loads(msg)
            tipo  = datos.get('tipo')

            if tipo == 'jugador_unido':
                self.mi_id = datos.get('tu_jugador_id')

            elif tipo == 'juego_listo':
                if self._es_creador:
                    await asyncio.sleep(0.3)
                    await self._enviar({'accion': 'iniciar'})

            elif tipo == 'juego_iniciado':
                self.turno_actual = datos.get('turno_actual')
                self.estado = 'jugando'
                await self._enviar({'accion': 'obtener_estado'})

            elif tipo == 'estado_juego':
                est       = datos.get('estado', {})
                jugadores = est.get('jugadores', [])
                eliminados = set(est.get('eliminados', []))
                self.jugadores_vivos = [j for j, _ in jugadores if j not in eliminados]
                for jid, _ in jugadores:
                    if jid != self.mi_id:
                        self._tablero_de(jid)
                if self.estado == 'jugando' and self.turno_actual == self.mi_id:
                    await asyncio.sleep(0.15)
                    await self._hacer_disparo()

            elif tipo == 'resultado_disparo':
                atacante           = datos.get('atacante')
                objetivo           = datos.get('objetivo')
                fila               = datos.get('fila')
                col                = datos.get('columna')
                resultado          = datos.get('resultado')
                objetivo_eliminado = datos.get('objetivo_eliminado', False)

                if atacante == self.mi_id and objetivo in self.tableros_observados:
                    self.tableros_observados[objetivo][fila][col] = 2 if resultado == 'impacto' else 3
                    self.on_resultado_propio(objetivo, fila, col, resultado, objetivo_eliminado)

                if objetivo_eliminado and objetivo in self.jugadores_vivos:
                    self.jugadores_vivos.remove(objetivo)

                if datos.get('ganador'):
                    g = datos.get('ganador')
                    print(f"[{self.nombre}] {'¡GANÉ!' if g == self.mi_id else f'Ganó J{g}'}")
                    self.estado = 'terminado'
                    break

                self.turno_actual = datos.get('turno_actual')
                if self.turno_actual == self.mi_id:
                    await asyncio.sleep(0.15)
                    await self._hacer_disparo()

    # ── Punto de entrada ─────────────────────────────────────
    async def run(self, crear=False, nombres=None, modo='clasico'):
        self.websocket = await websockets.connect(self.url)
        tarea = asyncio.create_task(self._loop_eventos())

        if crear:
            self._es_creador = True
            nombres = nombres or ['A1','A2','A3','A4']
            await self._enviar({
                'accion':'crear_juego', 'nombre_j1':nombres[0],
                'nombre_j2':nombres[1],
                'nombre_j3':nombres[2] if len(nombres)>2 else None,
                'nombre_j4':nombres[3] if len(nombres)>3 else None,
                'modo':modo
            })
            await asyncio.sleep(0.3)

        await self._enviar({'accion':'unirse_juego','nombre_jugador':self.nombre})
        await asyncio.sleep(0.3)

        for tamaño, fila, col, horiz in self.colocar_barcos():
            await self._enviar({'accion':'colocar_barco','tamaño':tamaño,
                                'fila':fila,'columna':col,'horizontal':horiz})
            await asyncio.sleep(0.1)

        await tarea