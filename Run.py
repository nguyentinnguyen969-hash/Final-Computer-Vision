import threading
import time
import webbrowser
from app import app, socketio

"""
FILE KHOI CHAY (ENTRY POINT): Nút nguồn duy nhất của hệ thống.
Nhiệm vụ: Chạy Server App và tự động mở trình duyệt.
"""

def open_browser():
    """Tự động mở trình duyệt sau 2 giây để Server kịp khởi động"""
    time.sleep(2)
    print("--- [HE THONG] Dang mo Dashboard tren trinh duyet... ---")
    webbrowser.open("http://127.0.0.1:5000")

def run_app():
    print("--- [HE THONG] DANG KHOI TAO PREMIUM DASHBOARD (FLASK + AI) ---")
    
    # Chạy hàm mở trình duyệt bằng một luồng phụ (Thread) để không làm treo server
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Chạy Flask App kết hợp với SocketIO truyền dữ liệu thời gian thực
    # 0.0.0.0: Cho phép các máy khác trong cùng mạng LAN truy cập (nếu biết IP)
    # port 5000: Cổng mặc định của Flask
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    run_app()
