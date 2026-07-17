import cv2
from src.capture import VideoCapture

# Инициализация камеры (как в твоем конфиге)
cap = VideoCapture(device=0)

print("Начинаю показ в одном потоке. Нажми 'q' в окне, чтобы закрыть.")

while True:
    frame = cap.read()
    if frame is not None:
        cv2.imshow("TEST", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    else:
        print("Кадр пустой...")

cap.stop()
cv2.destroyAllWindows()