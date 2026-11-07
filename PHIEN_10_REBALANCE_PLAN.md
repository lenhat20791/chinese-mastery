"""Phiên 10: Tư vấn điều chỉnh cân bằng.

Phân tích: Hệ thống hiện tại quá dễ cho người chơi.
Khuyến cáo: Tăng hệ số quái/boss để cân bằng được phù hợp hơn.
"""

# ============================================================================
# KẾ HOẠCH ĐIỀU CHỈNH CÂN BẰNG
# ============================================================================

RECOMMENDATIONS = """
PHÂN TÍCH:
- Đầu game: Người chơi không pháp bảo vẫn mạnh hơn quái 13% (nên yếu hơn)
- Giữa game: Người chơi mạnh hơn tinh anh 59% (quá dễ)
- Cuối game: Người chơi mạnh hơn tinh anh 152% (quá dễ)

NGUYÊN NHÂN:
1. MONSTER_ATK_RATIO = 0.11 quá thấp (quái tấn công yếu)
2. MONSTER_HITS = 7 có thể quá thấp (quái HP yếu)
3. Pháp bảo bonus quá cao trong công thức

ĐIỀU CHỈNH ĐỀ XUẤT:

1. TĂNG MONSTER_ATK_RATIO từ 0.11 → 0.13-0.14
   - Hiện tại: Quái realm 8 damage = 100 × 1.25^8 × 0.11 = 66
   - Mới: Quái realm 8 damage = 100 × 1.25^8 × 0.14 = 84
   - Tác động: Người chơi bị tấn công 27% nhiều hơn

2. TĂNG BOSS_ATK_RATIO từ 0.14 → 0.16-0.17
   - Boss sẽ mạnh hơn quái thường ~25% (vừa phải)
   - Giữ cho boss là thách thức thực sự

3. TĂNG MONSTER_HITS từ 7 → 9-10 (lựa chọn)
   - Sẽ tăng HP quái ~30-40%
   - Nên kết hợp với MONSTER_ATK_RATIO

4. ĐIỀU CHỈNH COMBO_MAX từ 5 → 4 (lựa chọn)
   - Giảm lợi ích combo để người chơi không quá mạnh

TÓM TẮT OPTION CÂN BẰNG:

Option A: MONSTER_ATK_RATIO 0.11 → 0.14 (chỉ damage)
- Ưu: Đơn giản, không ảnh hưởng HP
- Nhược: Người chơi bị sát thương nhiều hơn

Option B: MONSTER_HITS 7 → 10 (chỉ HP)
- Ưu: Quái bền hơn, trận đánh lâu hơn
- Nhược: Combo bonus lớn hơn

Option C: Cả hai (đề xuất)
- MONSTER_ATK_RATIO 0.11 → 0.125
- MONSTER_HITS 7 → 9
- BOSS_ATK_RATIO 0.14 → 0.16
- Kết quả: Cân bằng phù hợp, không quá khó

TIÊU CHÍ KIỂM TRA:

Sau khi điều chỉnh, tỷ lệ sức mạnh nên:
- Đầu game: 0.8-1.2 (người chơi không pháp bảo vs quái)
- Giữa game: 0.9-1.2 (người chơi có pháp bảo vs tinh anh)
- Cuối game: 0.9-1.2 (người chơi có pháp bảo vs tinh anh)
- Boss: 0.6-0.9 (khó, cần chiến lược)

DEPTH SCALING:
- Ở depth tối đa, quái realm 15 damage nên tăng từ 312 → ~400
- Sẽ tương đương người chơi không có HP bonus
- Người chơi phải có HP tốt hoặc sử dụng combo chính xác
"""

print(RECOMMENDATIONS)
