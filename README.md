**Cấu trúc thư mục**

face\_analysis/

├── src/

│   ├── camera.py               # Kết nối và đọc frame từ webcam

│   ├── face\_detector.py        # Detect bounding box khuôn mặt (Haar Cascade)

│   ├── data\_collector.py       # Quay video + cắt frames

│   ├── preprocessor.py         # Tiền xử lý ảnh cho từng luồng

│   ├── landmark\_extractor.py   # MediaPipe FaceMesh — 468 landmarks

│   └── landmark\_storage.py     # Lưu landmarks ra CSV + NPZ

├── data/

│   ├── videos/                 # File .mp4 từ chế độ thu thập

│   ├── frames/                 # Frames .jpg đã cắt từ video

│   └── landmarks/              # CSV + NPZ landmarks đã xử lý

├── requirements.txt

├── README.md

└── main.py                     # Entry point



**Yêu cầu hệ thống**



\- Python 3.9 – 3.11 (khuyến nghị 3.11)

\- Webcam

\- RAM tối thiểu 4GB



**Cài đặt**



Bước 1 — Tạo và kích hoạt môi trường ảo



python -m venv venv



\# Windows

venv\\Scripts\\activate



\# Mac / Linux

source venv/bin/activate



Bước 2 — Cài thư viện



pip install -r requirements.txt



Lưu ý: numpy==1.26.4 được pin cố định vì MediaPipe và TensorFlow chưa hỗ trợ NumPy 2.x.



**Chạy chương trình**



python main.py



**Chọn chế độ từ menu:**



==================================================

&#x20; FACE ANALYSIS — Landmarks + Storage

==================================================



Chọn chế độ:

&#x20; 1 → Realtime  (webcam + nhấn S để ghi)

&#x20; 2 → Thu thập  (quay video + cắt frames)

&#x20; 3 → Offline   (xử lý frames → lưu CSV + NPZ)

&#x20; 4 → Inspect   (xem nội dung file NPZ)



\*\*Hướng dẫn từng chế độ\*\*



&#x20; Chế độ 1 — Realtime

&#x20; 

&#x20; Mở webcam, hiển thị 468 landmarks trực tiếp lên mặt. Dùng để kiểm tra và demo.

&#x20; Webcam → MediaPipe FaceMesh → 468 chấm vàng hiển thị realtime



&#x20; Phím và chức năng



&#x20; S - Bắt đầu / dừng ghi landmarks

&#x20; P - In tọa độ summary ra console

&#x20; G - In tọa độ theo nhóm (mắt, mày, miệng)

&#x20; Q - Thoát



&#x20; Đầu ra khi nhấn S:



&#x20; data/landmarks/session\_YYYYMMDD\_HHMMSS/

&#x20;   landmarks.csv

&#x20;   landmarks.npz

&#x20;   meta.txt



&#x20; Chế độ 2 — Thu thập dữ liệu

&#x20; 

&#x20; Quay video từ webcam trong N giây, sau đó tự động cắt thành frames.



&#x20; Dùng khi muốn lưu raw data để xử lý sau, hoặc máy yếu không chạy MediaPipe realtime được.



&#x20; Webcam → video .mp4 → frames .jpg



&#x20; Nhập thông số:



&#x20; Thời gian quay (giây, mặc định 20): 20

&#x20; Frame step (mặc định 3): 3



&#x20; frame\_step=3 nghĩa là lấy 1 frame mỗi 3 frame — giảm dữ liệu trùng lặp ở 30fps.



&#x20; Đầu ra:



&#x20; data/videos/session\_YYYYMMDD\_HHMMSS.mp4



&#x20; data/frames/session\_YYYYMMDD\_HHMMSS/



&#x20;     frame\_00000.jpg

&#x20;   

&#x20;     frame\_00001.jpg



&#x20;     ...



&#x20; Chế độ 3 — Offline



&#x20; Chạy MediaPipe trên toàn bộ frames đã cắt, lưu kết quả ra CSV và NPZ.



&#x20; Thường dùng sau chế độ 2.



&#x20; frames .jpg → MediaPipe → landmarks.csv + landmarks.npz



&#x20; Nhập đường dẫn:



&#x20; Đường dẫn thư mục frames: data/frames/session\_20241201\_143022



&#x20; Đầu ra:



&#x20; data/landmarks/session\_20241201\_143022/



&#x20;     landmarks.csv       # mỗi hàng = 1 frame, 1404 cột tọa độ

&#x20;     landmarks.npz       # array shape (N, 468, 3)

&#x20;     meta.txt            # thông tin tổng quan

&#x20;    

&#x20; Chế độ 4 — Inspect



&#x20; Kiểm tra nội dung file NPZ đã lưu — xem số frames, tọa độ mẫu.

&#x20; Đường dẫn file .npz: data/landmarks/session\_xxx/landmarks.npz



