"""
Giao diện công pháp các (Techniques Grid UI) - Phiên 11
Thiết kế mới: Panel danh sách (trái) + Khung đan điền (phải)
"""
import streamlit as st
import game_config as cfg
import game_core as core
from userdb import get_user_db


def current_user_id():
    """Dùng cùng hồ sơ khóa học với trò chơi."""
    return core.current_user_id()


# =====================================================================
# GRID PACKING ALGORITHM - Tối ưu sắp xếp công pháp
# =====================================================================

class DantianGrid:
    """Quản lý grid đan điền 5x5 với placement tự động."""
    
    def __init__(self, rows=cfg.DANTIAN_ROWS, cols=cfg.DANTIAN_COLS):
        self.rows = rows
        self.cols = cols
        # grid[r][c] = technique_id hoặc None
        self.grid = [[None for _ in range(cols)] for _ in range(rows)]
        self.occupied = set()  # set of (r, c) đã chiếm
    
    def load_from_techniques(self, techniques):
        """Nạp vị trí công pháp từ danh sách."""
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]
        self.occupied = set()
        
        for tech in techniques:
            if tech["dantian_row"] >= 0 and tech["dantian_col"] >= 0:
                tech_id = tech["id"]
                code = tech["code"]
                size = cfg.TECHNIQUE_BY_CODE[code]["size"]  # (height, width)
                h, w = size
                
                r, c = tech["dantian_row"], tech["dantian_col"]
                # Đánh dấu toàn bộ diện tích chiếm
                for dr in range(h):
                    for dc in range(w):
                        if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols:
                            self.grid[r + dr][c + dc] = tech_id
                            self.occupied.add((r + dr, c + dc))
    
    def find_first_free_position(self, technique_size):
        """
        Tìm vị trí trống đầu tiên có thể đặt công pháp.
        technique_size = (height, width)
        Trả về (row, col) hoặc None nếu không có chỗ.
        """
        h, w = technique_size
        
        # Scan từ trên xuống, trái sang phải
        for r in range(self.rows):
            for c in range(self.cols):
                # Kiểm tra xem có thể đặt tại (r, c) không
                if self._can_place_at(r, c, h, w):
                    return (r, c)
        
        return None
    
    def _can_place_at(self, row, col, h, w):
        """Kiểm tra xem có thể đặt công pháp size (h, w) tại (row, col) không."""
        if row + h > self.rows or col + w > self.cols:
            return False
        
        for dr in range(h):
            for dc in range(w):
                if self.grid[row + dr][col + dc] is not None:
                    return False
        
        return True
    
    def place_technique(self, technique_id, row, col, size):
        """Đặt công pháp vào grid."""
        h, w = size
        if not self._can_place_at(row, col, h, w):
            return False
        
        for dr in range(h):
            for dc in range(w):
                self.grid[row + dr][col + dc] = technique_id
                self.occupied.add((row + dr, col + dc))
        
        return True
    
    def remove_technique(self, technique_id):
        """Xóa công pháp khỏi grid."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == technique_id:
                    self.grid[r][c] = None
        
        self.occupied = {(r, c) for r in range(self.rows) for c in range(self.cols) 
                        if self.grid[r][c] is not None}
    
    def get_techniques_in_grid(self):
        """Lấy danh sách technique_id đang trong grid (không trùng)."""
        seen = set()
        result = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] is not None and self.grid[r][c] not in seen:
                    result.append(self.grid[r][c])
                    seen.add(self.grid[r][c])
        return result


def _optimize_placement(techniques_to_place):
    """
    Tối ưu placement: xếp gọn nhất.
    Trả về dict {technique_id: (row, col)}.
    """
    # Sắp xếp theo kích thước giảm dần (kích thước lớn xếp trước)
    sorted_techs = sorted(
        techniques_to_place,
        key=lambda t: cfg.TECHNIQUE_BY_CODE[t["code"]]["size"][0] * 
                      cfg.TECHNIQUE_BY_CODE[t["code"]]["size"][1],
        reverse=True
    )
    
    grid = DantianGrid()
    placements = {}
    
    for tech in sorted_techs:
        size = cfg.TECHNIQUE_BY_CODE[tech["code"]]["size"]
        pos = grid.find_first_free_position(size)
        
        if pos:
            r, c = pos
            grid.place_technique(tech["id"], r, c, size)
            placements[tech["id"]] = (r, c)
    
    return placements


# =====================================================================
# UI COMPONENTS
# =====================================================================

def _get_grade_color(grade):
    """Lấy màu theo đẳng cấp."""
    return cfg.TECHNIQUE_COLORS[grade]


def _get_grade_name(grade):
    """Lấy tên đẳng cấp."""
    return cfg.TECHNIQUE_GRADES[grade]


def _render_technique_list_panel(techniques):
    """
    Panel bên trái: Danh sách công pháp.
    Sắp xếp: Đẳng cấp cao → thấp.
    Rê chuột → Tooltip: Tên, Đẳng cấp, Tu vi, Buff chỉ số.
    """
    st.markdown("### 📜 Công Pháp Sở Hữu")
    
    if not techniques:
        st.info("Chưa có công pháp. Hãy đánh boss để nhận.")
        return None
    
    # Sắp xếp: đẳng cấp cao → thấp
    sorted_techs = sorted(techniques, key=lambda t: t["grade"], reverse=True)
    
    # Chia danh sách thành cột
    cols = st.columns(1)
    
    selected_id = None
    
    for tech in sorted_techs:
        code = tech["code"]
        grade = tech["grade"]
        color = _get_grade_color(grade)
        grade_name = _get_grade_name(grade)
        size = cfg.TECHNIQUE_BY_CODE[code]["size"]
        is_in_grid = tech["dantian_row"] >= 0
        
        # Tooltip content
        tooltip_text = (
            f"**{tech['name']}** ({tech['emoji']})\n"
            f"- Đẳng cấp: {grade_name}\n"
            f"- Kích thước: {size[0]}×{size[1]} ô\n"
            f"- Buff: HP +{tech['hp_mult']*100:.1f}%, ATK +{tech['atk_mult']*100:.1f}%\n"
            f"- Loại: {'Tâm Pháp' if tech['kind'] == 'heart' else 'Bí Pháp'}\n"
            f"- Trạng thái: {'✅ Đang sử dụng' if is_in_grid else '❌ Không sử dụng'}"
        )
        
        with st.container(border=True):
            col_icon, col_info = st.columns([1, 5])
            
            with col_icon:
                st.markdown(f"<div style='font-size: 32px; text-align: center; color: {color}'>{tech['emoji']}</div>", 
                           unsafe_allow_html=True)
            
            with col_info:
                st.markdown(
                    f"<span style='color: {color}; font-weight: bold;'>{grade_name}</span> {tech['name']}",
                    unsafe_allow_html=True
                )
                st.caption(f"Size: {size[0]}×{size[1]} | {tech['id']}")
            
            # Nút "Sử dụng" hoặc "Thu hồi"
            if is_in_grid:
                if st.button("🔄 Thu hồi", key=f"recall_{tech['id']}", use_container_width=True):
                    _recall_technique(tech['id'])
                    st.rerun()
            else:
                if st.button("✨ Sử dụng", key=f"use_{tech['id']}", use_container_width=True):
                    selected_id = tech['id']
                    _use_technique(tech['id'])
                    st.rerun()


def _render_dantian_grid(techniques):
    """
    Panel bên phải: Khung đan điền 5×5.
    Hiển thị công pháp đang sử dụng với màu theo đẳng cấp.
    """
    st.markdown("### 💎 Khung Đan Điền")
    
    # Nạp grid từ dữ liệu
    grid = DantianGrid()
    
    # Lọc công pháp đang trong grid
    techniques_in_grid = [t for t in techniques if t["dantian_row"] >= 0]
    grid.load_from_techniques(techniques_in_grid)
    
    # Hiển thị grid bằng HTML/CSS
    html_grid = _build_grid_html(grid, techniques)
    st.markdown(html_grid, unsafe_allow_html=True)
    
    # Thông tin tổng buff
    st.divider()
    _render_buff_summary(techniques_in_grid)
    
    # Nút sắp xếp / Thu hồi tất cả
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 Sắp xếp tối ưu", key="optimize", use_container_width=True):
            _optimize_dantian(techniques)
            st.rerun()
    
    with col2:
        if st.button("♻️ Thu hồi tất cả", key="recall_all", use_container_width=True):
            _recall_all_techniques(techniques)
            st.rerun()


def _build_grid_html(grid, all_techniques):
    """Xây dựng HTML để hiển thị grid."""
    tech_by_id = {t["id"]: t for t in all_techniques}
    
    # Grid 4x5 (DANTIAN_ROWS x DANTIAN_COLS)
    html = f"<div style='display: grid; grid-template-columns: repeat({grid.cols}, 1fr); gap: 8px; margin-bottom: 20px;'>"
    
    # Track which tech_ids we've already rendered (to avoid duplicates)
    rendered_techs = set()
    
    for r in range(grid.rows):
        for c in range(grid.cols):
            tech_id = grid.grid[r][c]
            
            if tech_id is None:
                # Ô trống
                html += (
                    f"<div style='background: #f0f0f0; border: 2px solid #ddd; "
                    f"aspect-ratio: 1; display: flex; align-items: center; justify-content: center; "
                    f"border-radius: 8px; color: #999; font-weight: bold; font-size: 12px;'>"
                    f"{r},{c}</div>"
                )
            elif tech_id not in rendered_techs:
                # Ô có công pháp (chỉ render lần đầu tiên thấy tech_id này)
                tech = tech_by_id.get(tech_id)
                if tech:
                    color = _get_grade_color(tech["grade"])
                    grade_name = _get_grade_name(tech["grade"])
                    size = cfg.TECHNIQUE_BY_CODE[tech["code"]]["size"]
                    tooltip_content = f"{tech['name']} ({size[0]}x{size[1]}) - {grade_name}"
                    
                    html += (
                        f"<div style='background: {color}; border: 3px solid {color}; "
                        f"aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; "
                        f"justify-content: center; border-radius: 8px; color: white; "
                        f"font-weight: bold; padding: 8px; text-align: center; "
                        f"box-shadow: 0 0 12px {color}66; cursor: pointer;' "
                        f"title='{tooltip_content}'>"
                        f"<div style='font-size: 28px;'>{tech['emoji']}</div>"
                        f"<div style='font-size: 10px; margin-top: 4px; text-shadow: 0 0 4px rgba(0,0,0,0.5);'>{tech['name'][:10]}</div>"
                        f"</div>"
                    )
                    rendered_techs.add(tech_id)
            else:
                # Ô này là phần mở rộng của công pháp đã render (đánh dấu bằng overlay)
                tech = tech_by_id.get(tech_id)
                if tech:
                    color = _get_grade_color(tech["grade"])
                    html += (
                        f"<div style='background: {color}; opacity: 0.3; border: 2px dashed {color}; "
                        f"aspect-ratio: 1; border-radius: 8px;'></div>"
                    )
    
    html += "</div>"
    return html


def _render_buff_summary(techniques_in_grid):
    """Hiển thị bảng tổng buff của các công pháp đang sử dụng."""
    st.markdown("#### 📊 Tổng Buff Hiện Tại")
    
    total_hp_mult = sum(t["hp_mult"] for t in techniques_in_grid)
    total_atk_mult = sum(t["atk_mult"] for t in techniques_in_grid)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("❤️ Tổng HP Buff", f"+{total_hp_mult * 100:.1f}%")
    with col2:
        st.metric("⚔️ Tổng ATK Buff", f"+{total_atk_mult * 100:.1f}%")
    
    # Danh sách công pháp chi tiết
    if techniques_in_grid:
        st.markdown("**Danh sách công pháp đang sử dụng:**")
        for tech in techniques_in_grid:
            grade_name = _get_grade_name(tech["grade"])
            st.caption(
                f"{tech['emoji']} {tech['name']} ({grade_name}) "
                f"— HP +{tech['hp_mult']*100:.1f}% | ATK +{tech['atk_mult']*100:.1f}%"
            )
    else:
        st.info("Chưa có công pháp nào được sử dụng.")


# =====================================================================
# CALLBACK FUNCTIONS
# =====================================================================

def _use_technique(technique_id):
    """Sử dụng công pháp: đặt vào ô trống đầu tiên."""
    user_id = current_user_id()
    techniques = core.get_techniques_inventory(user_id)
    
    # Lấy công pháp
    tech = next((t for t in techniques if t["id"] == technique_id), None)
    if not tech:
        st.error("Công pháp không tồn tại")
        return
    
    # Nạp grid
    grid = DantianGrid()
    techniques_in_grid = [t for t in techniques if t["dantian_row"] >= 0]
    grid.load_from_techniques(techniques_in_grid)
    
    # Tìm vị trí trống
    code = tech["code"]
    size = cfg.TECHNIQUE_BY_CODE[code]["size"]
    pos = grid.find_first_free_position(size)
    
    if not pos:
        st.warning(
            "⚠️ Khung đan điền đã đầy!\n\n"
            "Bạn có thể:\n"
            "1. Tháo bớt công pháp hiện tại bằng cách nhấn 'Thu hồi'\n"
            "2. Nhấn 'Sắp xếp tối ưu' để tái tổ chức công pháp\n\n"
            "Vui lòng giải phóng không gian trước khi thêm công pháp mới."
        )
        return
    
    r, c = pos
    success, msg = core.place_technique_in_dantian(user_id, technique_id, r, c)
    
    if success:
        st.success(f"✅ Sử dụng công pháp thành công tại ({r}, {c})")
    else:
        st.error(f"❌ Lỗi: {msg}")


def _recall_technique(technique_id):
    """Thu hồi công pháp từ đan điền."""
    user_id = current_user_id()
    success, msg = core.remove_technique_from_dantian(user_id, technique_id)
    
    if success:
        st.success("✅ Thu hồi công pháp thành công")
    else:
        st.error(f"❌ Lỗi: {msg}")


def _recall_all_techniques(techniques):
    """Thu hồi tất cả công pháp."""
    user_id = current_user_id()
    db = get_user_db()
    
    for tech in techniques:
        if tech["dantian_row"] >= 0:
            db.execute(
                "UPDATE game_techniques SET dantian_row = -1, dantian_col = -1 WHERE id = ?",
                (tech["id"],)
            )
    
    db.commit()
    st.success("✅ Thu hồi tất cả công pháp")


def _optimize_dantian(techniques):
    """Sắp xếp tối ưu các công pháp trong đan điền."""
    user_id = current_user_id()
    db = get_user_db()
    
    # Lấy công pháp đang trong grid
    techniques_in_grid = [t for t in techniques if t["dantian_row"] >= 0]
    
    if not techniques_in_grid:
        st.info("Không có công pháp nào trong khung đan điền.")
        return
    
    # Tối ưu placement
    placements = _optimize_placement(techniques_in_grid)
    
    # Cập nhật database
    for tech_id, (r, c) in placements.items():
        db.execute(
            "UPDATE game_techniques SET dantian_row = ?, dantian_col = ? WHERE id = ?",
            (r, c, tech_id)
        )
    
    db.commit()
    st.success("✅ Sắp xếp tối ưu hoàn tất")


# =====================================================================
# MAIN INTERFACE
# =====================================================================

def render_techniques_tab():
    """Render tab công pháp - Giao diện chính."""
    user_id = current_user_id()
    
    if not user_id:
        st.error("Không tìm thấy thông tin người dùng. Vui lòng đăng nhập lại.")
        return
    
    techniques = core.get_techniques_inventory(user_id)
    
    # Layout 2 cột
    col_left, col_right = st.columns([2, 3])
    
    with col_left:
        _render_technique_list_panel(techniques)
    
    with col_right:
        _render_dantian_grid(techniques)
