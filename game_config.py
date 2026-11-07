"""Cấu hình trò chơi tu tiên: mọi con số cân bằng nằm ở đây để chỉnh mà không sửa logic."""

TZ_OFFSET_HOURS = 7  # ngày chơi tính theo giờ Việt Nam (server mây chạy giờ UTC)

# ---------------------------------------------------------------------------
# Cảnh giới: 16 đại cảnh giới x 3 tiểu kỳ, trải đều theo số từ đã học (0 -> HSK 5)
# ---------------------------------------------------------------------------
MAJOR_REALMS = [
    "Linh Khí Kỳ", "Trúc Cơ Kỳ", "Kim Đan Kỳ", "Nguyên Anh Kỳ", "Xuất Khiếu Kỳ", "Hóa Thần Kỳ",
    "Luyện Hư Kỳ", "Hợp Thể Kỳ", "Độ Kiếp Kỳ", "Tán Tiên", "Địa Tiên", "Chân Tiên",
    "Kim Tiên", "Đại La Kim Tiên", "Tiên Tôn", "Tiên Đế",
]
PHAM_REALMS = 9   # 9 cảnh giới đầu thuộc Phàm Giới, 7 cảnh giới có chữ Tiên thuộc Tiên Giới
SUB_REALMS = ("Sơ Kỳ", "Trung Kỳ", "Hậu Kỳ")
HSK4_WORDS = 1200   # xong HSK 4 ở cuối Độ Kiếp Kỳ
HSK5_WORDS = 2500   # xong HSK 5 ở cuối Tiên Đế
REALMS_UNTIL_HSK4 = 9


def _build_thresholds():
    """Số từ tối thiểu để bước vào từng tiểu kỳ (48 mốc)."""
    sub_hsk4 = REALMS_UNTIL_HSK4 * 3
    sub_total = len(MAJOR_REALMS) * 3
    starts = []
    for s in range(sub_total):
        if s < sub_hsk4:
            starts.append(round(s * HSK4_WORDS / sub_hsk4))
        else:
            starts.append(round(HSK4_WORDS + (s - sub_hsk4) * (HSK5_WORDS - HSK4_WORDS) / (sub_total - sub_hsk4)))
    return starts


SUB_THRESHOLDS = _build_thresholds()

# ---------------------------------------------------------------------------
# Kinh tế Linh Thạch
# ---------------------------------------------------------------------------
ECON_SCALE = 1.25          # mỗi đại cảnh giới, thu nhập và giá cả nhân thêm 1.25
BASE_DAY_INCOME = 100      # Linh Thạch của một ngày cày nhẹ ở cảnh giới đầu

MATCH_MAX_PAIRS = 6
MATCH_MIN_PAIRS = 6
MATCH_PAIR_REWARD = 3
MATCH_PERFECT_BONUS = 2

HUNT_NORMAL_REWARD = 8
HUNT_BOSS_REWARD = 80
HUNT_EVENT_REWARD = 3

# ---------------------------------------------------------------------------
# Mở khóa: (cảnh giới tối thiểu, số từ đã học tối thiểu)
# ---------------------------------------------------------------------------
GAME_UNLOCKS = {
    "fortune": {"realm_idx": 0, "words": 4},
    "match": {"realm_idx": 0, "words": 4},
    "hunt": {"realm_idx": 0, "words": 4},
    "grammar_battle": {"realm_idx": 1, "words": 30},  # câu điền từ trong trận đánh
}

# ---------------------------------------------------------------------------
# Quẻ bói hằng ngày
# ---------------------------------------------------------------------------
FORTUNE_TIERS = [("Đại Cát", 0.15), ("Cát", 0.35), ("Bình", 0.50)]
FORTUNE_REWARD = 6  # Linh Thạch khi giải đúng quẻ (nhân hệ số cảnh giới)
FORTUNE_TEXT = {
    "Đại Cát": "Tử khí đông lai, thiên cơ rộng mở. Hôm nay là ngày hợp tu luyện.",
    "Cát": "Linh khí thuận dòng, đạo tâm yên ổn. Có chữ chờ người ngộ ra.",
    "Bình": "Mây nhẹ gió êm, chớ vội chớ chậm. Một chữ cũ đang gõ cửa tâm trí.",
    "Hung": "Tâm ma quấy nhiễu, chữ này còn chưa vững. Hãy ôn lại cho kỹ.",
}
# buff: mã -> (tên, mô tả, giá trị thường, giá trị Đại Cát)
FORTUNE_BUFFS = {
    "ls": ("Linh Thạch Phúc", "Linh Thạch nhận thêm {v}% hôm nay", 10, 20),
    "shield": ("Hộ Thân Phù", "Chắn {v} đòn đầu tiên trong mỗi trận săn hôm nay", 1, 2),
    "drop": ("Thiên Cơ Hiển Lộ", "Tỉ lệ rơi vật phẩm thêm {v}% hôm nay", 20, 40),
}

# ---------------------------------------------------------------------------
# Chiến đấu
# ---------------------------------------------------------------------------
POWER_PER_REALM = 1.25
PLAYER_BASE_HP = 100
PLAYER_BASE_ATK = 12
MONSTER_HITS = 7            # số đòn gốc để hạ một yêu thú thường
MONSTER_MIN_HITS = 4        # dù pháp bảo mạnh cũng cần ít nhất ngần này câu đúng
BOSS_HITS = 15              # boss cần đủ 15 câu đúng
MONSTER_ATK_RATIO = 0.11    # sát thương yêu thú trên HP gốc người chơi
BOSS_ATK_RATIO = 0.14
COMBO_STEP = 0.10
COMBO_MAX = 5
SPECIAL_EVENTS = 3          # số cơ quan phải vượt qua trước khi gặp boss
SPECIAL_MIN_KILLS = 3       # số tinh anh đã hạ trong khu để mở thách đấu boss
ELITE_HP_MULT = 1.4         # tinh anh trâu hơn quái thường
ELITE_ATK_MULT = 1.25
DEPTH_EVERY = 5             # cứ 5 trận thắng liên tiếp trong một lượt vào khu thì "đi sâu" hơn
DEPTH_STEP = 0.05           # mỗi trận thắng tăng 5% HP và sát thương của quái
DEPTH_MAX = 2.5

SKILL_NAME = "Hỏa Cầu Thuật"   # tuyệt kỹ mặc định, bổ sung thêm tuyệt kỹ sau

# Chỉ số tu luyện: bonus = trần × điểm / (điểm + K) (lợi suất giảm dần, không thể vượt trần)
CRIT_MAX, CRIT_K = 0.25, 3000        # Ngộ tính (số câu đáp đúng) -> tỉ lệ chí mạng
CRIT_MULT = 1.5
CAN_CO_HP_MAX, CAN_CO_ATK_MAX, CAN_CO_K = 0.075, 0.075, 1250   # Căn cơ (từ đã học) -> HP và sát thương
DAO_TAM_MAX, DAO_TAM_K = 0.25, 90    # Đạo tâm (chuỗi ngày) -> giảm sát thương Tâm Ma Kiếp
TAM_MA_K = 30                        # cường độ tâm ma T = demons / (demons + K)
TAM_MA_Q_MAJOR = 10                  # số câu Tâm Ma Kiếp ở cuối Đại Thiên Kiếp (50 câu)
TRAPS = [
    ("Cơ Quan Chữ Hán", "Một trận pháp khắc chữ Hán chặn lối, cần giải mã để đi qua."),
    ("Rương Cổ Phong Ấn", "Chiếc rương cổ phát ra linh quang, ấn chú trên nắp đòi một đáp án."),
    ("Bia Đá Thượng Cổ", "Tấm bia đá hiện lên văn tự, chỉ ai hiểu mới được qua."),
    ("Linh Trận Thủ Hộ", "Linh trận thủ hộ xoay chuyển, chờ một lời đáp đúng."),
]

# ---------------------------------------------------------------------------
# Bộ vật phẩm: mỗi bộ dùng chung cho 2 đại cảnh giới liền kề (cảnh giới 2s và 2s+1 rơi bộ s).
# Khu thường rơi vật phẩm phổ thông; khu tinh anh/boss rơi vật phẩm hiếm và quý (core item).
# 6 vật phẩm / bộ: [3 phổ thông, 2 hiếm, 1 quý]: (tên, emoji). Mã vật phẩm: r{bộ}_{0..5}
# ---------------------------------------------------------------------------
ITEM_SETS = [
    {
        "name": "Thanh Vân Địa Giới",
        "items": [("Hắc Thiết", "01_hac_thiet"), ("Yêu Lang Bì", "02_yeu_lang_bi"), ("Thanh Linh Thảo", "03_thanh_linh_thao"),
                  ("Tinh Thiết", "04_tinh_thiet"), ("Hạ Phẩm Yêu Đan", "05_ha_pham_yeu_dan"), ("Linh Mộc Tâm", "06_linh_moc_tam")],
    },
    {
        "name": "Xích Mộc Cương Vực",
        "items": [("Huyền Thiết", "07_huyen_thiet"), ("Hỏa Giao Lân", "08_hoa_giao_lan"), ("Tử Linh Chi", "09_tu_linh_chi"),
                  ("Xích Tinh Thạch", "10_xich_tinh_thach"), ("Trung Phẩm Yêu Đan", "11_trung_pham_yeu_dan"), ("Kim Đan Tinh Hoa", "12_kim_dan_tinh_hoa")],
    },
    {
        "name": "Hàn Lôi Cực Địa",
        "items": [("Hàn Thiết", "13_han_thiet"), ("Băng Giao Cốt", "14_bang_giao_cot"), ("Tuyết Liên Diệp", "15_tuyet_lien_diep"),
                  ("Hàn Ngọc", "16_han_ngoc"), ("Lôi Tinh", "17_loi_tinh"), ("Thiên Lôi Mộc", "18_thien_loi_moc")],
    },
    {
        "name": "Cửu U Vân Hải",
        "items": [("U Minh Thiết", "19_u_minh_thiet"), ("Hoang Mạc Sa Tinh", "20_hoang_mac_sa_tinh"), ("Vân Hải Linh Tảo", "21_van_hai_linh_tao"),
                  ("Cốt Ngọc", "22_cot_ngoc"), ("Giao Long Đan", "23_giao_long_dan"), ("Chiến Hồn Tinh", "24_chien_hon_tinh")],
    },
    {
        "name": "Hỗn Độn Bất Chu",
        "items": [("Hỗn Độn Thiết", "25_hon_don_thiet"), ("Tiên Hải Lân", "26_tien_hai_lan"), ("Bất Chu Linh Chi", "27_bat_chu_linh_chi"),
                  ("Thần Sơn Ngọc", "28_than_son_ngoc"), ("Kỳ Lân Giác", "29_ky_lan_giac"), ("Tiên Ma Tinh Phách", "30_tien_ma_tinh_phach")],
    },
    {
        "name": "Ngọc Hư Tiên Cảnh",
        "items": [("Ngọc Hư Kim", "31_ngoc_hu_kim"), ("Tiên Vân Lân", "32_tien_van_lan"), ("Bích Tiêu Tiên Thảo", "33_bich_tieu_tien_thao"),
                  ("Tiên Linh Ngọc", "34_tien_linh_ngoc"), ("Thanh Loan Vũ", "35_thanh_loan_vu"), ("Thái Cổ Thần Tinh", "36_thai_co_than_tinh")],
    },
    {
        "name": "Cửu Thiên Tinh Hà",
        "items": [("Tinh Hà Thiết", "37_tinh_ha_thiet"), ("Nguyệt Quang Bì", "38_nguyet_quang_bi"), ("Hồng Mông Linh Thảo", "39_hong_mong_linh_thao"),
                  ("Tinh Thần Sa", "40_tinh_than_sa"), ("Địa Mạch Long Đan", "41_dia_mach_long_dan"), ("Hồng Hoang Cốt", "42_hong_hoang_cot")],
    },
    {
        "name": "Thiên Đế Cố Cảnh",
        "items": [("Thiên Đế Thiết", "43_thien_de_thiet"), ("Kim Quang Vũ", "44_kim_quang_vu"), ("Vạn Đạo Linh Thảo", "45_van_dao_linh_thao"),
                  ("Thiên Lộ Tinh Ngọc", "46_thien_lo_tinh_ngoc"), ("Thiên Long Giác", "47_thien_long_giac"), ("Chí Tôn Đạo Quả", "48_chi_ton_dao_qua")],
    },
]
ITEM_SET_COUNT = 8
assert len(ITEM_SETS) == ITEM_SET_COUNT

ITEM_RARITIES = ("common", "rare", "precious")
RARITY_LABEL = {"common": "Phổ thông", "rare": "Hiếm", "precious": "Quý"}
ITEM_LAYOUT = ("common", "common", "common", "rare", "rare", "precious")


def build_items():
    """Danh mục vật phẩm: mã -> thông tin. Mã dạng r{bộ}_{chỉ số}."""
    items = {}
    for s, item_set in enumerate(ITEM_SETS):
        for i, (name, img_code) in enumerate(item_set["items"]):
            items[f"r{s}_{i}"] = {"code": f"r{s}_{i}", "name": name, "emoji": "📦", "img_code": img_code, "folder": "icon item", "region": s,
                                  "rarity": ITEM_LAYOUT[i]}
    items["pham_dan"] = {"code": "pham_dan", "name": "Tụ Phẩm Đan", "emoji": "💊", "img_code": "49_tu_pham_dan", "folder": "icon item", "region": None,
                         "rarity": "special"}
    return items


ITEMS = build_items()

# ---------------------------------------------------------------------------
# Quái, boss và bản đồ. Ảnh: assets/monsters/<mã>.png, assets/boss/<mã>.png (thiếu ảnh -> emoji)
# ---------------------------------------------------------------------------
MONSTERS = [
    ("thanh_phong_lang", "Thanh Phong Lang", "🐺"), ("nhat_muc_xa_yeu", "Nhất Mục Xà Yêu", "🐍"),
    ("hac_loi_dieu", "Hắc Lôi Điểu", "🦅"), ("kim_mao_thu", "Kim Mao Thử", "🐹"),
    ("tu_bi_giao_long", "Tử Bì Giao Long", "🐉"), ("bach_nien_moc_yeu", "Bách Niên Mộc Yêu", "🌳"),
    ("thuc_nhan_hoa", "Thực Nhân Hoa", "🌺"), ("cuong_thiet_tru", "Cuồng Thiết Trư", "🐗"),
    ("thiem_dien_bao", "Thiểm Điện Báo", "🐆"), ("tam_dau_yeu_su", "Tam Đầu Yêu Sư", "🦁"),
    ("cu_xi_hac_ho", "Cự Xỉ Hắc Hổ", "🐅"),
]
BOSSES = [
    ("ty_huu", "Tỳ Hưu", "🦁"), ("thong_thien_cu_vien", "Thông Thiên Cự Viên", "🦍"),
    ("phuong_hoang", "Phượng Hoàng", "🦚"), ("thao_thiet", "Thao Thiết", "👹"),
    ("ky_lan", "Kỳ Lân", "🦄"), ("dai_bang_kim_xi_dieu", "Đại Bàng Kim Xí Điểu", "🦅"),
    ("bach_ho", "Bạch Hổ", "🐅"), ("huyen_vu", "Huyền Vũ", "🐢"),
    ("thanh_long", "Thanh Long", "🐲"), ("cuu_vi_thien_ho", "Cửu Vĩ Thiên Hồ", "🦊"),
]

# Mỗi cảnh giới 2 khu: khu thường (quái thường) và khu tinh anh + boss.
# (tên khu thường, x, y, tên khu tinh anh, x, y) — x, y là pixel trên ảnh map đã thu nhỏ 1595x890
MAP_W, MAP_H = 1595, 890
MAP_ICON_OFFSET_Y = -40   # nút bấm đặt phía trên nhãn tên, trúng hình đảo/địa danh
_AREA_DATA = [
    ("Thanh Khê Thôn", 117, 578, "Bích Thảo Nguyên", 283, 547),
    ("Linh Tuyền Trấn", 448, 551, "Hắc Mộc Lâm", 617, 559),
    ("Vạn Kiếm Sơn Trang", 343, 806, "U Minh Thành", 433, 759),
    ("Huyễn Vụ Chiểu Trạch", 607, 732, "Đoạn Hồn Nhai", 700, 706),
    ("Liệt Hỏa Sơn", 805, 558, "U Đầm Cốc", 931, 626),
    ("Băng Thành", 1033, 763, "Cấm Địa Hỏa Vực", 1139, 640),
    ("Bí Cảnh Động Phủ", 1046, 541, "Vạn Yêu Sào", 1257, 545),
    ("Cổ Di Tích", 1316, 760, "Vạn Niên Diễm Uyên", 1383, 615),
    ("Cửu Trọng Lôi Hải", 1494, 588, "Phi Thăng Thiên Đài", 1498, 771),
    ("Tru Tiên Nhai", 136, 258, "Nhiễm Ma Tiên Đầm", 337, 194),
    ("Tử Hà Cổ Động", 295, 325, "Bách Thảo Tiên Cung", 458, 319),
    ("Thiên Tuyền Giang", 711, 305, "Ngọc Hư Phong", 532, 192),
    ("Thái Ất Tiên Khư", 905, 319, "Kim Diễm Linh Trì", 1111, 344),
    ("Đại La Vạn Tiên Đảo", 1028, 209, "Vạn Đạo Tôn Điện", 1246, 230),
    ("Thần Lăng Tiên Uyên", 1170, 150, "Cửu Tiêu Băng Cung", 1300, 380),   # Thần Lăng chưa có nhãn trên ảnh
    ("Tuyên Cổ Điện", 1480, 378, "Vĩnh Hằng Đế Thành", 1427, 173),
]
assert len(_AREA_DATA) == len(MAJOR_REALMS)


def build_areas():
    """Danh sách 32 khu: chỉ số = 2 * cảnh giới + (0 khu thường | 1 khu tinh anh + boss)."""
    areas = []
    for r, (n_name, nx, ny, e_name, ex, ey) in enumerate(_AREA_DATA):
        common = {"realm": r, "item_set": r // 2}
        areas.append({**common, "kind": "normal", "name": n_name, "x": nx, "y": ny,
                      "monsters": [MONSTERS[(2 * r) % len(MONSTERS)], MONSTERS[(2 * r + 1) % len(MONSTERS)]]})
        areas.append({**common, "kind": "elite", "name": e_name, "x": ex, "y": ey,
                      "monsters": [MONSTERS[(2 * r + 5) % len(MONSTERS)], MONSTERS[(2 * r + 6) % len(MONSTERS)]],
                      "boss": BOSSES[r % len(BOSSES)]})
    return areas


AREAS = build_areas()
AREA_KIND_LABEL = {"normal": "Khu săn quái", "elite": "Khu tinh anh & Boss"}


def world_of(realm_idx):
    return "Phàm Giới" if realm_idx < PHAM_REALMS else "Tiên Giới"


# Rơi vật phẩm (số lần quay, số lượng mỗi lần ...)
DROP_NORMAL = {"common_rolls": 2, "common_qty": (1, 2)}
DROP_ELITE = {"common_rolls": 1, "common_qty": (1, 2), "rare_chance": 0.5, "precious_chance": 0.04}
DROP_BOSS = {"common_rolls": 4, "common_qty": (1, 3), "rare_rolls": 2, "rare_qty": (1, 2), "precious_chance": 0.40}
DROP_EVENT = {"common_chance": 0.7, "common_qty": (1, 2)}
HUNT_ELITE_REWARD = 14

# ---------------------------------------------------------------------------
# Pháp bảo: 5 cấp x 3 phẩm. Mỗi bí phương cố định hình dáng + cấp + vùng nguyên liệu.
# Ảnh tùy chọn: assets/artifacts/<mã>.png (hoặc .webp/.jpg)
# ---------------------------------------------------------------------------
ARTIFACT_TIERS = {
    "linh_khi": {"name": "Linh Khí", "emoji": "🗡️", "days": 4, "order": 0,
                 "need": {"common": (6, 4, 0), "rare": (1, 0), "precious": 0}},
    "phap_bao": {"name": "Pháp Bảo", "emoji": "🛡️", "days": 6, "order": 1,
                 "need": {"common": (8, 6, 4), "rare": (2, 1), "precious": 1}},
    "linh_bao": {"name": "Linh Bảo", "emoji": "🔱", "days": 8, "order": 2,
                 "need": {"common": (10, 8, 6), "rare": (3, 2), "precious": 1}},
    "tien_bao": {"name": "Tiên Bảo", "emoji": "⚜️", "days": 10, "order": 3,
                 "need": {"common": (12, 10, 8), "rare": (4, 3), "precious": 2}},
    "tien_khi": {"name": "Tiên Khí", "emoji": "👑", "days": 12, "order": 4,
                 "need": {"common": (14, 12, 10), "rare": (5, 4), "precious": 3}},
}
QUALITY_NAMES = ("Hạ Phẩm", "Trung Phẩm", "Thượng Phẩm")
QUALITY_MULT = (1.0, 1.25, 1.6)
QUALITY_ODDS = (0.60, 0.30, 0.10)
QUALITY_ODDS_PILL = (0.40, 0.40, 0.20)
PITY_MID_AT = 6      # sau 5 lần chế không ra >= Trung Phẩm thì lần 6 chắc chắn
PITY_HIGH_AT = 12    # sau 11 lần chế không ra Thượng Phẩm thì lần 12 chắc chắn
RECIPE_PRICE_DAYS = 1.5
PILL_PRICE_DAYS = 1.0

# Mã bí phương = tên file ảnh. kind: atk (tăng công) | def (tăng HP).
# region = bộ vật phẩm cần (= cảnh giới tối thiểu // 2): nguyên liệu farm ở 2 khu của cảnh giới đó.
RECIPES = [
    {"code": "thanh_phong_kiem", "name": "Thanh Phong Kiếm", "tier": "linh_khi", "kind": "atk", "region": 0, "min_idx": 0},
    {"code": "ho_tam_kinh", "name": "Hộ Tâm Kính", "tier": "linh_khi", "kind": "def", "region": 0, "min_idx": 1},
    {"code": "xich_diem_dao", "name": "Xích Diễm Đao", "tier": "phap_bao", "kind": "atk", "region": 1, "min_idx": 2},
    {"code": "huyen_quy_thuan", "name": "Huyền Quy Thuẫn", "tier": "phap_bao", "kind": "def", "region": 1, "min_idx": 3},
    {"code": "han_bang_chau", "name": "Hàn Băng Châu", "tier": "linh_bao", "kind": "atk", "region": 2, "min_idx": 5},
    {"code": "cuu_uu_phien", "name": "Cửu U Phiên", "tier": "linh_bao", "kind": "def", "region": 3, "min_idx": 6},
    {"code": "van_hai_chung", "name": "Vân Hải Chung", "tier": "tien_bao", "kind": "def", "region": 4, "min_idx": 8},
    {"code": "hon_don_an", "name": "Hỗn Độn Ấn", "tier": "tien_bao", "kind": "atk", "region": 5, "min_idx": 10},
    {"code": "ngoc_hu_tien_kiem", "name": "Ngọc Hư Tiên Kiếm", "tier": "tien_khi", "kind": "atk", "region": 6, "min_idx": 12},
]
assert all(r["region"] == r["min_idx"] // 2 for r in RECIPES)
RECIPE_BY_CODE = {r["code"]: r for r in RECIPES}
LEGACY_RECIPE_CODES = {"lk1": "thanh_phong_kiem", "lk2": "ho_tam_kinh", "pb1": "xich_diem_dao", "pb2": "huyen_quy_thuan",
                       "lb1": "han_bang_chau", "lb2": "cuu_uu_phien", "tb1": "van_hai_chung", "tb2": "hon_don_an",
                       "tk1": "ngoc_hu_tien_kiem"}
KIND_LABEL = {"atk": "Công", "def": "Thủ"}
ARTIFACT_SLOTS = 2
SELL_REFUND_RATIO = 0.5    # bán pháp bảo hoàn 50% Linh Thạch chế tạo (không tính nâng cấp)
ARTIFACT_PCT_PER_TIER = 0.04   # +% sức công/HP gốc của người chơi, nhân số bậc (1-5), phẩm và cấp nâng

ARTIFACT_ATK_RATIO = 0.7   # cộng thêm so với sức công gốc tại cảnh giới tối thiểu của pháp bảo công
ARTIFACT_HP_RATIO = 0.5    # tương tự cho HP của pháp bảo thủ
UPGRADE_MAX = 9
UPGRADE_STAT_STEP = 0.10
UPGRADE_LS_RATIO = 0.12    # trên giá chế tạo, nhân (1 + 0.4 * cấp hiện tại)
UPGRADE_BASE_MATERIALS = 2

# ---------------------------------------------------------------------------
# Danh hào (10 bậc, tương ứng với Tiên Định Cảnh Giới)
# ---------------------------------------------------------------------------
HONOR_TITLES = [
    {"code": "so_nhap_tien_lo", "name": "Sơ nhập tiên lộ", "realm_idx": 0, "atk_pct": 3, "hp_pct": 0},
    {"code": "chan_nhan", "name": "Chân nhân", "realm_idx": 2, "atk_pct": 5, "hp_pct": 5},
    {"code": "lao_to", "name": "Lão tổ", "realm_idx": 3, "atk_pct": 7, "hp_pct": 7},
    {"code": "ton_gia", "name": "Tôn giả", "realm_idx": 6, "atk_pct": 9, "hp_pct": 9},
    {"code": "nua_buoc_chi_ton", "name": "Nửa bước chí tôn", "realm_idx": 7, "atk_pct": 12, "hp_pct": 12},
    {"code": "chi_ton_nhan_gian", "name": "Chí tôn nhân gian", "realm_idx": 8, "atk_pct": 15, "hp_pct": 15},
    {"code": "phi_thang_tien_gioi", "name": "Phi thăng tiên giới", "realm_idx": 9, "atk_pct": 17, "hp_pct": 17},
    {"code": "tung_hoang_tien_gioi", "name": "Tung hoành tiên giới", "realm_idx": 10, "atk_pct": 19, "hp_pct": 19},
    {"code": "chi_ton_tien_gioi", "name": "Chí tôn tiên giới", "realm_idx": 14, "atk_pct": 22, "hp_pct": 22},
    {"code": "vinh_hang_tien_de", "name": "Vĩnh hằng Tiên Đế", "realm_idx": 15, "atk_pct": 25, "hp_pct": 25},
]
HONOR_TITLE_BY_CODE = {t["code"]: t for t in HONOR_TITLES}

# Huy hiệu (3 bậc Đồng / Bạc / Vàng) và huy hiệu ẩn
# ---------------------------------------------------------------------------
BADGE_TIER_ICONS = ("🥉", "🥈", "🥇")
BADGE_REWARD_LS = (30, 100, 300)
BADGE_LINES = [
    {"base": "scholar", "counter": "words_learned", "label": "từ vựng đã học", "tiers": (50, 300, 1000),
     "names": ("Sơ Nhập Thư Phòng", "Bác Học Đa Văn", "Vạn Quyển Thư Sinh")},
    {"base": "monster", "counter": "monsters_killed", "label": "yêu thú đã hạ", "tiers": (10, 50, 200),
     "names": ("Trảm Yêu Học Đồ", "Tâm Ma Sát Thủ", "Diệt Yêu Chân Nhân")},
    {"base": "boss", "counter": "bosses_killed", "label": "boss đã hạ", "tiers": (1, 5, 20),
     "names": ("Phá Cấm Giả", "Trấn Ải Tu Sĩ", "Bá Chủ Cấm Địa")},
    {"base": "match", "counter": "matches_played", "label": "ván lật bài", "tiers": (10, 50, 200),
     "names": ("Linh Thạch Học Đồ", "Linh Thạch Sư", "Linh Thạch Đại Sư")},
    {"base": "perfect", "counter": "perfect_matches", "label": "ván lật bài hoàn hảo", "tiers": (1, 10, 50),
     "names": ("Tâm Linh Tương Thông", "Nhất Mục Thập Hành", "Thiên Nhãn Thông")},
    {"base": "fortune", "counter": "fortune_streak_best", "label": "ngày bói quẻ liên tiếp", "tiers": (3, 7, 30),
     "names": ("Đạo Tâm Kiên Định", "Bất Diệt Kim Thân", "Vạn Niên Đạo Quả")},
    {"base": "craft", "counter": "crafts", "label": "pháp bảo đã chế", "tiers": (1, 5, 15),
     "names": ("Luyện Khí Học Đồ", "Luyện Khí Sư", "Thiên Công Đại Sư")},
    {"base": "upgrade", "counter": "upgrades", "label": "lần nâng cấp thành công", "tiers": (1, 10, 30),
     "names": ("Tinh Luyện Sơ Thành", "Bách Luyện Thành Cương", "Thần Binh Thiên Tạo")},
    {"base": "sentence", "counter": "sentences_ok", "label": "câu đã ghép đúng", "tiers": (5, 50, 200),
     "names": ("Văn Tự Sơ Ngộ", "Câu Đạo Tu Sĩ", "Ngôn Xuất Pháp Tùy")},
    {"base": "wealth", "counter": "ls_earned", "label": "Linh Thạch kiếm được", "tiers": (500, 5000, 50000),
     "names": ("Tiểu Phú Tu Sĩ", "Linh Thạch Phú Hào", "Tài Thần Giáng Thế")},
    {"base": "answers", "counter": "answers_correct", "label": "câu trả lời đúng", "tiers": (50, 500, 3000),
     "names": ("Ngộ Tính Sơ Hiển", "Ngộ Tính Phi Phàm", "Thiên Tư Tuyệt Thế")},
]
HIDDEN_BADGES = [
    {"code": "night_owl", "counter": "night_plays", "need": 1, "name": "Dạ Tu Sĩ",
     "desc": "Chơi sau 23 giờ đêm"},
    {"code": "flawless", "counter": "flawless_boss", "need": 1, "name": "Nhất Kiếm Phong Hầu",
     "desc": "Hạ boss mà không mất một giọt máu"},
]
NIGHT_HOUR = 23
