"""Phiên 10: Script kiểm tra và tư vấn điều chỉnh cân bằng.

Không thay đổi game_config.py chưa, chỉ đề xuất các số liệu.
"""

# ============================================================================
# MỤC TIÊU CÂN BẰNG
# ============================================================================

TARGET_RATIOS = {
    "early_game_no_artifact": (0.8, 1.2),  # Người chơi vs quái thường, không pháp bảo
    "mid_game_with_artifact": (0.9, 1.2),  # Người chơi vs tinh anh, có pháp bảo
    "end_game_with_artifact": (0.9, 1.2),  # Người chơi vs tinh anh, có pháp bảo
    "boss": (0.6, 0.9),                    # Khó, cần chiến lược
}

# ============================================================================
# ĐỀ XUẤT ĐIỀU CHỈNH HIỆN TẠI
# ============================================================================

CURRENT_CONFIG = {
    "MONSTER_ATK_RATIO": 0.11,
    "MONSTER_HITS": 7,
    "BOSS_ATK_RATIO": 0.14,
    "ELITE_HP_MULT": 1.4,
    "ELITE_ATK_MULT": 1.25,
}

PROPOSED_OPTIONS = {
    "option_a": {
        "name": "Tăng damage quái (nhẹ)",
        "changes": {
            "MONSTER_ATK_RATIO": 0.125,  # Tăng từ 0.11
            "BOSS_ATK_RATIO": 0.16,      # Tăng từ 0.14
        },
        "rationale": "Quái tấn công mạnh hơn, nhưng vẫn giữ HP như cũ",
    },
    "option_b": {
        "name": "Tăng HP quái (trung bình)",
        "changes": {
            "MONSTER_HITS": 9,  # Tăng từ 7
            "MONSTER_ATK_RATIO": 0.125,
        },
        "rationale": "Quái bền hơn + tấn công mạnh hơn, cân đối",
    },
    "option_c": {
        "name": "Cân bằng toàn diện (khuyến cáo)",
        "changes": {
            "MONSTER_ATK_RATIO": 0.125,
            "MONSTER_HITS": 9,
            "BOSS_ATK_RATIO": 0.16,
            "COMBO_MAX": 4,  # Giảm từ 5 để combo bonus ít hơn
        },
        "rationale": "Tổng hợp tất cả, tạo cân bằng phù hợp nhất",
    },
}

# ============================================================================
# KỲ VỌNG THAY ĐỔI
# ============================================================================

EXPECTED_IMPACT = {
    "option_a": {
        "early_game_ratio": "1.13 -> 0.95 (ổn)",
        "mid_game_ratio": "1.59 -> 1.25 (vẫn dễ hơi)",
        "end_game_ratio": "2.52 -> 2.05 (vẫn quá dễ)",
        "complexity": "Thấp: chỉ thay đổi 2 số",
    },
    "option_b": {
        "early_game_ratio": "1.13 -> 0.92 (ổn)",
        "mid_game_ratio": "1.59 -> 1.05 (ổn)",
        "end_game_ratio": "2.52 -> 1.65 (tốt hơn)",
        "complexity": "Trung bình: thay đổi 2 số",
    },
    "option_c": {
        "early_game_ratio": "1.13 -> 0.92 (ổn)",
        "mid_game_ratio": "1.59 -> 1.00 (tuyệt vời)",
        "end_game_ratio": "2.52 -> 1.55 (tốt)",
        "complexity": "Cao: thay đổi 4 số",
        "note": "COMBO_MAX giảm 5->4 sẽ ảnh hưởng trận đấu, cần test kỹ",
    },
}

# ============================================================================
# CHIẾN LƯỢC KHUYẾN CÁO
# ============================================================================

STRATEGY = """
CHIẾN LƯỢC ĐỀ XUẤT CHO PHIÊN 10:

BƯỚC 1: Triển khai Option B (Trung bình, cân bằng tốt)
  - MONSTER_ATK_RATIO: 0.11 -> 0.125
  - MONSTER_HITS: 7 -> 9
  - BOSS_ATK_RATIO: 0.14 -> 0.16
  - Không thay COMBO_MAX (vì nó ảnh hưởng mechanics)

BƯỚC 2: Chạy test suite (tests/test_phien_10.py)
  - Nếu tỷ lệ trong 0.8-1.2: Hoàn tất
  - Nếu vẫn quá dễ: Tăng MONSTER_ATK_RATIO thêm 0.01 nữa
  - Nếu quá khó: Giảm một chút

BƯỚC 3: Kiểm tra depth scaling
  - Ở depth tối đa, quái vẫn phải khó nhưng không bất khả
  - Boss không bị ảnh hưởng depth, nên vẫn là điểm cân bằng

BƯỚC 4: Kiểm tra combo/crit impact
  - Combo vẫn là phần thưởng (không nên xóa)
  - Crit rate giữ nguyên

LỢI ÍCH:
✓ Người chơi mới: Khó hơn, yêu cầu chiến lược
✓ Người chơi cũ: Vẫn thích thú (không quá khác)
✓ Depth: Vẫn có tác động, quái sâu quả khó
✓ Boss: Vẫn là thách thức, không phải gặt nói chuyện

NGUY HIỂM:
✗ Nếu tăng quá nhiều: Người chơi mới bỏ cuộc
✗ Nếu không test kỹ: Có bug, kế hoạch fail

LỊCH TRÌNH:
1. Sửa game_config.py (5 phút)
2. Chạy tests, debug (30 phút)
3. Kiểm tra mọi trường hợp (30 phút)
4. Commit + báo cáo (5 phút)
"""

print(STRATEGY)
