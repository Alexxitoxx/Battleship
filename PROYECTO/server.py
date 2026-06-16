import asyncio
import websockets
import json
import traceback
from classic_game_logic import JuegoClasico as JuegoClasicoClassic
from extra import JuegoClasicoExtra

# Modos soportados
AVAILABLE_MODES = ['clasico', 'extra']

# Única partida activa
juego_actual = None
clientes_activos = {}  # {jugador_id: websocket}
listo_flags = {}       # {jugador_id: bool}

async def manejar_cliente(websocket, path=None):
    """Maneja conexiones de clientes"""
    global juego_actual
    jugador_id = None
    
    try:
        async for mensaje in websocket:
            datos = json.loads(mensaje)
            accion = datos.get('accion')
            
            # ===== CREAR JUEGO =====
            if accion == 'crear_juego':
                if juego_actual is not None:
                    await websocket.send(json.dumps({
                        'tipo': 'error',
                        'mensaje': 'Ya hay una partida activa'
                    }))
                    continue
                
                nombre_j1 = datos['nombre_j1']
                nombre_j2 = datos['nombre_j2']
                nombre_j3 = datos.get('nombre_j3')
                nombre_j4 = datos.get('nombre_j4')
                modo = datos.get('modo', 'clasico')
                
                if modo not in AVAILABLE_MODES:
                    await websocket.send(json.dumps({'tipo': 'error', 'mensaje': f'Modo inválido. Modos válidos: {AVAILABLE_MODES}'}))
                    continue

                JuegoClass = JuegoClasicoClassic if modo == 'clasico' else JuegoClasicoExtra
                juego_actual = JuegoClass(nombre_j1, nombre_j2, nombre_j3, nombre_j4) if nombre_j3 else JuegoClass(nombre_j1, nombre_j2)
                
                # Inicializar clientes
                for i in range(1, juego_actual.num_jugadores + 1):
                    clientes_activos[i] = None
                    listo_flags[i] = False

                respuesta = {
                    'tipo': 'juego_creado',
                    'num_jugadores': juego_actual.num_jugadores,
                    'modo': modo,
                    'mensaje': f'Juego creado (modo={modo}). Esperando {juego_actual.num_jugadores} jugador(es)...'
                }
                await websocket.send(json.dumps(respuesta))
                print(f"Juego creado (modo={modo}, {juego_actual.num_jugadores} jugadores)")
            
            # Validar que existe juego para el resto de acciones
            if accion != 'crear_juego' and juego_actual is None:
                await websocket.send(json.dumps({
                    'tipo': 'error',
                    'mensaje': 'No hay juego activo'
                }))
                continue
            if accion == 'unirse_juego':
                nombre_jugador = datos.get('nombre_jugador', '')
                
                # Buscar primer slot disponible
                for i in range(1, juego_actual.num_jugadores + 1):
                    if clientes_activos[i] is None:
                        jugador_id = i
                        break
                else:
                    await websocket.send(json.dumps({'tipo': 'error', 'mensaje': 'Juego lleno'}))
                    continue
                
                clientes_activos[jugador_id] = websocket
                if not nombre_jugador:
                    nombre_jugador = f"Jugador{jugador_id}"
                juego_actual.jugadores[jugador_id] = nombre_jugador
                
                # Notificar a todos
                respuesta = {
                    'tipo': 'jugador_unido',
                    'jugador_id': jugador_id,
                    'nombre': nombre_jugador,
                    'mensaje': f'¡Jugador {jugador_id} ({nombre_jugador}) se ha unido!'
                }
                for jid in range(1, juego_actual.num_jugadores + 1):
                    if clientes_activos[jid]:
                        r = respuesta.copy()
                        r['tu_jugador_id'] = jid
                        await clientes_activos[jid].send(json.dumps(r))
                print(f"Jugador {jugador_id} ({nombre_jugador}) se unió")
            
            # ===== COLOCAR BARCO =====
            elif accion == 'colocar_barco':
                tamaño = datos['tamaño']
                fila = datos['fila']
                columna = datos['columna']
                horizontal = datos['horizontal']
                
                exito = juego_actual.tableros[jugador_id].agregar_barco(tamaño, fila, columna, horizontal)
                num_barcos = len(juego_actual.tableros[jugador_id].barcos)
                
                respuesta = {
                    'tipo': 'barco_colocado' if exito else 'barco_error',
                    'exito': exito,
                    'barcos_colocados': num_barcos,
                    'mensaje': f'Barco {num_barcos}/{juego_actual.barcos_requeridos}' if exito else 'Posición inválida'
                }
                await websocket.send(json.dumps(respuesta))
                
                # Si el jugador llegó a 5 barcos, marcarlo automáticamente como listo
                if exito and num_barcos == juego_actual.barcos_requeridos:
                    listo_flags[jugador_id] = True
                    for jid in range(1, juego_actual.num_jugadores + 1):
                        if clientes_activos[jid]:
                            await clientes_activos[jid].send(json.dumps({'tipo': 'jugador_listo', 'jugador_id': jugador_id}))
                    
                    # Si todos listos, cambiar estado a 'listo'
                    if all(listo_flags[i] for i in range(1, juego_actual.num_jugadores + 1)):
                        juego_actual.iniciar_juego(force=False)
                        for jid in range(1, juego_actual.num_jugadores + 1):
                            if clientes_activos[jid]:
                                await clientes_activos[jid].send(json.dumps({'tipo': 'juego_listo', 'mensaje': 'Todos listos. Esperando inicio.'}))
            


            # ===== INICIAR PARTIDA =====
            elif accion == 'iniciar':
                if juego_actual.iniciar_juego(force=True):
                    respuesta = {
                        'tipo': 'juego_iniciado',
                        'turno_actual': juego_actual.turno_actual,
                        'mensaje': '¡El juego ha comenzado!'
                    }
                    for jid in range(1, juego_actual.num_jugadores + 1):
                        if clientes_activos[jid]:
                            await clientes_activos[jid].send(json.dumps(respuesta))
                    print(f"Juego iniciado")
                else:
                    await websocket.send(json.dumps({
                        'tipo': 'error',
                        'mensaje': f'No se puede iniciar: cada jugador debe tener {juego_actual.barcos_requeridos} barcos'
                    }))
            
            # ===== DISPARAR =====
            elif accion == 'disparar':
                objetivo = datos['objetivo']
                fila = datos['fila']
                columna = datos['columna']
                
                resultado = juego_actual.disparar(jugador_id, objetivo, fila, columna)
                
                # respuesta = {
                #     'tipo': 'resultado_disparo',
                #     'resultado': resultado['resultado'],
                #     'turno_actual': juego_actual.turno_actual,
                #     'ganador': resultado.get('ganador')
                # }
                respuesta = {
                    'tipo':               'resultado_disparo',
                    'atacante':           jugador_id,          # ← agregar
                    'objetivo':           objetivo,            # ← agregar
                    'fila':               fila,                # ← agregar
                    'columna':            columna,             # ← agregar
                    'resultado':          resultado['resultado'],
                    'turno_actual':       juego_actual.turno_actual,
                    'ganador':            resultado.get('ganador'),
                    'objetivo_eliminado': resultado.get('objetivo_eliminado', False),  # ← agregar
                }
                
                # Enviar a todos
                for jid in range(1, juego_actual.num_jugadores + 1):
                    if clientes_activos[jid]:
                        await clientes_activos[jid].send(json.dumps(respuesta))
                print(f"J{jugador_id} → J{objetivo} ({fila},{columna}): {resultado['resultado']}")
            
            # ===== OBTENER ESTADO =====
            elif accion == 'obtener_estado':
                respuesta = {
                    'tipo': 'estado_juego',
                    'estado': juego_actual.obtener_estado_juego()
                }
                await websocket.send(json.dumps(respuesta))
    
    except websockets.exceptions.ConnectionClosed:
        print(f"Cliente desconectado")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        try:
            await websocket.send(json.dumps({
                'tipo': 'error',
                'mensaje': f'Error del servidor: {str(e)}'
            }))
        except Exception:
            pass
    finally:
        # Liberar slot del cliente desconectado
        for pid in list(clientes_activos.keys()):
            if clientes_activos[pid] is websocket:
                clientes_activos[pid] = None
                listo_flags[pid] = False
                print(f"Jugador {pid} desconectado")
                # Notificar a otros
                for jid in range(1, juego_actual.num_jugadores + 1) if juego_actual else []:
                    if clientes_activos[jid]:
                        try:
                            await clientes_activos[jid].send(json.dumps({'tipo': 'jugador_desconectado', 'jugador_id': pid}))
                        except:
                            pass
        
        # Si todos desconectados, limpiar
        if juego_actual and all(v is None for v in clientes_activos.values()):
            juego_actual = None
            clientes_activos.clear()
            listo_flags.clear()
            print("Partida eliminada")

async def main():
    async with websockets.serve(manejar_cliente, "10.100.91.112", 5000):
        print("=" * 50)
        print("SERVIDOR BATTLESHIP INICIADO")
        print("=" * 50)
        print("Escuchando en ws://10.100.91.112:5000")
        print("Para conectar localmente: ws://localhost:8765")
        print("=" * 50)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
