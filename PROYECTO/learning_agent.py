import os, random
import numpy as np
from collections import deque
from base_agent import AgenteBase

try:
    import torch, torch.nn as nn, torch.optim as optim
    TORCH_OK = True
except ImportError:
    TORCH_OK = False
    print("PyTorch no disponible → fallback a parity random")

if TORCH_OK:
    class RedDQN(nn.Module):
        def __init__(self):
            super().__init__()
            self.red = nn.Sequential(
                nn.Linear(100, 256), nn.ReLU(),
                nn.Linear(256, 256), nn.ReLU(),
                nn.Linear(256, 100),
            )
        def forward(self, x):
            return self.red(x)

class AgenteAprendizaje(AgenteBase):
    """
    DQN: aprende a elegir celdas óptimas por experiencia.
    Estado:  tablero aplanado → 100 floats (0 / 1 / -1)
    Acción:  índice de celda (0-99)
    Reward:  +1 impacto, -0.5 agua, +5 rival eliminado
    Guarda pesos en dqn_weights.pth entre partidas.
    """
    PESOS       = "dqn_weights.pth"
    LR          = 1e-3
    GAMMA       = 0.95
    EPS_INI     = 1.0
    EPS_MIN     = 0.10
    EPS_DECAY   = 0.995
    BUFFER      = 10_000
    BATCH       = 64
    SYNC_EACH   = 200

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._obj_actual    = None
        self._ultimo_estado = None
        self._ultima_accion = None

        if TORCH_OK:
            self.epsilon = self.EPS_INI
            self.buf     = deque(maxlen=self.BUFFER)
            self.model   = RedDQN()
            self.target  = RedDQN()
            self.opt     = optim.Adam(self.model.parameters(), lr=self.LR)
            self.loss_fn = nn.MSELoss()
            self._pasos  = 0
            self._cargar()

    def _cargar(self):
        if os.path.exists(self.PESOS):
            ck = torch.load(self.PESOS, map_location='cpu')
            self.model.load_state_dict(ck['model'])
            self.target.load_state_dict(ck['target'])
            self.epsilon = ck.get('epsilon', self.EPS_INI)
            self._pasos  = ck.get('pasos', 0)
            print(f"[{self.nombre}] Pesos cargados ε={self.epsilon:.3f}")

    def guardar_pesos(self):
        if TORCH_OK:
            torch.save({'model':self.model.state_dict(),'target':self.target.state_dict(),
                        'epsilon':self.epsilon,'pasos':self._pasos}, self.PESOS)

    def _a_estado(self, tablero):
        mapa = {0: 0.0, 2: 1.0, 3: -1.0}
        return np.array([mapa.get(tablero[f][c], 0.0)
                         for f in range(10) for c in range(10)], dtype=np.float32)

    def _elegir_idx(self, tablero):
        libres = [f*10+c for f in range(10) for c in range(10) if tablero[f][c] == 0]
        if not libres:
            return 0
        if not TORCH_OK or random.random() < self.epsilon:
            parity = [i for i in libres if (i//10 + i%10) % 2 == 0] or libres
            return random.choice(parity)
        s = torch.FloatTensor(self._a_estado(tablero)).unsqueeze(0)
        with torch.no_grad():
            q = self.model(s).squeeze(0)
        mascara = torch.full((100,), float('-inf'))
        for i in libres:
            mascara[i] = q[i]
        return int(mascara.argmax().item())

    def _entrenar(self):
        if not TORCH_OK or len(self.buf) < self.BATCH:
            return
        S,A,R,S2,D = zip(*random.sample(self.buf, self.BATCH))
        S  = torch.FloatTensor(np.array(S))
        A  = torch.LongTensor(A).unsqueeze(1)
        R  = torch.FloatTensor(R)
        S2 = torch.FloatTensor(np.array(S2))
        D  = torch.FloatTensor(D)
        q  = self.model(S).gather(1, A).squeeze(1)
        with torch.no_grad():
            qt = R + self.GAMMA * self.target(S2).max(1)[0] * (1-D)
        loss = self.loss_fn(q, qt)
        self.opt.zero_grad(); loss.backward(); self.opt.step()
        self._pasos += 1
        if self._pasos % self.SYNC_EACH == 0:
            self.target.load_state_dict(self.model.state_dict())
        self.epsilon = max(self.EPS_MIN, self.epsilon * self.EPS_DECAY)

    # ── Interfaz ─────────────────────────────────────────────
    def colocar_barcos(self):
        return self._colocar_aleatorio()

    def elegir_objetivo(self):
        rivales = self.rivales_vivos()
        if not rivales:
            return None
        def imp(jid):
            t = self._tablero_de(jid)
            return sum(t[f][c]==2 for f in range(10) for c in range(10))
        self._obj_actual = max(rivales, key=imp)
        return self._obj_actual

    def elegir_disparo(self, tablero):
        self._ultimo_estado = self._a_estado(tablero) if TORCH_OK else None
        idx = self._elegir_idx(tablero)
        self._ultima_accion = idx
        return (idx//10, idx%10)

    def on_resultado_propio(self, objetivo, fila, col, resultado, objetivo_eliminado):
        if not TORCH_OK or self._ultimo_estado is None:
            return
        r  = 5.0 if objetivo_eliminado else (1.0 if resultado=='impacto' else -0.5)
        s2 = self._a_estado(self._tablero_de(objetivo))
        self.buf.append((self._ultimo_estado, self._ultima_accion,
                         r, s2, float(objetivo_eliminado)))
        self._entrenar()