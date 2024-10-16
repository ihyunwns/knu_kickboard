import cv2
import numpy as np
from ultralytics import YOLO  # YOLOv8

from util import compute_iou, convert_tlwh_to_xyxy  # 유틸리티 함수 정의 필요

# 모델 초기화
model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_cuda\runs\detect\kickboard_v3x3\weights\best.pt")
model.to('cuda')  # GPU 사용

# 클래스 이름 확인
class_names = model.names
print(f"Class names: {class_names}")

# 설정 파라미터
CONFIDENCE_THRESHOLD = 0.5  # 신뢰도 임계값
IOU_THRESHOLD = 0.1  # 킥보드와 사람의 IOU 임계값
IOU_THRESHOLD_HELMET = 0.1  # 사람과 헬멧의 IOU 임계값
VIOLATION_THRESHOLD = 5  # 위반으로 간주할 프레임 수

track_history = {}
recorded_violations = set()  # 중복 기록 방지를 위한 집합

# 비디오 캡처
video_path = r"C:\Users\ihyun\Desktop\킥보드 단속 데이터셋\test_helmet.mp4"
cap = cv2.VideoCapture(video_path)

while cap.isOpened():

    success, frame = cap.read()
    if success:
        # 객체 추적 (YOLOv8의 내장 ByteTrack 사용)
        results = model.track(source=frame, tracker="bytetrack.yaml", persist=True)[0] # 현재 프레임에 대한 탐지 및 추적 결과

        # 추적 결과 처리
        kickboard_tracks = []
        person_tracks = []
        helmet_tracks = []

        for box in results.boxes:
            xmin, ymin, xmax, ymax = box.xyxy[0].cpu().numpy().astype(int)
            confidence = box.conf.cpu().numpy().astype(float)[0]
            class_id = int(box.cls.cpu().numpy().astype(int)[0])

            class_name = class_names[class_id]
            track_id = int(box.id.cpu().numpy().astype(int)[0]) if box.id is not None else -1  # track_id가 없을 경우 -1로 설정

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            bbox = [xmin, ymin, xmax - xmin, ymax - ymin]  # [x, y, w, h]

            # 필요 클래스만 처리
            if class_name == 'kickboard':
                kickboard_tracks.append({'track_id': track_id, 'bbox': bbox, 'confidence': confidence})
            elif class_name == 'person':
                person_tracks.append({'track_id': track_id, 'bbox': bbox, 'confidence': confidence,'has_helmet': False})
            elif class_name == 'helmet':
                helmet_tracks.append({'track_id': track_id, 'bbox': bbox, 'confidence': confidence})

        print(f"Kickboard Tracks: {kickboard_tracks}")
        print(f"Person Tracks: {person_tracks}")
        print(f"Helmet Tracks: {helmet_tracks}")

        grouped_kickboards = []

        # 킥보드별로 연관된 사람 트랙 찾기
        for kickboard in kickboard_tracks:
            kickboard_id = kickboard['track_id']
            kickboard_bbox = kickboard['bbox']

            associated_persons = []
            assigned_person_ids = set()  # 이미 할당된 사람 ID 추적

            for person in person_tracks:
                person_id = person['track_id']
                person_bbox = person['bbox']

                # 킥보드와 사람의 IOU 계산
                iou = compute_iou(convert_tlwh_to_xyxy(person_bbox), convert_tlwh_to_xyxy(kickboard_bbox))
                print(f"IOU between kickboard {kickboard_id} and person {person_id}: {iou}")

                if iou > IOU_THRESHOLD and person_id not in assigned_person_ids:
                    associated_persons.append(person)
                    assigned_person_ids.add(person_id)

            # 헬멧 착용 여부 확인
            for person in associated_persons:
                person_bbox = person['bbox']
                max_iou = 0
                closest_helmet = None
                for helmet in helmet_tracks:
                    helmet_bbox = helmet['bbox']
                    iou = compute_iou(convert_tlwh_to_xyxy(person_bbox), convert_tlwh_to_xyxy(helmet_bbox))
                    print(f"IOU between person {person['track_id']} and helmet {helmet['track_id']}: {iou}")
                    if iou > max_iou and iou > IOU_THRESHOLD_HELMET:
                        max_iou = iou
                        closest_helmet = helmet

                if closest_helmet:
                    person['has_helmet'] = True
                    print(f"Person {person['track_id']} has helmet {closest_helmet['track_id']}")

            # 그룹 생성
            group = {
                'group_id': kickboard_id,  # 킥보드의 트랙 ID를 그룹 ID로 사용
                'kickboard_track': kickboard,
                'person_tracks': associated_persons
            }

            grouped_kickboards.append(group)

        # 위반 사항 검사 및 트랙 히스토리 업데이트
        for group in grouped_kickboards:
            group_id = group['group_id']
            if group_id not in track_history:
                track_history[group_id] = {
                    'violations': 0,
                    'total_frames': 0
                }

            violation = False
            num_persons = len(group['person_tracks'])

            if num_persons > 1:
                violation = True

            for person in group['person_tracks']:
                if not person['has_helmet']:
                    violation = True
                    break  # 헬멧 미착용자 발견 시

            track_history[group_id]['total_frames'] += 1
            if violation:
                track_history[group_id]['violations'] += 1

                if track_history[group_id]['violations'] >= VIOLATION_THRESHOLD:
                    if group_id not in recorded_violations:
                        print(f"Violation detected for group {group_id}")
                        # TODO: DB에 기록하는 코드 추가
                        recorded_violations.add(group_id)


        # 프레임에 바운딩 박스 및 텍스트 그리기
        for group in grouped_kickboards:
            kickboard_bbox = convert_tlwh_to_xyxy(group['kickboard_track']['bbox'])
            cv2.rectangle(frame, (int(kickboard_bbox[0]), int(kickboard_bbox[1])),
                          (int(kickboard_bbox[2]), int(kickboard_bbox[3])),
                          (0, 0, 255), 2)  # 킥보드: 빨간색

            for person in group['person_tracks']:
                person_bbox = convert_tlwh_to_xyxy(person['bbox'])
                cv2.rectangle(frame, (int(person_bbox[0]), int(person_bbox[1])),
                              (int(person_bbox[2]), int(person_bbox[3])),
                              (0, 255, 0), 2)  # 사람: 초록색

                # 헬멧이 있는 경우 시각화
                if person['has_helmet']:
                    for helmet in helmet_tracks:
                        helmet_bbox = convert_tlwh_to_xyxy(helmet['bbox'])
                        iou = compute_iou(person_bbox, helmet_bbox)
                        if iou > IOU_THRESHOLD_HELMET:
                            cv2.rectangle(frame, (int(helmet_bbox[0]), int(helmet_bbox[1])),
                                          (int(helmet_bbox[2]), int(helmet_bbox[3])),
                                          (255, 0, 0), 2)  # 헬멧: 파란색

        # 위반 사항 표시
        for group in grouped_kickboards:
            group_id = group['group_id']
            color = (0, 255, 0)  # 기본 색상 (초록색)
            violation_status = ''

            if group_id in track_history and track_history[group_id]['violations'] >= VIOLATION_THRESHOLD:
                violation_status = 'VIOLATION'
                color = (0, 0, 255)  # 빨간색

            # 킥보드에 텍스트 추가
            kickboard_bbox = convert_tlwh_to_xyxy(group['kickboard_track']['bbox'])
            cv2.putText(frame, f'GID {group_id} {violation_status}',
                        (int(kickboard_bbox[0]), int(kickboard_bbox[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 프레임 표시
        cv2.imshow('Kickboard Violation Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    else:
        break

cap.release()
cv2.destroyAllWindows()
