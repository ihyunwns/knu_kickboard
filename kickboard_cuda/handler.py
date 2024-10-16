
import uuid

import cv2
import numpy as np
import websockets

from deep_sort_realtime.deepsort_tracker import DeepSort

from ultralytics import YOLO #YOLO 8

model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_cuda\runs\detect\kickboard_v4\weights\best.pt")
tracker = DeepSort(max_age=30, n_init=3, nms_max_overlap=1.0) #n_init: ? , nms_max_overlap: ?

class_names = model.names
track_history = {}

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

                    results = model.track(
                        source=r"C:\Users\ihyun\Desktop\킥보드 단속 데이터셋\test.mp4",
                        persist=True,
                        conf=0.5,
                        iou=0.5,
                        tracker='botsort.yaml' # DeepSort 트래커
                    )

                    result = results[0] # 현재 프레임 결과
                    person_tracks = []
                    kickboard_tracks = []
                    helmet_tracks = []
                    hat_tracks = []

                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                            conf = box.conf.cpu().numpy()
                            class_id = int(box.cls.cpu().numpy())

                            if box.id is not None:
                                track_id = int(box.id.cpu().numpy())
                            else:
                                track_id = None  # 또는 다른 기본값을 설정

                            class_name = class_names[class_id]
                            bbox = [x1, y1, x2, y2]

                            if class_name == 'person':
                                person_tracks.append({'track_id': track_id, 'bbox': bbox, 'conf': conf})
                            elif class_name == 'kickboard':
                                kickboard_tracks.append({'track_id': track_id, 'bbox': bbox, 'conf': conf})
                            elif class_name == 'helmet':
                                helmet_tracks.append({'track_id': track_id, 'bbox': bbox, 'conf': conf})
                            elif class_name == 'hat':
                                hat_tracks.append({'track_id': track_id, 'bbox': bbox, 'conf': conf})

                    iou_threshold = 0.3

                    # 연관성 저장
                    person_kickboard_associations = {}  # person_track_id: kickboard_track_id
                    person_helmet_associations = {}  # person_track_id: True/False

                    # 사람과 킥보드 연관시키기
                    for person in person_tracks:
                        person_id = person['track_id']
                        person_bbox = person['bbox']
                        max_iou = 0
                        associated_kickboard_id = None
                        for kickboard in kickboard_tracks:
                            kickboard_id = kickboard['track_id']
                            kickboard_bbox = kickboard['bbox']
                            iou = bbox_iou(person_bbox, kickboard_bbox)
                            if iou > max_iou:
                                max_iou = iou
                                associated_kickboard_id = kickboard_id
                        if max_iou > iou_threshold:
                            person_kickboard_associations[person_id] = associated_kickboard_id

                    # 헬멧 착용 여부 확인
                    for person in person_tracks:
                        person_id = person['track_id']
                        person_bbox = person['bbox']
                        wearing_helmet = False
                        for helmet in helmet_tracks:
                            helmet_bbox = helmet['bbox']
                            iou = bbox_iou(person_bbox, helmet_bbox)
                            if iou > iou_threshold:
                                wearing_helmet = True
                                break
                        person_helmet_associations[person_id] = wearing_helmet

                    # 트랙 히스토리 업데이트 및 위반 사항 감지
                    for person in person_tracks:
                        person_id = person['track_id']
                        if person_id not in track_history:
                            track_history[person_id] = {
                                'kickboard_associations': [],
                                'helmet_associations': [],
                                'no_helmet_frames': 0,
                                'total_frames': 0
                            }
                        # 연관성 업데이트
                        associated_kickboard_id = person_kickboard_associations.get(person_id)
                        track_history[person_id]['kickboard_associations'].append(associated_kickboard_id)
                        wearing_helmet = person_helmet_associations.get(person_id, False)
                        track_history[person_id]['helmet_associations'].append(wearing_helmet)
                        track_history[person_id]['total_frames'] += 1
                        if not wearing_helmet:
                            track_history[person_id]['no_helmet_frames'] += 1

                        # 판단 로직 (예: 10 프레임 이후)
                        if track_history[person_id]['total_frames'] >= 10:
                            no_helmet_ratio = track_history[person_id]['no_helmet_frames'] / track_history[person_id][
                                'total_frames']
                            if no_helmet_ratio > 0.6 and any(track_history[person_id]['kickboard_associations']):
                                print(f"사람 {person_id}에 대한 위반 감지: 헬멧 없이 킥보드 탑승.")
                                # 여기서 데이터베이스에 저장
                                # 카운트 초기화
                                track_history[person_id]['no_helmet_frames'] = 0
                                track_history[person_id]['total_frames'] = 0

                    # 한 킥보드에 여러 사람이 타고 있는지 확인
                    kickboard_person_counts = {}  # kickboard_track_id: 사람 ID 집합
                    for person_id, kickboard_id in person_kickboard_associations.items():
                        if kickboard_id is not None:
                            if kickboard_id not in kickboard_person_counts:
                                kickboard_person_counts[kickboard_id] = set()
                            kickboard_person_counts[kickboard_id].add(person_id)

                    for kickboard_id, person_ids in kickboard_person_counts.items():
                        if len(person_ids) > 1:
                            print(f"킥보드 {kickboard_id}에서 위반 감지: 여러 명의 탑승자 감지.")
                            # 여기서 데이터베이스에 저장


                    annotated_img = result.plot()

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
