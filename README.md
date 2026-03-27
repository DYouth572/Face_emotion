face_analysis/
├── src/
│   ├── camera.py               # Kết nối và đọc frame từ webcam
│   ├── face_detector.py        # Detect bounding box khuôn mặt (Haar Cascade)
│   ├── data_collector.py       # Quay video + cắt frames
│   ├── preprocessor.py         # Tiền xử lý ảnh cho từng luồng
│   ├── landmark_extractor.py   # MediaPipe FaceMesh — 468 landmarks
│   └── landmark_storage.py     # Lưu landmarks ra CSV + NPZ
├── data/
│   ├── videos/                 # File .mp4 từ chế độ thu thập
│   ├── frames/                 # Frames .jpg đã cắt từ video
│   └── landmarks/              # CSV + NPZ landmarks đã xử lý
├── requirements.txt
├── README.md
└── main.py                     

**Yêu cầu hệ thống**

- Python 3.9 – 3.11 (khuyến nghị 3.11)
  
- Webcam
 
- RAM tối thiểu 4GB

**Cài đặt**

Bước 1 — Tạo và kích hoạt môi trường ảo

python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

Bước 2 — Cài thư viện

pip install -r requirements.txt

Lưu ý: numpy==1.26.4 được pin cố định vì MediaPipe và TensorFlow chưa hỗ trợ NumPy 2.x.

**Chạy chương trình**

python main.py

Chọn chế độ từ menu:

==================================================
  FACE ANALYSIS — Landmarks + Storage
==================================================

Chọn chế độ:
  1 → Realtime  (webcam + nhấn S để ghi)
  2 → Thu thập  (quay video + cắt frames)
  3 → Offline   (xử lý frames → lưu CSV + NPZ)
  4 → Inspect   (xem nội dung file NPZ)

**Hướng dẫn từng chế độ**

  Chế độ 1 — Realtime
  
  Mở webcam, hiển thị 468 landmarks trực tiếp lên mặt. Dùng để kiểm tra và demo.
  
  Webcam → MediaPipe FaceMesh → 468 chấm vàng hiển thị realtime

  Phím và chức năng

  S - Bắt đầu / dừng ghi landmarks

  P - In tọa độ summary ra console

  G - In tọa độ theo nhóm (mắt, mày, miệng)

  Q - Thoát

  Đầu ra khi nhấn S:

  data/landmarks/session_YYYYMMDD_HHMMSS/
  
    landmarks.csv
    
    landmarks.npz
    
    meta.txt

Chế độ 2 — Thu thập dữ liệu

Quay video từ webcam trong N giây, sau đó tự động cắt thành frames.

Dùng khi muốn lưu raw data để xử lý sau, hoặc máy yếu không chạy MediaPipe realtime được.

Webcam → video .mp4 → frames .jpg

Nhập thông số:

Thời gian quay (giây, mặc định 20): 20
Frame step (mặc định 3): 3

frame_step=3 nghĩa là lấy 1 frame mỗi 3 frame — giảm dữ liệu trùng lặp ở 30fps.

Đầu ra:

data/videos/session_YYYYMMDD_HHMMSS.mp4

data/frames/session_YYYYMMDD_HHMMSS/

    frame_00000.jpg
    
    frame_00001.jpg

    ...

Chế độ 3 — Offline

Chạy MediaPipe trên toàn bộ frames đã cắt, lưu kết quả ra CSV và NPZ.

Thường dùng sau chế độ 2.

frames .jpg → MediaPipe → landmarks.csv + landmarks.npz

Nhập đường dẫn:

Đường dẫn thư mục frames: data/frames/session_20241201_143022

Đầu ra:

data/landmarks/session_20241201_143022/

    landmarks.csv       # mỗi hàng = 1 frame, 1404 cột tọa độ
    
    landmarks.npz       # array shape (N, 468, 3)
    
    meta.txt            # thông tin tổng quan
    

Chế độ 4 — Inspect

Kiểm tra nội dung file NPZ đã lưu — xem số frames, tọa độ mẫu.

Đường dẫn file .npz: data/landmarks/session_xxx/landmarks.npz
