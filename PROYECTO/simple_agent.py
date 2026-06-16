from base_agent import AgenteBase

class AgenteSimple(AgenteBase):
    """
    Reflejo simple: sin memoria ni estrategia.
    Barcos siempre en las mismas posiciones fijas.
    Objetivo: round-robin entre rivales vivos.
    Disparo: barrido fila por fila (0,0) → (9,9).
    """
    _BARCOS_FIJOS = [
        (4, 0, 0, True),
        (3, 2, 0, True),
        (3, 4, 0, True),
        (2, 6, 0, True),
        (2, 8, 0, True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._idx_objetivo = 0

    def colocar_barcos(self):
        return self._BARCOS_FIJOS

    def elegir_objetivo(self):
        rivales = self.rivales_vivos()
        if not rivales:
            return None
        self._idx_objetivo %= len(rivales)
        obj = rivales[self._idx_objetivo]
        self._idx_objetivo = (self._idx_objetivo + 1) % len(rivales)
        return obj

    def elegir_disparo(self, tablero):
        for f in range(10):
            for c in range(10):
                if tablero[f][c] == 0:
                    return (f, c)