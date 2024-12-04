import cv2
import numpy as np

from deep_sort_realtime.deepsort_tracker import DeepSort
from util.util import compute_iou, convert_tlwh_to_xyxy

from ultralytics import YOLO  # YOLO 8

model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_cuda\runs\detect\kickboard_v62\weights\best.pt")
model.to('cuda')  # GPU

class_names = model.names
print(f"Class names: {class_names}")

# 추적기 초기화
tracker = DeepSort(
    max_age=5,  # 객체가 더 이상 추적 되지 않을 때의 생존 시간
    n_init=2,  # 트랙이 확정되기 위한 초기 프레임 수
    nms_max_overlap=1.0,  # NMS 임계값
    max_iou_distance=0.7,  # IOU 임계값
)

IOU_THRESHOLD = 0.4  # 킥보드와 사람의 IOU 임계값
VIOLATION_THRESHOLD = 10  # 위반으로 간주할 프레임 수
NOT_VIOLATION_THRESHOLD = 10  # 위반 오인 감지에 대한 위반 프레임 초기화 임계값
SPEED_THRESHOLD = 200  # 속도 임계값

track_history = {}

def process_frame(frame, elapsed_time):
    global track_history  # track_history를 전역 변수로 사용

    # 객체 감지
    detection = model.predict(source=frame, conf=0.4)[0]
    results = []

    if detection:
        # 검출 결과 처리
        for data in detection.boxes.data.tolist():
            confidence = float(data[4])
            xmin, ymin, xmax, ymax = map(int, data[0:4])
            class_name = class_names[int(data[5])]

            # 필요 클래스만 처리
            if class_name not in ['with_helmet', 'kickboard', 'without_helmet']:
                continue

            bbox = [xmin, ymin, xmax - xmin, ymax - ymin]  # [x, y, w, h]
            results.append((bbox, confidence, class_name))

    # 추적기 업데이트
    tracks = tracker.update_tracks(results, frame=frame)

    # 추적 종료된 객체 처리
    for track_id in list(track_history.keys()):
        if track_id not in [track.track_id for track in tracks]:
            del track_history[track_id]  # track_history에서 해당 트랙 제거
            print(f"Track ID {track_id} removed from track history")

    # 클래스별로 트랙 분류
    kickboard_tracks = [track for track in tracks if
                        track.det_class == 'kickboard' and track.is_confirmed()]
    person_tracks = [track for track in tracks if
                     track.det_class in ['with_helmet', 'without_helmet'] and track.is_confirmed()]

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        ltrb = track.to_ltrb()
        center_x = (ltrb[0] + ltrb[2]) / 2
        center_y = (ltrb[1] + ltrb[3]) / 2

        if track_id not in track_history:
            track_history[track_id] = {
                'positions': [],
                'timestamps': []
            }

        # 모든 객체의 위치 및 타임 스탬프 업데이트
        track_history[track_id]['positions'].append([center_x, center_y])
        track_history[track_id]['timestamps'].append(elapsed_time)

    # 킥보드 ID를 키로 하는 딕셔너리 생성
    for kickboard in kickboard_tracks:
        kickboard_id = kickboard.track_id
        kickboard_bbox = kickboard.to_ltrb()

        # 트랙 히스토리에 킥보드 ID가 없으면 초기화
        if 'violation_frames' not in track_history[kickboard_id]:
            track_history[kickboard_id]['violation_frames'] = 0
            track_history[kickboard_id]['not_violation_frames'] = 0
            track_history[kickboard_id]['associated_persons'] = []

        associated_persons = []

        # 사람과 연관 짓기
        for person in person_tracks:
            person_bbox = person.to_ltrb()
            iou = compute_iou(convert_tlwh_to_xyxy(person_bbox), convert_tlwh_to_xyxy(kickboard_bbox))

            # 킥보드와 사람의 속도 계산
            kickboard_speed = 0
            person_speed = 0

            if len(track_history[kickboard_id]['positions']) >= 2:
                kb_pos1 = track_history[kickboard_id]['positions'][-2]
                kb_pos2 = track_history[kickboard_id]['positions'][-1]
                kb_time1 = track_history[kickboard_id]['timestamps'][-2]
                kb_time2 = track_history[kickboard_id]['timestamps'][-1]
                kb_distance = np.hypot(kb_pos2[0] - kb_pos1[0], kb_pos2[1] - kb_pos1[1])
                kb_time_diff = kb_time2 - kb_time1
                if kb_time_diff > 0:
                    kickboard_speed = kb_distance / kb_time_diff

            if len(track_history[person.track_id]['positions']) >= 2:
                p_pos1 = track_history[person.track_id]['positions'][-2]
                p_pos2 = track_history[person.track_id]['positions'][-1]
                p_time1 = track_history[person.track_id]['timestamps'][-2]
                p_time2 = track_history[person.track_id]['timestamps'][-1]
                p_distance = np.hypot(p_pos2[0] - p_pos1[0], p_pos2[1] - p_pos1[1])
                p_time_diff = p_time2 - p_time1
                if p_time_diff > 0:
                    person_speed = p_distance / p_time_diff

            speed_difference = abs(kickboard_speed - person_speed)

            # IOU 및 속도 차이를 기준으로 연관 여부 판단
            if iou > IOU_THRESHOLD and speed_difference < SPEED_THRESHOLD:
                associated_persons.append(person)
                track_history[kickboard_id]['associated_persons'].append(person.track_id)

        # 연관된 사람의 트랙 ID 리스트로 업데이트
        track_history[kickboard_id]['associated_persons'] = [person.track_id for person in
                                                             associated_persons]

        # 위반 여부 판단
        num_persons = len(track_history[kickboard_id]['associated_persons'])
        violation = False

        # 헬멧 미착용 여부 체크
        for person in associated_persons:
            if person.det_class == 'without_helmet':
                violation = True
                break  # 한명이라도 헬멧 미착용이면 위반

        # 2인 탑승 여부 체크
        if num_persons > 1:
            violation = True

        if violation:
            track_history[kickboard_id]['violation_frames'] += 1
        else:
            track_history[kickboard_id]['not_violation_frames'] += 1

            if track_history[kickboard_id]['not_violation_frames'] >= NOT_VIOLATION_THRESHOLD:
                track_history[kickboard_id]['violation_frames'] = 0
                track_history[kickboard_id]['not_violation_frames'] = 0

        if track_history[kickboard_id]['violation_frames'] >= VIOLATION_THRESHOLD:
            # TODO: DB 연결 후 위반 사항 저장
            print(f"Violation detected for kickboard {kickboard_id}")

    # 프레임 표시
    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        class_name = track.det_class
        ltrb = track.to_ltrb()
        x1, y1, x2, y2 = map(int, ltrb)

        # 색상 및 텍스트 기본 설정
        color = (255, 255, 0)  # 기본 색상
        label = f'ID {track_id} {class_name}'

        # 개별 객체 바운딩 박스 및 텍스트 그리기
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # 킥보드와 연관된 그룹 바운딩 박스 표시
    for kickboard in kickboard_tracks:
        kickboard_id = kickboard.track_id

        if track_history[kickboard_id]['violation_frames'] >= VIOLATION_THRESHOLD:
            # 킥보드의 초기 바운딩 박스 설정
            ltrb = kickboard.to_ltrb()
            xmin, ymin, xmax, ymax = map(int, ltrb)

            associated_persons_ids = track_history[kickboard_id]['associated_persons']
            for person_id in associated_persons_ids:
                # 연관된 사람의 바운딩 박스를 가져와 그룹 바운딩 박스를 확장
                for person_track in person_tracks:
                    if person_track.track_id == person_id:
                        person_ltrb = person_track.to_ltrb()
                        x1, y1, x2, y2 = map(int, person_ltrb)

                        # 그룹 바운딩 박스 확장
                        xmin = min(xmin, x1)
                        ymin = min(ymin, y1)
                        xmax = max(xmax, x2)
                        ymax = max(ymax, y2)

            # 그룹 바운딩 박스 그리기
            cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
            cv2.putText(frame, 'VIOLATION', (xmin, ymin + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2)

    return frame
