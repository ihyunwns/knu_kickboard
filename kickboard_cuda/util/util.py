from cgi import print_form


def compute_iou(box_a, box_b):
    """
    IOU 겹침 정도를 계산
    """

    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[2], box_b[2])
    y_b = min(box_a[3], box_b[3])

    inter_area = max(0, x_b - x_a) * max(0, y_b - y_a)

    box_a_area = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    box_b_area = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])

    iou = inter_area / float(box_a_area + box_b_area - inter_area)

    return iou


def convert_tlwh_to_xyxy(box):
    """
    bbox 형식이 다를 때 계산이 안되는 것을 방지 하기 위한 컨버터
    Top-Left Width-Height 형식의 바운딩 박스를 Top-Left Bottom-Right 형식으로 변환
    """
    x, y, w, h = box
    return [x, y, x + w, y + h]


def is_helmet_position_valid(person_bbox, helmet_bbox, y_threshold):
    """
    헬멧이 사람의 바운딩 박스 안에 위치하고,
    헬멧의 상단 y 좌표값이 사람의 상단 y 좌표값과 ±y_threshold 픽셀 이내 인지 확인
    """
    person_x1, person_y1, person_x2, person_y2 = person_bbox
    helmet_x1, helmet_y1, helmet_x2, helmet_y2 = helmet_bbox

    print(f"person_bbox: {person_bbox}, helmet_bbox: {helmet_bbox}")

    # 헬멧의 x 중심 좌표
    helmet_x = (helmet_x1 + helmet_x2) / 2

    x_within = person_x1 <= helmet_x <= person_x2

    # 헬멧의 상단 y 좌표값이 사람의 상단 y 좌표값과 ±y_threshold 픽셀 이내인지 확인
    y_diff = abs(helmet_y1 - person_y1)
    y_close = y_diff <= y_threshold

    return x_within and y_close