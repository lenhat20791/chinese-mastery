import os
import datetime
import streamlit as st
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
    Xác thực Google Drive: Ưu tiên đọc từ st.secrets (trên mây), 
    nếu không có thì dùng file token.json / credentials.json cục bộ (trên máy tính).
    """
    creds = None

    # 1. Kiểm tra xem có cấu hình trong Streamlit Secrets không (Khi chạy trên mây)
    if "google_token" in st.secrets and "google_credentials" in st.secrets:
        try:
            token_info = dict(st.secrets["google_token"])
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        except Exception as e:
            print(f"Lỗi đọc token từ secrets: {e}")

    # 2. Nếu không có trong secrets, thử đọc từ file token.json cục bộ
    elif os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 3. Kiểm tra tính hợp lệ của token, nếu hết hạn thì refresh
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            creds = None

    # 4. Nếu vẫn không có creds hợp lệ và đang chạy máy tính cá nhân -> Dùng flow đăng nhập local
    if not creds or not creds.valid:
        if os.path.exists(CREDENTIALS_FILE):
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                # Lưu token lại trên máy cá nhân
                with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
                    token.write(creds.to_json())
            except Exception as e:
                return None
        elif "google_credentials" in st.secrets:
            # Trường hợp chạy trên mây nhưng token hết hạn và cần dùng thông tin client từ secrets
            try:
                cred_info = dict(st.secrets["google_credentials"])
                # Có thể tái tạo từ refresh token trong secrets nếu có
                if "google_token" in st.secrets and "refresh_token" in st.secrets["google_token"]:
                    token_info = dict(st.secrets["google_token"])
                    creds = Credentials(
                        token=token_info.get("token"),
                        refresh_token=token_info.get("refresh_token"),
                        token_uri=token_info.get("token_uri"),
                        client_id=cred_info.get("client_id"),
                        client_secret=cred_info.get("client_secret"),
                        scopes=SCOPES
                    )
                    creds.refresh(Request())
            except Exception as e:
                return None
        else:
            return None

    if not creds:
        return None

    return build('drive', 'v3', credentials=creds)

def backup_to_drive(current_day):
    """
    Tải file database lên Drive cá nhân và chỉ giữ lại đúng 2 bản sao lưu gần nhất.
    """
    try:
        service = get_drive_service()
        if not service:
            return False, "Không thể xác thực tài khoản Google Drive!"

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
            return False, "Không thể xác thực tài khoản Google Drive!"

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
