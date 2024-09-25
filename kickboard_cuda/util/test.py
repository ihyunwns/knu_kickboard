from ultralytics import YOLO #YOLO 8

model = YOLO(r"C:\Users\ihyun\Desktop\knup_kickboard\runs\detect\train6\weights\best.pt")

results = model.predict(source=r"C:\Users\ihyun\Desktop\knup_kickboard\kickboard_dataset\Kickboard.v5i.yolov8\test\images", save=True)





