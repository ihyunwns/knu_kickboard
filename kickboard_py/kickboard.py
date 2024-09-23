import websockets

import asyncio
import ssl
from handler import handler

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=r'C:\Users\ihyun\kickboard_ssl\full_chain.crt', keyfile=r'C:\Users\ihyun\kickboard_ssl\private.key')

start_server = websockets.serve(handler, '0.0.0.0', 5000, ssl=ssl_context)
print('WebSocket 서버 시작됨')

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()