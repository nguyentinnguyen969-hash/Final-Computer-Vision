import eventlet
eventlet.monkey_patch() # Quan trọng: Phải đứng đầu để thư viện Web không bị treo trên Windows

import cv2
import time
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import threading
from backend import FireDetectionEngine
from telegram_bot import TelegramNotifier

"""
LỚP APP SERVER: Nơi kết nối AI với Trình duyệt (Frontend).
Nhiệm vụ: Truyền hình ảnh (Streaming) -> Nhận lệnh từ nút bấm -> Điều khiển Telegram.
"""

app = Flask(__name__)
# SocketIO giúp Frontend và Backend nói chuyện 'nháy mắt' với nhau (Real-time)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Khởi tạo lõi AI và Bot thông báo
engine = FireDetectionEngine()
notifier = TelegramNotifier()

# 1. BƯỚC CHUẨN BỊ: Nạp model và mở camera ngay khi khởi động
engine.load_model()
engine.initialize_camera(0)

@app.route('/')
def index():
    """Giao diện chính (Dashboard)"""
    return render_template('index.html')

@socketio.on('update_roi')
def handle_roi(data):
    """Lắng nghe lệnh VẼ ROI từ trình duyệt (dưới dạng tỷ lệ 0-1)"""
    if data is None:
        engine.roi = None # Xóa vùng vẽ
    else:
        # Lưu tọa độ vùng vẽ [x1, y1, x2, y2] vào Engine
        engine.roi = (data['x1'], data['y1'], data['x2'], data['y2'])
    print(f"--- [SERVER] Cap nhat vung ROI moi: {engine.roi} ---")

@socketio.on('toggle_telegram')
def handle_telegram(data):
    """Lắng nghe lệnh BẬT/TẮT từ nút gạt Telegram"""
    engine.telegram_enabled = data['enabled']
    print(f"--- [SERVER] Telegram Alert set to: {engine.telegram_enabled} ---")

def generate_frames():
    """Hàm VÒNG LẶP CHÍNH: Chạy liên tục để lấy ảnh từ AI và gửi lên Web"""
    fire_logged = False
    smoke_logged = False
    
    while True:
        # Lấy ảnh và danh sách vật thể từ Backend
        frame, detections = engine.process_frame()
        
        if frame is not None:
            # Lọc danh sách Lửa và Khói
            fire_in_view = [d for d in detections if d['label'].lower() == 'fire']
            smoke_in_view = [d for d in detections if d['label'].lower() == 'smoke']

            # --- A. LOG TRÊN WEB: Luôn báo cho người dùng biết (Web Alerts) ---
            if fire_in_view and not fire_logged:
                socketio.emit('new_detection', {'msg': '🔥 CANH BAO: PHAT HIEN LUA!', 'type': 'fire'})
                fire_logged = True
            elif not fire_in_view:
                fire_logged = False
            
            if smoke_in_view and not smoke_logged:
                socketio.emit('new_detection', {'msg': '💨 THONG BAO: CO KHOI!', 'type': 'smoke'})
                smoke_logged = True
            elif not smoke_in_view:
                smoke_logged = False

            # --- B. GUI TELEGRAM (QUY TAC: PHAI CO ROI + BAT NUT MOI GUI) ---
            if engine.telegram_enabled and engine.roi is not None:
                # Nếu vừa có phát hiện mới (Lửa/Khói mới hiện ra)
                if (fire_in_view and fire_logged) or (smoke_in_view and smoke_logged):
                    import os
                    if not os.path.exists("outputs"):
                        os.makedirs("outputs")
                        
                    photo_path = os.path.join("outputs", "tele_alert.jpg")
                    cv2.imwrite(photo_path, frame) # Chụp lại khung hình có hỏa hoạn
                    
                    caption = "⚠️ <b>ALARM: XAM PHAM VUNG ROI!</b>\n"
                    caption += "Trang thai: " + (f"🔥 LUA " if fire_in_view else "") + (f"💨 KHOI " if smoke_in_view else "") + "\n"
                    caption += f"Thoi gian: {time.strftime('%H:%M:%S')}"
                    
                    # notifier.send_photo(photo_path, caption) # Gửi ảnh + Chữ về Telegram
                    
                    # SỬA LỖI ĐƠ: Chạy hàm gửi Telegram trong một luồng riêng (Thread)
                    # Điều này giúp vòng lặp video tiếp tục chạy ngay lập tức mà không phải đợi mạng.
                    threading.Thread(target=notifier.send_photo, args=(photo_path, caption), daemon=True).start()
                    
                    print(f"--- [SERVER] Dang gui canh bao toi Telegram (Background Thread)... ---")

            # Nén ảnh thành định dạng JPEG để truyền qua Internet (Streaming)
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Tạm nghỉ 0.01s để trình duyệt không bị quá tải
        eventlet.sleep(0.01)

@app.route('/video_feed')
def video_feed():
    """Đường dẫn video chính: <img src='/video_feed'>"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Chạy server tại địa chỉ http://127.0.0.1:5000
    socketio.run(app, host='0.0.0.0', port=5000)
