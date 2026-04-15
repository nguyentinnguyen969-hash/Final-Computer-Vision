import cv2
import numpy as np
from ultralytics import YOLO
import kagglehub
import os

class FireDetectionEngine:
    """
    LỚP BACKEND: Nơi xử lý 'não bộ' của ứng dụng.
    Nhiệm vụ: Đọc camera -> Chạy AI (YOLO) -> Vẽ thông tin lên hình -> Lọc vùng ROI.
    """
    def __init__(self, model_source="bertnardomariouskono/fire-and-smoke-detection-yolov8/pyTorch/default"):
        self.model_source = model_source
        self.model = None
        self.cap = None
        
        # Cấu hình ngưỡng AI riêng biệt:
        self.conf_fire = 0.35       # Ngưỡng cho Lửa (mặc định 35%)
        self.conf_smoke = 0.25    # Ngưỡng cho Khói (mặc định 25%)
        self.brightness_alpha = 0.6 # Giảm độ sáng khung hình xuống 60%
        
        # Tối ưu hóa hiệu năng (Smoothness)
        self.skip_frames = 6        # Chỉ chạy AI mỗi N khung hình (2 = 1 chạy, 1 nghỉ)
        self.last_detections = []   # Lưu lại kết quả cũ để dùng cho khung hình bị bỏ qua
        
        # Quản lý trạng thái
        self.frame_count = 0        # Tổng số ảnh đã xử lý
        self.roi = None             # Vùng quan tâm (Region of Interest)
        self.telegram_enabled = True # Trạng thái gửi tin nhắn

    def load_model(self):
        """Tải mô hình AI từ Kaggle hoặc thư mục cục bộ"""
        path = kagglehub.model_download(self.model_source)
        self.model = YOLO(os.path.join(path, 'infernoguard_best.pt'))
        return True

    def initialize_camera(self, source=0):
        """Mở Camera (mặc định là 0 - webcam máy tính)"""
        self.cap = cv2.VideoCapture(source)
        return self.cap.isOpened()

    def process_frame(self):
        """HÀM CHÍNH: Xử lý từng khung hình một (Có tối ưu nhảy khung hình)"""
        if self.cap is None or not self.cap.isOpened():
            return None, []

        ret, frame = self.cap.read()
        if not ret: return None, []
        
        self.frame_count += 1
        h, w = frame.shape[:2]
        
        # 1. Tiền xử lý: Làm tối ảnh
        processed_frame = cv2.convertScaleAbs(frame, alpha=self.brightness_alpha, beta=0)   

        # LOGIC NHẢY KHUNG HÌNH: Chỉ chạy AI khi (frame_count % skip_frames == 0)
        # Điều này giúp camera mượt hơn vì giảm tải cho CPU/GPU
        should_run_ai = (self.frame_count % self.skip_frames == 0)
        
        if should_run_ai:
            # 2. Chạy AI: Dùng ngưỡng thấp nhất để lọc sơ bộ
            min_conf = min(self.conf_fire, self.conf_smoke)
            results = self.model.predict(source=processed_frame, conf=min_conf, verbose=False)
            
            current_detections = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = self.model.names[int(box.cls[0])].lower()
                    conf = float(box.conf[0])
                    
                    # 2b. LỌC THEO NGƯỠNG RIÊNG BIỆT CHO TỪNG LOẠI
                    target_conf = self.conf_fire if label == 'fire' else self.conf_smoke
                    if conf < target_conf:
                        continue # Bỏ qua nếu không đạt ngưỡng riêng

                    # 3. LOGIC LỌC VÙNG ROI
                    is_in_roi = True
                    if self.roi:
                        p_rx1, p_ry1, p_rx2, p_ry2 = self.roi
                        rx1, ry1 = int(p_rx1 * w), int(p_ry1 * h)
                        rx2, ry2 = int(p_rx2 * w), int(p_ry2 * h)
                        is_in_roi = not (x1 > rx2 or x2 < rx1 or y1 > ry2 or y2 < ry1)

                    if is_in_roi:
                        current_detections.append({'label': label, 'bbox': (x1, y1, x2, y2), 'conf': conf})
            
            self.last_detections = current_detections # Lưu lại kết quả cho frame kế tiếp

        # Dùng kết quả (mới hoặc cũ) để vẽ lên màn hình
        for det in self.last_detections:
            x1, y1, x2, y2 = det['bbox']
            label = det['label']
            conf = det['conf']
            
            color = (0, 0, 255) if label == 'fire' else (128, 128, 128)
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
            text = f"{label.upper()} {conf:.2f}"
            cv2.putText(processed_frame, text, (x1, y1 - 15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3)

        # 4. Vẽ Vùng ROI (Hình chữ nhật màu Vàng)
        if self.roi:
            p_rx1, p_ry1, p_rx2, p_ry2 = self.roi
            rx1, ry1, rx2, ry2 = int(p_rx1 * w), int(p_ry1 * h), int(p_rx2 * w), int(p_ry2 * h)
            cv2.rectangle(processed_frame, (rx1, ry1), (rx2, ry2), (0, 255, 255), 2)
            cv2.putText(processed_frame, "DANG QUET VUNG NAY", (rx1 + 5, ry1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # 5. Thông tin tổng hợp
        green_color = (166, 227, 161)
        cv2.putText(processed_frame, f"Count: {len(self.last_detections)}", (20, 50), 1, 2.5, green_color, 3)
        cv2.putText(processed_frame, f"Frames: {self.frame_count}", (20, 90), 1, 1.2, (255, 255, 255), 1)
        if not should_run_ai:
            cv2.putText(processed_frame, "SMOOTHING ACTIVE", (20, 120), 1, 0.8, (255, 255, 0), 1)
        
        return processed_frame, self.last_detections

    def release(self):
        """Giải phóng camera khi tắt app"""
        if self.cap: self.cap.release()
