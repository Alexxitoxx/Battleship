import asyncio, argparse
from simple_agent       import AgenteSimple
from reactive_agent     import AgenteReactivo
from deliberative_agent import AgenteDeliberativo
from learning_agent     import AgenteAprendizaje

async def partida(modo):
    ag = [AgenteSimple      (url="ws://192.168.1.80:5000", nombre="Simple"),
          AgenteReactivo    (url="ws://192.168.1.80:5000", nombre="Reactivo"),
          AgenteDeliberativo(url="ws://192.168.1.80:5000", nombre="Deliberativo"),
          AgenteAprendizaje (url="ws://192.168.1.80:5000", nombre="Aprendiz")]

    async def invitado(a, delay):
        await asyncio.sleep(delay); await a.run()

    await asyncio.gather(
        ag[0].run(crear=True, nombres=[a.nombre for a in ag], modo=modo),
        invitado(ag[1], 0.6),
        invitado(ag[2], 0.9),
        invitado(ag[3], 1.2),
    )
    return ag[3]   # devuelve el DQN para guardar pesos

async def main(n, modo):
    dqn = None
    for i in range(n):
        print(f"\n── Partida {i+1}/{n} ──")
        dqn = await partida(modo)
        await asyncio.sleep(1.2)
    if dqn:
        dqn.guardar_pesos()

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--partidas', type=int, default=1)
    p.add_argument('--modo', default='clasico', choices=['clasico','extra'])
    args = p.parse_args()
    asyncio.run(main(args.partidas, args.modo))
    