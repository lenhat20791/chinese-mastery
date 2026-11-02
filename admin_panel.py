"""Tab quản trị (chỉ admin): quản lý tài khoản, sao lưu và khôi phục tiến độ."""
import datetime

import streamlit as st

from auth import admin_has_default_password, create_user, delete_user, list_users, reset_password
from backup_manager import backup_to_drive, list_progress_backups, restore_from_drive
from userdb import get_meta, using_turso

BACKUP_REMINDER_DAYS = 7


def _days_since(iso_text):
    try:
        then = datetime.datetime.fromisoformat(iso_text)
    except (TypeError, ValueError):
        return None
    return (datetime.datetime.now(datetime.timezone.utc) - then).days


def _render_accounts():
    st.markdown("### 👥 Tài khoản")
    if admin_has_default_password():
        st.warning("Tài khoản **admin** đang dùng mật khẩu mặc định `123456`. Hãy đổi ở phần bên dưới.")

    with st.form("create_user_form", clear_on_submit=True):
        st.markdown("**Tạo tài khoản mới**")
        col_a, col_b, col_c = st.columns(3)
        username = col_a.text_input("Tên đăng nhập (không dấu)")
        display_name = col_b.text_input("Tên hiển thị")
        password = col_c.text_input("Mật khẩu", type="password")
        if st.form_submit_button("➕ Tạo tài khoản", type="primary"):
            ok, msg = create_user(username, display_name, password)
            (st.success if ok else st.error)(msg)

    users = list_users()
    st.dataframe(
        [{
            "Tên đăng nhập": u["username"],
            "Tên hiển thị": u["display_name"],
            "Vai trò": "Admin" if u["is_admin"] else "Học viên",
            "Ngày học": u["current_day"],
            "Cảnh giới": u["current_realm"],
            "Ngày tạo": u["created_at"],
        } for u in users],
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("**Đổi mật khẩu / xóa tài khoản**")
    labels = {u["id"]: f"{u['username']} ({u['display_name']})" for u in users}
    target_id = st.selectbox("Chọn tài khoản", list(labels), format_func=labels.get)
    target = next(u for u in users if u["id"] == target_id)

    with st.form("reset_pw_form", clear_on_submit=True):
        new_pw = st.text_input("Mật khẩu mới", type="password")
        if st.form_submit_button("🔑 Đổi mật khẩu"):
            ok, msg = reset_password(target_id, new_pw)
            (st.success if ok else st.error)(msg)

    if not target["is_admin"]:
        confirm = st.checkbox(f"Tôi chắc chắn muốn xóa '{target['username']}' và toàn bộ tiến độ của họ")
        if st.button("🗑️ Xóa tài khoản", disabled=not confirm):
            ok, msg = delete_user(target_id)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()


def _render_backup():
    st.markdown("### ☁️ Sao lưu & khôi phục (Google Drive)")
    st.caption(
        "Tiến độ của mọi người tự lưu liên tục. Sao lưu ở đây là bản dự phòng gửi lên Drive của admin "
        "(giữ 8 bản gần nhất, mật khẩu đã được mã hóa)."
    )
    if not using_turso():
        st.info("Đang chạy chế độ cục bộ (chưa cấu hình Turso): dữ liệu nằm trong file user_data.db trên máy này.")

    last = get_meta("last_backup_at")
    days = _days_since(last)
    if days is None:
        st.warning("⚠️ Chưa có bản sao lưu nào. Hãy sao lưu ngay!")
    elif days >= BACKUP_REMINDER_DAYS:
        st.warning(f"⚠️ Đã {days} ngày chưa sao lưu. Nên sao lưu mỗi tuần một lần.")
    else:
        st.success(f"Lần sao lưu gần nhất: {days} ngày trước.")

    if st.button("📤 Sao lưu tiến độ mọi người lên Drive", use_container_width=True):
        with st.spinner("Đang đồng bộ lên Google Drive..."):
            ok, msg = backup_to_drive()
        (st.success if ok else st.error)(msg)

    st.markdown("**Khôi phục từ Drive**")
    backups = list_progress_backups()
    if not backups:
        st.caption("Chưa tìm thấy bản sao lưu nào trên Drive.")
        return
    names = {b["id"]: f"{b['name']}" for b in backups}
    file_id = st.selectbox("Chọn bản sao lưu", list(names), format_func=names.get)
    st.error("Khôi phục sẽ **ghi đè toàn bộ** tiến độ hiện tại của mọi người và đăng xuất tất cả.")
    confirm = st.checkbox("Tôi hiểu và muốn khôi phục bản này")
    if st.button("📥 Khôi phục", disabled=not confirm, use_container_width=True):
        with st.spinner("Đang tải và khôi phục..."):
            ok, msg = restore_from_drive(file_id)
        if ok:
            st.session_state.clear()
            st.rerun()
        else:
            st.error(msg)


def render_admin_panel():
    st.subheader("👑 Quản Lý Hệ Thống")
    _render_accounts()
    st.divider()
    _render_backup()
