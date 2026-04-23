# 🚁 YOLO Object Detection for Clover Drone

В этом руководстве описан процесс обучения нейросети YOLOv8 для распознавания объектов с камеры квадрокоптера **Clover** и интеграции модели в полётную миссию. Материал ориентирован на образовательные цели и не содержит готового решения соревновательных задач, однако даёт все необходимые компоненты для самостоятельной сборки рабочей системы.

## 📚 Содержание

- [Необходимое оборудование и ПО](#-необходимое-оборудование-и-по)
- [Сбор данных](#-сбор-данных)
- [Разметка датасета](#-разметка-датасета)
- [Обучение YOLOv8](#-обучение-yolov8)
- [Тестирование модели](#-тестирование-модели)
- [Интеграция с Clover](#-интеграция-с-clover)
- [Полезные ссылки](#-полезные-ссылки)

---

## ⚙️ Необходимое оборудование и ПО

- **Дрон COEX Clover** (физический или симулятор Gazebo)
- **ROS** + пакет `clover` (см. [официальную документацию](https://clover.coex.tech/))
- **Python 3.8+** с установленными библиотеками:
  - `ultralytics` (YOLOv8)
  - `opencv-python`
  - `cv_bridge`, `tf2_geometry_msgs` (доступны в ROS-окружении)
- **Инструмент разметки**: [LabelImg](https://github.com/HumanSignal/labelImg) или [Roboflow](https://roboflow.com/)

---

## 📹 Сбор данных

Для обучения модели необходимо записать видео с бортовой камеры дрона, на котором присутствуют целевые объекты.  
Пример кода для захвата видео во время полёта можно найти в статье на Habr:  
[«Распознавание объектов с помощью YOLO на дроне Clover»](https://habr.com/ru/articles/821971/) (раздел «Запись видео»).  

Базовый фрагмент для инициализации видеозаписи:

```python
import cv2

def start_video_writer(output_path='flight_video.avi', fps=15.0, frame_size=(320, 240)):
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    return cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    ⚠️ Важно: Для симулятора разрешение камеры обычно 320×240. В реальном дроне может быть 640×480.

После получения видеофайла извлеките кадры с интервалом (например, каждый 30‑й), чтобы избежать дублирования сцен. Скрипт извлечения:
python

import cv2
import os

cap = cv2.VideoCapture('flight_video.avi')
os.makedirs('dataset_frames', exist_ok=True)
frame_num, saved = 0, 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    if frame_num % 30 == 0:
        cv2.imwrite(f'dataset_frames/frame_{saved:05d}.jpg', frame)
        saved += 1
    frame_num += 1

cap.release()
print(f'Сохранено {saved} кадров')

🏷️ Разметка датасета

    Создайте структуру папок:
    text

    dataset/
    ├── data.yaml
    ├── train/
    │   ├── images/
    │   └── labels/
    └── val/
        ├── images/
        └── labels/

    Разместите изображения: примерно 80% в train/images, 20% в val/images.

    Запустите LabelImg:
    bash

    labelImg

        Откройте папку train/images.

        Укажите директорию сохранения train/labels.

        Выберите формат YOLO (переключатель в левой панели).

        Обведите объекты и задайте имена классов (например, grebnik, brakonier, tyrist).

        Повторите для папки val.

    Файл data.yaml:
    yaml

    train: /absolute/path/to/dataset/train/images
    val: /absolute/path/to/dataset/val/images

    nc: 3
    names: ['grebnik', 'brakonier', 'tyrist']

        📌 Используйте абсолютные пути! Например: /home/clover/dataset/train/images.

🧠 Обучение YOLOv8

Убедитесь, что библиотека Ultralytics установлена:
bash

pip install ultralytics

Запустите обучение (пример для YOLOv8n):
bash

yolo detect train model=yolov8n.pt \
               data=/path/to/dataset/data.yaml \
               epochs=100 \
               imgsz=320 \
               batch=8 \
               name=clover_detector

Подробнее о параметрах обучения: Ultralytics Docs.

После завершения лучшая модель сохранится в runs/detect/clover_detector/weights/best.pt.
🔍 Тестирование модели

Проверка на отдельном изображении:
bash

yolo predict model=/path/to/best.pt source=test_image.jpg imgsz=320

Если всё работает корректно, скопируйте модель на дрон (или в виртуальную среду Clover):
bash

cp runs/detect/clover_detector/weights/best.pt /home/clover/

✈️ Интеграция с Clover

Теперь необходимо встроить вызов модели в ROS‑ноду, обрабатывающую изображение с камеры. Ниже представлены ключевые фрагменты, которые потребуется соединить в единый скрипт.
1. Инициализация подписчика и модели
python

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

rospy.init_node('yolo_detector')
bridge = CvBridge()
model = YOLO('/home/clover/best.pt')
CONFIDENCE = 0.5

2. Callback обработки кадра
python

from clover import long_callback

@long_callback
def image_callback(msg):
    img = bridge.imgmsg_to_cv2(msg, 'bgr8')
    results = model(img, verbose=False)
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                conf = float(box.conf[0])
                if conf < CONFIDENCE:
                    continue
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                # Здесь можно добавить отрисовку и публикацию координат

3. Преобразование координат пикселя в карту

Функция pixel_to_map использует модель камеры и tf‑трансформации. Пример реализации можно найти в Clover‑примерах.

Краткий каркас:
python

import image_geometry
import tf2_ros

camera_model = image_geometry.PinholeCameraModel()
camera_model.fromCameraInfo(rospy.wait_for_message('main_camera/camera_info', CameraInfo))
tf_buffer = tf2_ros.Buffer()
tf_listener = tf2_ros.TransformListener(tf_buffer)

def pixel_to_map(u, v):
    ray = camera_model.projectPixelTo3dRay((u, v))
    # ... вычисление пересечения луча с плоскостью земли ...
    return (map_x, map_y)

4. Полётная логика

Для перемещения дрона используйте сервисы navigate и вспомогательную функцию navigate_wait (описана в документации Clover).
python

from clover import srv
navigate = rospy.ServiceProxy('navigate', srv.Navigate)

def navigate_wait(x, y, z, frame_id='aruco_map'):
    # реализация ожидания достижения точки
    pass

5. Публикация результатов

Обнаруженные объекты можно отправлять в топик ~detected_object типа geometry_msgs/PointStamped.
python

from geometry_msgs.msg import PointStamped
point_pub = rospy.Publisher('~detected_object', PointStamped, queue_size=10)

# Внутри callback:
point_msg = PointStamped()
point_msg.header.frame_id = 'aruco_map'
point_msg.point.x, point_msg.point.y = map_xy
point_pub.publish(point_msg)

6. Запись видео во время миссии

Совместить запись видео с детекцией можно, добавив в callback вызов video_writer.write(img). Инициализация VideoWriter показана в начале руководства.
🔗 Полезные ссылки

    Clover – документация

    Ultralytics YOLOv8

    Статья на Habr: Распознавание объектов с помощью YOLO на дроне Clover

    LabelImg – разметка изображений

    Примеры кода для Clover# 🚁 YOLO Object Detection for Clover Drone

В этом руководстве описан процесс обучения нейросети YOLOv8 для распознавания объектов с камеры квадрокоптера **Clover** и интеграции модели в полётную миссию. Материал ориентирован на образовательные цели и не содержит готового решения соревновательных задач, однако даёт все необходимые компоненты для самостоятельной сборки рабочей системы.

## 📚 Содержание

- [Необходимое оборудование и ПО](#необходимое-оборудование-и-по)
- [Сбор данных](#сбор-данных)
- [Разметка датасета](#разметка-датасета)
- [Обучение YOLOv8](#обучение-yolov8)
- [Тестирование модели](#тестирование-модели)
- [Интеграция с Clover](#интеграция-с-clover)
- [Полезные ссылки](#полезные-ссылки)

---

## ⚙️ Необходимое оборудование и ПО

- **Дрон COEX Clover** (физический или симулятор Gazebo)
- **ROS** + пакет `clover` (см. [официальную документацию](https://clover.coex.tech/))
- **Python 3.8+** с установленными библиотеками:
  - `ultralytics` (YOLOv8)
  - `opencv-python`
  - `cv_bridge`, `tf2_geometry_msgs` (доступны в ROS-окружении)
- **Инструмент разметки**: [LabelImg](https://github.com/HumanSignal/labelImg) или [Roboflow](https://roboflow.com/)

---

## 📹 Сбор данных

Для обучения модели необходимо записать видео с бортовой камеры дрона, на котором присутствуют целевые объекты.  
Пример кода для захвата видео во время полёта можно найти в статье на Habr:  
[«Распознавание объектов с помощью YOLO на дроне Clover»](https://habr.com/ru/articles/821971/) (раздел «Запись видео»).  

Базовый фрагмент для инициализации видеозаписи:

```python
import cv2

def start_video_writer(output_path='flight_video.avi', fps=15.0, frame_size=(320, 240)):
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    return cv2.VideoWriter(output_path, fourcc, fps, frame_size)
