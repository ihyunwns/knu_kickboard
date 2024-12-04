from ultralytics import YOLO  # YOLOv8

model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_cuda\runs\detect\kickboard_v62\weights\best.pt")
model.to('cuda')

results = model(r"C:\Users\ihyun\Downloads\HOW TO TEACH A TODDLER TO SCOOT.mp4", show=True, conf=0.5)
