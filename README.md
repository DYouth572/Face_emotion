# Ứng dụng AI trong trích chọn đặc trưng khuôn mặt và biểu cảm người học

CHÚ Ý: dùng Python phiên bản 3.10.0 (là ổn định nhất, phiên bản 3.11.x cũng được, nhưng phiên bản cao hơn thì ko đc)

## Giới thiệu
Đây là đồ án xây dựng một ứng dụng AI hỗ trợ **ghi nhận và hiển thị cảm xúc, các đặc trưng khuôn mặt của người học theo thời gian thực** thông qua webcam.  
Hệ thống tập trung vào việc:
- Phát hiện khuôn mặt trong khung hình
- Cắt vùng khuôn mặt để phân tích
- Trích xuất **468 điểm landmark khuôn mặt**
- Sử dụng **DeepFace** để **gán nhãn cảm xúc**
- Tính toán các **đặc trưng khuôn mặt thủ công** từ landmark
- Hiển thị kết quả trực tiếp trên giao diện realtime

Ứng dụng hướng tới việc hỗ trợ theo dõi biểu cảm và trạng thái khuôn mặt của người học trong quá trình học tập.

---

## Mục tiêu của đề tài
Mục tiêu chính của dự án là xây dựng một hệ thống có khả năng:
1. Nhận diện khuôn mặt từ webcam
2. Trích xuất đặc trưng hình học khuôn mặt
3. Xác định cảm xúc khuôn mặt
4. Hiển thị các chỉ số đặc trưng theo thời gian thực
5. Làm nền tảng cho việc đánh giá trạng thái khuôn mặt và mức độ tập trung/căng thẳng của người học

---

## Chức năng chính
- Phát hiện khuôn mặt từ camera
- Chọn và xử lý khuôn mặt trong khung hình
- Cắt vùng khuôn mặt để phục vụ phân tích
- Trích xuất 468 điểm landmark khuôn mặt
- Gán nhãn cảm xúc bằng DeepFace
- Tính toán các đặc trưng khuôn mặt thủ công từ landmark
- Hiển thị kết quả realtime trên giao diện

---

## Quy trình xử lý của hệ thống

### 1. Thu nhận dữ liệu từ camera
Hệ thống sử dụng webcam để lấy video theo thời gian thực.

### 2. Phát hiện khuôn mặt
Khung hình đầu vào được xử lý để phát hiện vị trí khuôn mặt.

### 3. Cắt vùng khuôn mặt
Sau khi xác định được khuôn mặt, hệ thống cắt riêng vùng khuôn mặt để phục vụ cho các bước xử lý tiếp theo.

### 4. Trích xuất landmark khuôn mặt
Từ khuôn mặt đã được cắt, hệ thống xác định **468 điểm landmark** để mô tả cấu trúc hình học khuôn mặt.

### 5. Gán nhãn cảm xúc bằng DeepFace
Vùng khuôn mặt được đưa vào **DeepFace** để phân tích cảm xúc.  
Kết quả đầu ra bao gồm:
- Nhãn cảm xúc chính (ví dụ: happy, neutral, sad, angry, ...)
- Độ tin cậy tương ứng của cảm xúc dự đoán

### 6. Tính toán đặc trưng khuôn mặt thủ công
Dựa trên 468 điểm landmark, hệ thống áp dụng các công thức hình học để suy ra các đặc trưng khuôn mặt như:
- Nháy mắt / độ mở mắt
- Mức độ nhíu mày
- Độ mở miệng
- Một số thay đổi hình học liên quan đến biểu cảm

### 7. Hiển thị giao diện realtime
Các thông tin sau được hiển thị trực tiếp:
- Khung khuôn mặt
- Landmark khuôn mặt
- Nhãn cảm xúc
- Các đặc trưng khuôn mặt được trích xuất

---

## Công nghệ sử dụng
- **Python**
- **OpenCV** – xử lý ảnh và video realtime
- **MediaPipe** – trích xuất landmark khuôn mặt
- **DeepFace** – nhận diện cảm xúc khuôn mặt
- **NumPy** – xử lý dữ liệu số

---

## Vai trò của DeepFace trong dự án
Trong hệ thống này, **DeepFace được sử dụng để gán nhãn cảm xúc cho khuôn mặt**.  
Đây là một mô-đun hỗ trợ giúp hệ thống xác định nhanh 7 trạng thái cảm xúc tổng quát của người học

Kết quả cảm xúc từ DeepFace được kết hợp cùng các đặc trưng hình học từ landmark để phục vụ phân tích tổng thể khuôn mặt.

---

**Cấu trúc thư mục** (phần này t giữ lại, vì chưa xong hết các file nên t chưa sửa)

face\_analysis/

├── src/

│   ├── camera.py               # Kết nối và đọc frame từ webcam

│   ├── face\_detector.py        # Detect bounding box khuôn mặt (Haar Cascade)

│   ├── data\_collector.py       # Quay video + cắt frames

│   ├── preprocessor.py         # Tiền xử lý ảnh cho từng luồng

│   ├── landmark\_extractor.py   # MediaPipe FaceMesh — 468 landmarks

│   └── landmark\_storage.py     # Lưu landmarks ra CSV + NPZ

│   └── test.py     # Tính toán theo công thức cho các đặc trưng khuôn mặt 

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
