class Barco:
    def __init__(self, tamaño, fila, columna, horizontal):
        self.tamaño = tamaño
        self.fila = fila
        self.columna = columna
        self.horizontal = horizontal
        self.impactos = set()

    def get_posiciones(self):
        posiciones = []
        if self.horizontal:
            for c in range(self.columna, self.columna + self.tamaño):
                posiciones.append((self.fila, c))
        else:
            for f in range(self.fila, self.fila + self.tamaño):
                posiciones.append((f, self.columna))
        return posiciones

    def recibir_impacto(self, fila, columna):
        bum = (fila, columna)
        if bum in self.get_posiciones():
            self.impactos.add(bum)
            return True
        return False

    def esta_hundido(self):
        return len(self.impactos) == self.tamaño


class Tablero:
    def __init__(self):
        self.barcos = []
        self.disparos = [[0 for _ in range(10)] for _ in range(10)]

    def agregar_barco(self, tamaño, fila, columna, horizontal):
        if horizontal:
            if columna + tamaño > 10:
                return False
        else:
            if fila + tamaño > 10:
                return False

        barco_nuevo = Barco(tamaño, fila, columna, horizontal)
        posiciones_nuevas = set(barco_nuevo.get_posiciones())

        for barco_existente in self.barcos:
            posiciones_existentes = set(barco_existente.get_posiciones())
            if posiciones_nuevas & posiciones_existentes:
                return False

        self.barcos.append(barco_nuevo)
        for pos in posiciones_nuevas:
            self.disparos[pos[0]][pos[1]] = 1
        return True
    

    #Estados:
    # 0: Sin disparar
    # 1: Barco sin impactar
    # 2: Barco impactado
    # 3: Agua
    # 4: Barco hundido

    def disparar(self, fila, columna):
        if not (0 <= fila < 10 and 0 <= columna < 10):
            return "invalido"

        if self.disparos[fila][columna] in (2, 3, 4):
            return "repetido"

        for barco in self.barcos:
            if barco.recibir_impacto(fila, columna):
                self.disparos[fila][columna] = 2
                if barco.esta_hundido():
                    posiciones = barco.get_posiciones()
                    for pos in posiciones:
                        self.disparos[pos[0]][pos[1]] = 4
                return "impacto"

        self.disparos[fila][columna] = 3
        return "agua"

    def todos_hundidos(self):
        if len(self.barcos) == 0:
            return False
        return all(barco.esta_hundido() for barco in self.barcos)

    def get_vista_inicial(self):
        return [fila[:] for fila in self.disparos]

    def get_vista_para_rival(self):
        tablero=self.get_vista_inicial()
        for f in range(10):
            for c in range(10):
                if tablero[f][c] == 1:
                    tablero[f][c] = 0
        return tablero
