from ultralytics import YOLO  # YOLOv8

model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_cuda\runs\detect\kickboard_v5\weights\best.pt")
model.to('cuda')

results = model(r"C:\Users\ihyun\Desktop\킥보드 단속 데이터셋\추가 킥보드 데이터셋\스크린샷 2024-10-07 200159.png", show=True, conf=0.5)
