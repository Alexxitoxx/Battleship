import random
from base_agent import AgenteBase

class AgenteReactivo(AgenteBase):
    """
    Reactivo Hunt & Target.
    HUNT:   dispara en patrón tablero de ajedrez (máxima cobertura).
    TARGET: cuando hay impacto, ataca las 4 celdas adyacentes.
    Objetivo: el rival con más impactos acumulados (go for the kill).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._modo        = 'hunt'
        self._cola_target = []
        self._obj_actual  = None

    def colocar_barcos(self):
        return self._colocar_aleatorio()

    def elegir_objetivo(self):
        rivales = self.rivales_vivos()
        if not rivales:
            return None

        def impactos(jid):
            t = self._tablero_de(jid)
            return sum(t[f][c] == 2 for f in range(10) for c in range(10))

        if self._modo == 'target' and self._obj_actual in rivales:
            return self._obj_actual

        self._obj_actual = max(rivales, key=impactos)
        return self._obj_actual

    def elegir_disparo(self, tablero):
        # Modo TARGET: consumir adyacentes al impacto
        while self._cola_target:
            f, c = self._cola_target.pop(0)
            if 0 <= f < 10 and 0 <= c < 10 and tablero[f][c] == 0:
                return (f, c)

        # Modo HUNT: patrón ajedrez (f+c par)
        parity = [(f, c) for f in range(10) for c in range(10)
                  if tablero[f][c] == 0 and (f + c) % 2 == 0]
        return random.choice(parity or self.celdas_libres(tablero))

    def on_resultado_propio(self, objetivo, fila, col, resultado, objetivo_eliminado):
        if objetivo_eliminado:
            self._cola_target.clear()
            self._modo = 'hunt'
            return
        if resultado == 'impacto':
            self._modo = 'target'
            for df, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nf, nc = fila+df, col+dc
                if 0 <= nf < 10 and 0 <= nc < 10 and (nf,nc) not in self._cola_target:
                    self._cola_target.append((nf, nc))
        elif not self._cola_target:
            self._modo = 'hunt'