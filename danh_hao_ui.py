"""Giao diện Danh Hào (Phase 12): Hiển thị danh hào theo cột với điều kiện, buff và nút sử dụng."""
import streamlit as st

import game_config as cfg
import game_core as core


def render_danh_hao_tab():
    """Hiển thị tab Danh Hào với layout cột: Danh hào - Điều kiện - Buff - Nút sử dụng."""
    st.markdown("### 🏅 Danh Hào")
    st.caption("Chọn danh hào phù hợp với cảnh giới hiện tại để trang bị buff.")
    
    state = core.get_state()
    realm = core.realm_info(state["counters"].get("words_learned", 0))
    idx = realm["idx"]
    
    # Danh hào hiện trang bị
    current_honor = state.get("title")
    
    # Danh hào có thể trang bị
    available_honors = core.available_honors(idx)
    
    if not available_honors:
        st.info(f"🔒 Hãy đạt Linh Khí Kỳ để mở khóa danh hào đầu tiên.")
        return
    
    # Hiển thị danh hào theo cột
    st.markdown("**Danh hào có sẵn:**")
    
    # Tạo bảng với các cột
    cols = st.columns([2, 2, 2, 1.5])
    with cols[0]:
        st.markdown("**Danh hào**")
    with cols[1]:
        st.markdown("**Điều kiện**")
    with cols[2]:
        st.markdown("**Buff được nhận**")
    with cols[3]:
        st.markdown("**Thao tác**")
    
    st.divider()
    
    # Hiển thị các danh hào
    for honor_code in available_honors:
        honor = cfg.HONOR_TITLE_BY_CODE[honor_code]
        
        # Tính buff
        buff_text = ""
        if honor["atk_pct"] > 0:
            buff_text += f"+{honor['atk_pct']}% công "
        if honor["hp_pct"] > 0:
            buff_text += f"+{honor['hp_pct']}% HP"
        if not buff_text:
            buff_text = "Không có hiệu ứng"
        
        # Điều kiện
        condition_text = f"Cảnh giới: {cfg.MAJOR_REALMS[honor['realm_idx']]} trở lên"
        
        # Status (đã trang bị hay chưa)
        is_equipped = current_honor == honor_code
        status_emoji = "✅" if is_equipped else "⭕"
        
        cols = st.columns([2, 2, 2, 1.5])
        with cols[0]:
            st.markdown(f"{status_emoji} **{honor['name']}**")
        with cols[1]:
            st.markdown(condition_text)
        with cols[2]:
            st.markdown(buff_text)
        with cols[3]:
            if is_equipped:
                st.button(
                    "✅ Đeo", 
                    key=f"honor_equipped_{honor_code}",
                    disabled=True,
                    use_container_width=True
                )
            else:
                if st.button(
                    "🔗 Đeo",
                    key=f"honor_equip_{honor_code}",
                    use_container_width=True
                ):
                    core.equip_title(honor_code)
                    st.rerun()
    
    # Nút tháo danh hào
    st.divider()
    if current_honor:
        st.markdown("**Danh hào hiện tại:**")
        honor = cfg.HONOR_TITLE_BY_CODE.get(current_honor)
        if honor:
            buff_text = ""
            if honor["atk_pct"] > 0:
                buff_text += f"+{honor['atk_pct']}% công "
            if honor["hp_pct"] > 0:
                buff_text += f"+{honor['hp_pct']}% HP"
            st.markdown(f"✅ **{honor['name']}** — {buff_text}")
            
            if st.button("🔓 Tháo danh hào", use_container_width=True):
                core.equip_title(None)
                st.rerun()
    else:
        st.caption("Chưa trang bị danh hào nào.")

