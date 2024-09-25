
import uuid

import cv2
import numpy as np
import websockets

from ultralytics import YOLO #YOLO 8


model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_cuda\runs\detect\grayscale_v4\weights\best.pt")
model.to('cuda')

async def handler(websocket, path):
    client_id = str(uuid.uuid4())  # 고유한 UUID를 사용하여 클라이언트 식별
    window_name = f"Client {client_id}"  # 창 이름에 고유 ID 추가

    print(f"클라이언트 {client_id} 연결됨")
    try:
        while True:
            message = await websocket.recv()

            if isinstance(message, bytes):
                # 이미지 복원
                nparr = np.frombuffer(message, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is not None:
                    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    gray_3channel = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)

                    result = model.predict(gray_3channel, conf=0.6)

                    annotated_img = result[0].plot()

                    cv2.imshow(window_name, annotated_img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                    success, encoded_image = cv2.imencode('.jpg', annotated_img)
                    if success:
                        await websocket.send(encoded_image.tobytes())
                    else:
                        print('Annotated 이미지 인코딩 실패')

                else:
                    print('이미지 복원 실패')
            else:
                print('텍스트 메시지 수신:', message)
    except websockets.exceptions.ConnectionClosed:
        print(f'클라이언트 {client_id} 연결 종료')
    finally:
        cv2.destroyAllWindows()
