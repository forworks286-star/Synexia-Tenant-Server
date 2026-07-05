import asyncio
import websockets
import json

async def t():
    try:
        async with websockets.connect('ws://localhost:8000/ws/alertes') as ws:
            print('Connecté...')
            while True:
                msg = await ws.recv()
                print('RECU:', json.loads(msg))
    except Exception as e:
        print('Erreur:', e)

asyncio.run(t())
