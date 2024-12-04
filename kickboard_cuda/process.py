import cv2
import numpy as np
import time

from deep_sort_realtime.deepsort_tracker import DeepSort

from util.save import save_violation_db, save_violation_image
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

            bbox = [xmin, ymin, xmax-xmin, ymax-ymin] # [x, y, w, h]
            results.append((bbox, confidence, class_name))

    # 추적기 업데이트
    tracks = tracker.update_tracks(results, frame=frame)
    # tracks 리스트에는 현재 프레임에서 추적되고 있는 객체들의 현재 상태만을 포함한다.
    # 각 track 객체는 현재 위치와 클래스 정보 등을 담고 있는데 추적 중인 객체의 고유 ID를 가지고 있으며, 이 ID를 통해 동일한 객체를 여러 프레임에 걸쳐 식별할 수 있다.

    # 추적 종료된 객체 처리
    for track_id in list(track_history.keys()):
        # 만약 현재 추적 중인 트랙 리스트에 track_id가 없다면, 해당 트랙이 추적 종료된 것으로 간주
        if track_id not in [track.track_id for track in tracks]:

            violation_types = []
            violation_durations = {}
            violation_start_times = {}
            if track_history[track_id]['helmet_violation_ongoing']:
                violation_duration = time.time() - track_history[track_id]['helmet_violation_start_time']
                violation_types.append('HELMET')
                violation_durations['HELMET'] = violation_duration
                violation_start_times['HELMET'] = track_history[track_id]['helmet_violation_start_time']
                print(f"킥보드 {track_id} 헬멧 미착용 위반 종료 (추적 종료), 지속 시간: {violation_duration}초")


            if track_history[track_id]['overload_violation_ongoing']:
                violation_duration = time.time() - track_history[track_id]['overload_violation_start_time']
                violation_types.append('2-PERSON')
                violation_durations['2-PERSON'] = violation_duration
                violation_start_times['2-PERSON'] = track_history[track_id]['overload_violation_start_time']
                print(f"킥보드 {track_id} 2인 탑승 위반 종료 (추적 종료), 지속 시간: {violation_duration}초")

            if violation_types:
                if len(violation_types) == 2:
                    violation_type = 'BOTH'
                    violation_duration = max(violation_durations.values())
                    violation_date = min(violation_start_times.values())
                else:
                    violation_type = violation_types[0]
                    violation_duration = violation_durations[violation_type]
                    violation_date = violation_start_times[violation_type]

                image_url = track_history[track_id]['saved_image_folder']
                save_violation_db(str(track_id), violation_type, violation_date, violation_duration, image_url)

            del track_history[track_id]  # track_history에서 해당 트랙 제거

            print(f"Track ID {track_id} removed from track history")

    # 클래스별로 트랙 분류, # tracks 리스트에서 클래스 이름과 is_confirmed 인것만 골라서 트랙에 저장
    kickboard_tracks = [track for track in tracks if track.det_class == 'kickboard' and track.is_confirmed()]
    person_tracks = [track for track in tracks if track.det_class in ['with_helmet', 'without_helmet'] and track.is_confirmed()]

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
                'timestamps': [],
                'associated_persons': [],

                # 위반 사항 포착 프레임
                'helmet_violation_frames': 0,
                'overload_violation_frames': 0,
                'non_helmet_violation_frames': 0,
                'non_overload_violation_frames': 0,

                # 위반 사항 기록 플래그
                'helmet_violation_ongoing': False,
                'overload_violation_ongoing': False,

                'helmet_violation_start_time': None,
                'overload_violation_start_time': None,

                'saved_image_folder' : None
            }

        # 모든 객체의 위치 및 타임 스탬프 업데이트
        track_history[track_id]['positions'].append([center_x, center_y])
        track_history[track_id]['timestamps'].append(elapsed_time)

    # 킥보드 ID를 키로 하는 딕셔너리 생성
    for kickboard in kickboard_tracks:
        kickboard_id = kickboard.track_id
        kickboard_bbox = kickboard.to_ltrb()

        associated_persons = []

        # 사람과 연관 짓기
        for person in person_tracks:
            person_bbox = person.to_ltrb()
            iou = compute_iou(convert_tlwh_to_xyxy(person_bbox), convert_tlwh_to_xyxy(kickboard_bbox))

            # 킥보드와 사람의 속도 계산
            kickboard_speed = 0
            person_speed = 0

            if len(track_history[kickboard_id]['positions']) >= 2: # 킥보드 위치 데이터가 2개 이상 있는 지

                kb_pos1 = track_history[kickboard_id]['positions'][-2] # 킥보드의 직전 위치
                kb_pos2 = track_history[kickboard_id]['positions'][-1] # 킥보드의 현재 위치

                kb_time1 = track_history[kickboard_id]['timestamps'][-2] # 킥보드의 직전 타임 스탬프
                kb_time2 = track_history[kickboard_id]['timestamps'][-1] # 킥보드의 현재 타임 스탬프

                # x축 거리 차이, y축 거리 차이를 이용한 두 점 사이의 직선 거리
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
        track_history[kickboard_id]['associated_persons'] = [person.track_id for person in associated_persons]

        # 위반 여부 판단
        num_persons = len(track_history[kickboard_id]['associated_persons'])

        helmet_violation = False
        overload_violation = False
        # 헬멧 미착용 여부 체크
        for person in associated_persons:
            if person.det_class == 'without_helmet':
                helmet_violation = True
                break # 한명이라도 헬멧 미착용이면 위반

        # 2인 탑승 여부 체크
        if num_persons > 1:
            overload_violation = True

        need_to_save_frame = False

        if helmet_violation:
            track_history[kickboard_id]['helmet_violation_frames'] += 1
            track_history[kickboard_id]['non_helmet_violation_frames'] = 0

            if track_history[kickboard_id]['helmet_violation_frames'] >= VIOLATION_THRESHOLD:
                if not track_history[kickboard_id]['helmet_violation_ongoing']:
                    # 위반이 처음 시작 됨
                    track_history[kickboard_id]['helmet_violation_ongoing'] = True
                    track_history[kickboard_id]['helmet_violation_start_time'] = time.time()
                    print(f"킥보드 {kickboard_id} 헬멧 미착용 위반 시작")

                need_to_save_frame = True

        else:
            track_history[kickboard_id]['non_helmet_violation_frames'] += 1

            if track_history[kickboard_id]['non_helmet_violation_frames'] >= NOT_VIOLATION_THRESHOLD:

                track_history[kickboard_id]['helmet_violation_frames'] = 0
                track_history[kickboard_id]['non_helmet_violation_frames'] = 0


        if overload_violation:
            track_history[kickboard_id]['overload_violation_frames'] += 1
            track_history[kickboard_id]['non_overload_violation_frames'] = 0
            if track_history[kickboard_id]['overload_violation_frames'] >= VIOLATION_THRESHOLD:
                if not track_history[kickboard_id]['overload_violation_ongoing']:
                    # 위반이 처음 시작 됨
                    track_history[kickboard_id]['overload_violation_ongoing'] = True
                    track_history[kickboard_id]['overload_violation_start_time'] = time.time()
                    print(f"킥보드 {kickboard_id} 2인 탑승 위반 시작")

                need_to_save_frame = True
        else:
            track_history[kickboard_id]['non_overload_violation_frames'] += 1

            if track_history[kickboard_id]['non_overload_violation_frames'] >= NOT_VIOLATION_THRESHOLD:

                track_history[kickboard_id]['overload_violation_frames'] = 0
                track_history[kickboard_id]['non_overload_violation_frames'] = 0

        if need_to_save_frame:
            folder = save_violation_image(kickboard_id, frame, elapsed_time, time.localtime())
            if track_history[kickboard_id]['saved_image_folder'] is None:
                track_history[kickboard_id]['saved_image_folder'] = folder
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

        if track_history[kickboard_id]['helmet_violation_frames'] >= VIOLATION_THRESHOLD or track_history[kickboard_id]['overload_violation_frames'] >= VIOLATION_THRESHOLD:
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
            cv2.putText(frame, 'VIOLATION', (xmin, ymin + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    return frame
