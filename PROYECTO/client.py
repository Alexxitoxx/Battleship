import asyncio
import websockets
import json
import argparse

class ClienteBattleship:
    def __init__(self, url="ws://localhost:8765"):
        self.url = url
        self.websocket = None
        self.jugador_id = None
        self.response_queue = asyncio.Queue()

    async def conectar(self):
        try:
            self.websocket = await websockets.connect(self.url)
            print(f"Conectado a {self.url}")
            return True
        except Exception as e:
            print(f"Error al conectar: {e}")
            return False

    async def crear_juego(self, nombre_j1, nombre_j2, nombre_j3=None, nombre_j4=None, modo='clasico'):
        mensaje = {
            'accion': 'crear_juego',
            'nombre_j1': nombre_j1,
            'nombre_j2': nombre_j2,
            'nombre_j3': nombre_j3,
            'nombre_j4': nombre_j4,
            'modo': modo
        }
        await self.websocket.send(json.dumps(mensaje))
        respuesta = await self.response_queue.get()
        print(f"\n{respuesta.get('mensaje')}")
        return respuesta

    async def unirse_juego(self, nombre=''):
        mensaje = {'accion': 'unirse_juego'}
        if nombre:
            mensaje['nombre_jugador'] = nombre
        await self.websocket.send(json.dumps(mensaje))
        respuesta = await self.response_queue.get()
        self.jugador_id = respuesta.get('jugador_id')
        print(f"\n{respuesta.get('mensaje')}")
        return respuesta
    async def colocar_barco(self, tamaño, fila, columna, horizontal):
        mensaje = {
            'accion': 'colocar_barco',
            'tamaño': tamaño,
            'fila': fila,
            'columna': columna,
            'horizontal': horizontal
        }
        await self.websocket.send(json.dumps(mensaje))
        respuesta = await self.response_queue.get()
        print(f"Barco: {respuesta.get('mensaje')}")
        return respuesta

    async def iniciar_partida(self):
        mensaje = {'accion': 'iniciar'}
        await self.websocket.send(json.dumps(mensaje))
        print("Solicitud de inicio enviada")

    async def disparar(self, objetivo, fila, columna):
        mensaje = {
            'accion': 'disparar',
            'objetivo': objetivo,
            'fila': fila,
            'columna': columna
        }
        await self.websocket.send(json.dumps(mensaje))
        respuesta = await self.response_queue.get()
        print(f"Disparo ({fila},{columna}): {respuesta.get('resultado','').upper()}")
        if respuesta.get('ganador'):
            print(f"¡GANADOR! Jugador {respuesta.get('ganador')}")
        return respuesta

    async def obtener_estado(self):
        mensaje = {'accion': 'obtener_estado'}
        await self.websocket.send(json.dumps(mensaje))
        respuesta = await self.response_queue.get()
        return respuesta

    async def escuchar_eventos(self):
        """Lee todos los mensajes del servidor, los encola para que respuestas se reciban, y muestra eventos."""
        try:
            async for mensaje in self.websocket:
                datos = json.loads(mensaje)
                tipo = datos.get('tipo')
                
                # Mostrar eventos informativos
                if tipo == 'jugador_desconectado':
                    print(f"\n{datos.get('mensaje')}")
                    await self.response_queue.put(datos)
                elif tipo == 'juego_creado':
                    print(f"\n{datos.get('mensaje')}")
                    await self.response_queue.put(datos)
                elif tipo == 'jugador_unido':
                    print(f"\n{datos.get('mensaje')}")
                    await self.response_queue.put(datos)
                elif tipo == 'juego_iniciado':
                    print(f"\n{datos.get('mensaje')}")
                    print(f"Turno actual: Jugador {datos.get('turno_actual')}")
                    await self.response_queue.put(datos)
                elif tipo == 'jugador_listo':
                    print(f"\n{datos.get('mensaje')}")
                    await self.response_queue.put(datos)
                elif tipo == 'juego_listo':
                    print(f"\n{datos.get('mensaje')}")
                    await self.response_queue.put(datos)
                elif tipo == 'resultado_disparo':
                    print(f"\nResultado: {datos.get('resultado','').upper()}")
                    print(f"Turno actual: Jugador {datos.get('turno_actual')}")
                    if datos.get('ganador'):
                        print(f"¡GANADOR! Jugador {datos.get('ganador')}")
                    await self.response_queue.put(datos)
                elif tipo == 'barco_colocado' or tipo == 'barco_error':
                    await self.response_queue.put(datos)
                elif tipo == 'estado_juego':
                    await self.response_queue.put(datos)
                elif tipo == 'error':
                    print(f"\nError: {datos.get('mensaje')}")
                    await self.response_queue.put(datos)
                else:
                    # Encolar cualquier respuesta no reconocida
                    await self.response_queue.put(datos)
        except websockets.exceptions.ConnectionClosed:
            print("\nConexión cerrada")
        except Exception as e:
            print(f"\nError en escuchar_eventos: {e}")


async def run_from_args(args):
    cliente = ClienteBattleship(args.server)
    if not await cliente.conectar():
        return

    # Iniciar escucha de eventos en background PRIMERO
    asyncio.create_task(cliente.escuchar_eventos())
    await asyncio.sleep(0.1)

    if args.create:
        if not args.create_names:
            print('Para crear, pasa --create-names con al menos dos nombres (ej: "Alice,Bob")')
            return
        create_names = [n.strip() for n in args.create_names.split(',') if n.strip()]
        while len(create_names) < 4:
            create_names.append(None)
        await cliente.crear_juego(create_names[0], create_names[1], create_names[2], create_names[3], args.modo)
        await cliente.unirse_juego(args.name)
    else:
        await cliente.unirse_juego(args.name)

    if args.auto:
        await asyncio.sleep(0.5)
        await cliente.colocar_barco(4, 0, 0, True)
        await cliente.colocar_barco(3, 2, 0, True)
        await cliente.colocar_barco(3, 4, 0, True)
        await cliente.colocar_barco(2, 6, 0, True)
        await cliente.colocar_barco(2, 8, 0, True)
        # No marcar listo manualmente: el servidor marcará automáticamente al colocar el 5.º barco
        if getattr(args, 'auto_start', False):
            await asyncio.sleep(0.5)
            await cliente.iniciar_partida()
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cliente Battleship (crear o unirse)')
    parser.add_argument('--server', default='ws://192.168.1.80:5000', help='URL del servidor')
    parser.add_argument('--create', action='store_true', help='Crear partida')
    parser.add_argument('--name', help='Nombre del jugador')
    parser.add_argument('--create-names', help='Nombres (coma-separados): "Alice,Bob,Carol"')
    parser.add_argument('--modo', default='clasico', choices=['clasico', 'extra'], help='Modo de juego')
    parser.add_argument('--auto', action='store_true', help='Auto-colocar barcos')
    parser.add_argument('--auto-start', action='store_true', help='Auto-iniciar tras colocar barcos')
    args = parser.parse_args()

    try:
        asyncio.run(run_from_args(args))
    except KeyboardInterrupt:
        print('\nInterrumpido por el usuario')
