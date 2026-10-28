import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Quyền hạn tối thiểu: Chỉ truy cập các file do chính ứng dụng tạo ra
SCOPES = ['https://www.googleapis.com/auth/drive.file']

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
DRIVE_FOLDER_ID = "1-jpbHMEUaOQASvQFX89KfxzeZO-6Vq_B"
DB_FILE = "chinese_mastery.db"

def get_drive_service():
    """
    Xác thực bằng tài khoản Google cá nhân thông qua OAuth 2.0.
    Lần đầu tiên chạy sẽ tự động bật trình duyệt để bạn bấm Cho phép.
    Từ các lần sau sẽ tự động dùng token.json đã lưu trên máy.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Lưu token lại cho những lần chạy sau
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def backup_to_drive(current_day):
    """
    Tải file database lên Drive cá nhân và chỉ giữ lại đúng 2 bản sao lưu gần nhất.
    """
    try:
        service = get_drive_service()
        if not service:
            return False, "Không tìm thấy file credentials.json trong thư mục dự án!"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"backup_chinese_day_{current_day}_{timestamp}.db"

        # 1. Upload bản backup mới
        media = MediaFileUpload(DB_FILE, mimetype='application/x-sqlite3', resumable=False)
        file_metadata = {
            'name': file_name,
            'parents': [DRIVE_FOLDER_ID]
        }
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        # 2. Quét và chỉ giữ lại đúng 2 bản mới nhất
        query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false and name contains 'backup_chinese_'"
        results = service.files().list(
            q=query, 
            spaces='drive', 
            fields='files(id, name, createdTime)', 
            orderBy='createdTime desc'
        ).execute()
        files = results.get('files', [])

        if len(files) > 2:
            for old_file in files[2:]:
                service.files().delete(fileId=old_file['id']).execute()

        return True, f"Đã lưu thành công bản Ngày {current_day} lên Drive! (Đang duy trì 2 bản gần nhất)"

    except Exception as e:
        return False, f"Lỗi đồng bộ: {str(e)}"

def restore_latest_from_drive():
    """
    Tải bản sao lưu mới nhất từ Drive về và ghi đè an toàn vào DB hiện tại.
    """
    try:
        service = get_drive_service()
        if not service:
            return False, "Không tìm thấy file credentials.json!"

        query = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false and name contains 'backup_chinese_'"
        results = service.files().list(
            q=query, 
            spaces='drive', 
            fields='files(id, name, createdTime)', 
            orderBy='createdTime desc'
        ).execute()
        files = results.get('files', [])

        if not files:
            return False, "Không tìm thấy bản sao lưu nào trên Google Drive!"

        latest_file = files[0]
        file_id = latest_file['id']
        file_name = latest_file['name']

        temp_download_path = "temp_restore.db"
        request = service.files().get_media(fileId=file_id)
        
        with open(temp_download_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        if os.path.exists(temp_download_path) and os.path.getsize(temp_download_path) > 0:
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            os.rename(temp_download_path, DB_FILE)
            return True, f"Đã khôi phục thành công từ bản: {file_name}"
        else:
            return False, "Lỗi: File tải về không hợp lệ!"

    except Exception as e:
        return False, f"Lỗi khôi phục: {str(e)}"