import random
import numpy as np
from base_agent import AgenteBase

class AgenteDeliberativo(AgenteBase):
    """
    Deliberativo: construye un mapa de calor antes de actuar.
    Para cada barco restante enumera TODAS las posiciones válidas
    del tablero e incrementa un contador por celda.
    Las celdas con impacto previo reciben un multiplicador ×3.
    Elige el rival + celda con mayor calor global.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._barcos_rivales = {}   # {rival_id: [4,3,3,2,2]}
        self._obj_actual     = None

    def colocar_barcos(self):
        return self._colocar_aleatorio()

    def _calcular_calor(self, tablero, barcos):
        calor = np.zeros((10, 10), dtype=float)
        for tam in barcos:
            for f in range(10):                       # horizontal
                for c in range(10 - tam + 1):
                    celdas = [(f, c+i) for i in range(tam)]
                    if all(tablero[ff][cc] != 3 for ff,cc in celdas):
                        for ff,cc in celdas:
                            calor[ff][cc] += 1
            for f in range(10 - tam + 1):             # vertical
                for c in range(10):
                    celdas = [(f+i, c) for i in range(tam)]
                    if all(tablero[ff][cc] != 3 for ff,cc in celdas):
                        for ff,cc in celdas:
                            calor[ff][cc] += 1

        mx = calor.max() or 1.0
        for f in range(10):
            for c in range(10):
                if tablero[f][c] == 2:     # impacto: prioridad máxima
                    calor[f][c] = mx * 3
                elif tablero[f][c] != 0:   # agua: no disparar aquí
                    calor[f][c] = 0.0
        return calor

    def _mejor_celda(self, rival_id):
        if rival_id not in self._barcos_rivales:
            self._barcos_rivales[rival_id] = list(self.BARCOS)
        tablero = self._tablero_de(rival_id)
        calor   = self._calcular_calor(tablero, self._barcos_rivales[rival_id])
        libres  = self.celdas_libres(tablero)
        if not libres:
            return (0, 0), 0.0
        mejor = max(libres, key=lambda rc: calor[rc[0]][rc[1]])
        return mejor, float(calor[mejor[0]][mejor[1]])

    def elegir_objetivo(self):
        rivales = self.rivales_vivos()
        if not rivales:
            return None
        self._obj_actual = max(rivales, key=lambda jid: self._mejor_celda(jid)[1])
        return self._obj_actual

    def elegir_disparo(self, tablero):
        celda, _ = self._mejor_celda(self._obj_actual)
        return celda

    def on_resultado_propio(self, objetivo, fila, col, resultado, objetivo_eliminado):
        if objetivo_eliminado:
            self._barcos_rivales[objetivo] = []