import cv2
from deepface import DeepFace

# Haar Cascade là bộ phát hiện khuôn mặt có sẵn trong OpenCV
# detect mặt 
faceCascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# mở cam
# Thử mở camera ngoài trước (1), nếu không có thì quay về camera mặc định (0)
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise IOError("Không mở được camera")

# KHAI BÁO BIẾN DÙNG CHUNG
font = cv2.FONT_HERSHEY_SIMPLEX

# Biến lưu nhãn cảm xúc hiện tại để hiển thị lên màn hình
emotion_text = "Detecting..."

# Biến đếm số frame
frame_count = 0

# VÒNG LẶP ĐỌC VIDEO
while True:
    ret, frame = cap.read()

    # Nếu không đọc được frame thì dừng
    if not ret:
        print("Không đọc được frame")
        break

    # Tăng số frame lên 1
    frame_count += 1

    # chuyển ảnh sang xám để detect mặt nhanh hơn 
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # DÙNG HAAR CASCADE ĐỂ TÌM KHUÔN MẶT
    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4
    )

    # CHỈ XỬ LÝ KHI PHÁT HIỆN ĐƯỢC ÍT NHẤT 1 MẶT
    if len(faces) > 0:
        
        # chọn mặt có diện tích lớn nhất: w*h lớn nhất
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        (x, y, w, h) = faces[0]

        # VẼ KHUNG XANH QUANH KHUÔN MẶT
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # CHỈ CHẠY DEEPFACE MỖI 30 FRAME ĐỂ ĐỠ LAG
        # Nghĩa là không phải frame nào cũng chạy model
        # Ví dụ webcam 30 FPS thì khoảng 1 giây mới phân tích 1 lần
        if frame_count % 30 == 0:
            try:
                # 8.1 CẮT RIÊNG VÙNG KHUÔN MẶT (ROI)
                # tọa độ (x, y, w, h) dùng tọa độ đó để cắt đúng phần mặt ra khỏi ảnh gốc, region of interest 
                face_roi = frame[y:y + h, x:x + w]

                # ĐƯA PHẦN MẶT ĐÃ CẮT VÀO DEEPFACE
                result = DeepFace.analyze(
                    face_roi,
                    actions=['emotion'],
                    enforce_detection=False
                )

                # angry, happy, sad, neutral,...
                emotion_scores = result[0]['emotion']

                # LẤY CẢM XÚC MẠNH NHẤT
                dominant_emotion = result[0]['dominant_emotion']

                # LẤY ĐỘ TIN CẬY CỦA CẢM XÚC ĐÓ
                confidence = emotion_scores[dominant_emotion]

                # Ví dụ: happy (87.3%)
                emotion_text = f"{dominant_emotion} ({confidence:.1f}%)"

            except Exception as e:
                emotion_text = "No face"

        # HIỂN THỊ NHÃN CẢM XÚC NGAY PHÍA TRÊN KHUÔN MẶT
        cv2.putText(
            frame,
            emotion_text,
            (x, y - 10),   # vị trí chữ nằm phía trên khuôn mặt
            font,
            0.9,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

    else:
        # Nếu không có mặt trong khung hình thì không chạy DeepFace
        # và đổi nhãn hiển thị thành "No face"
        emotion_text = "No face"

    # HIỂN THỊ VIDEO
    cv2.imshow("Demo video", frame)

    # Nhấn q để thoát
    if cv2.waitKey(2) & 0xFF == ord('q'):
        break
        
cap.release()
cv2.destroyAllWindows()
