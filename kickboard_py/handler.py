import json
import uuid
from os import times

import cv2
import numpy as np
import websockets

import detect

async def handler(websocket, path):
    client_id = str(uuid.uuid4())  # 고유한 UUID를 사용하여 클라이언트 식별
    window_name = f"Client {client_id}"  # 창 이름에 고유 ID 추가

    print(f"클라이언트 {client_id} 연결됨")
    try:
        while True:
            message = await websocket.recv()
            print()

            if isinstance(message, bytes):
                # 이미지 복원
                nparr = np.frombuffer(message, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is not None:
                    # 이미지 처리
                    is_wearing_helmet = detect.helmet(img)
                    is_two_riders = detect.two_riders(img)

                    cv2.imshow(window_name, img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                    # 결과 출력
                    print(f'{client_id}: 헬멧 착용 여부: {is_wearing_helmet}, 2인 탑승 여부: {is_two_riders}')

                    # 필요 시 클라이언트로 결과 전송
                    # await websocket.send(f'헬멧 착용 여부: {is_wearing_helmet}, 2인 탑승 여부: {is_two_riders}')
                else:
                    print('이미지 복원 실패')
            else:
                print('텍스트 메시지 수신:', message)
    except websockets.exceptions.ConnectionClosed:
        print(f'클라이언트 {client_id} 연결 종료')
    finally:
        cv2.destroyAllWindows()
