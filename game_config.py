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
MONSTER_HITS = 10           # số đòn gốc để hạ một yêu thú thường (phiên 10: +3 từ 7)
MONSTER_MIN_HITS = 4        # dù pháp bảo mạnh cũng cần ít nhất ngần này câu đúng
BOSS_HITS = 18              # boss cần đủ 18 câu đúng (phiên 10: +3 từ 15)
MONSTER_ATK_RATIO = 0.14    # sát thương yêu thú trên HP gốc người chơi (phiên 10: +0.03 từ 0.11)
BOSS_ATK_RATIO = 0.17       # (phiên 10: +0.03 từ 0.14)
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
CULTIVATION_BOOST_ATK_PCT = 5.0      # tăng 5% sát thương cơ bản mỗi cấp tu vi
CULTIVATION_BOOST_HP_PCT = 5.0       # tăng 5% HP cơ bản mỗi cấp tu vi
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

# ---------------------------------------------------------------------------
# Phiên 4: Công thức luyện đan (Alchemy System)
# ---------------------------------------------------------------------------
PILL_RECIPES = [
    {
        "code": "pill_1",
        "name": "Hạ Phẩm Yêu Đan",
        "min_realm": 0,
        "materials": [("r0_0", 2), ("r0_1", 1)],  # 2x Hắc Thiết, 1x Yêu Lang Bì
        "bonus_atk_pct": 2.0,
        "success_rate": 0.80,
    },
    {
        "code": "pill_2",
        "name": "Trung Phẩm Yêu Đan",
        "min_realm": 3,
        "materials": [("r0_3", 2), ("pill_1", 1)],  # 2x Tinh Thiết, 1x Hạ Phẩm Yêu Đan
        "bonus_atk_pct": 5.0,
        "success_rate": 0.70,
    },
    {
        "code": "pill_3",
        "name": "Thượng Phẩm Yêu Đan",
        "min_realm": 6,
        "materials": [("r1_2", 3), ("r1_4", 2)],  # 3x Huyền Thiết, 2x Xích Tinh Thạch
        "bonus_atk_pct": 8.0,
        "success_rate": 0.60,
    },
    {
        "code": "pill_4",
        "name": "Tối Thượng Yêu Đan",
        "min_realm": 10,
        "materials": [("r2_0", 3), ("r2_4", 2), ("r2_5", 1)],  # 3x Hàn Thiết, 2x Thiên Lôi Mộc, 1x Hàn Ngọc
        "bonus_atk_pct": 12.0,
        "success_rate": 0.50,
    },
    {
        "code": "pill_5",
        "name": "Tôn Thần Yêu Đan",
        "min_realm": 15,
        "materials": [("r3_2", 4), ("r3_4", 3), ("r3_5", 1)],  # 4x Linh Mộc Tâm, 3x Thiên Lôi Mộc, 1x Tiên Duyên
        "bonus_atk_pct": 15.0,
        "success_rate": 0.40,
    },
]

# Bảng giá mua công thức (Linh Thạch)
PILL_RECIPE_PRICES = {
    "pill_1": 50,
    "pill_2": 200,
    "pill_3": 500,
    "pill_4": 1500,
    "pill_5": 3000,
}

# Mapping nhanh
PILL_RECIPES_BY_CODE = {p["code"]: p for p in PILL_RECIPES}

# Phiên 5: Cấu hình mini-game Luyện Đan
ALCHEMIST_MIN_WORDS = 4          # Mở khóa mini-game khi đã học ≥ 4 từ
ALCHEMIST_MAX_LEARNED = 30       # Nếu > 30 từ đã học, bắt buộc giữ tất cả
ALCHEMIST_PAIRS_PER_RECIPE = {
    "pill_1": 3,   # Hạ Phẩm: 3 cặp từ
    "pill_2": 4,   # Trung Phẩm: 4 cặp từ
    "pill_3": 5,   # Thượng Phẩm: 5 cặp từ
    "pill_4": 6,   # Tối Thượng: 6 cặp từ
    "pill_5": 7,   # Tôn Thần: 7 cặp từ
}

# Tên vật phẩm (cho Phase 4-5)
ITEM_NAMES = {
    "r0_0": "Hắc Thiết",
    "r0_1": "Yêu Lang Bì",
    "r0_2": "Thanh Linh Thảo",
    "r0_3": "Tinh Thiết",
    "r0_4": "Hạ Phẩm Yêu Đan",
    "r0_5": "Linh Mộc Tâm",
    
    "r1_0": "Huyền Thiết",
    "r1_1": "Hỏa Giao Lân",
    "r1_2": "Tử Linh Chi",
    "r1_3": "Xích Tinh Thạch",
    "r1_4": "Trung Phẩm Yêu Đan",
    "r1_5": "Kim Đan Tinh Hoa",
    
    "r2_0": "Hàn Thiết",
    "r2_1": "Băng Giao Cốt",
    "r2_2": "Tuyết Liên Diệp",
    "r2_3": "Hàn Ngọc",
    "r2_4": "Lôi Tinh",
    "r2_5": "Thiên Lôi Mộc",
    
    "r3_0": "U Minh Thiết",
    "r3_1": "Hoang Mạc Sa Tinh",
    "r3_2": "Vân Hải Linh Tảo",
    "r3_3": "Cố Ngọc",
    "r3_4": "Thiên Lôi Mộc",
    "r3_5": "Tiên Duyên",
    
    "pill_1": "Hạ Phẩm Yêu Đan",
    "pill_2": "Trung Phẩm Yêu Đan",
    "pill_3": "Thượng Phẩm Yêu Đan",
    "pill_4": "Tối Thượng Yêu Đan",
    "pill_5": "Tôn Thần Yêu Đan",
}

# ---------------------------------------------------------------------------
# Phiên 6: Công thức vẽ phù (Talisman System)
# ---------------------------------------------------------------------------
TALISMAN_RECIPES = [
    {
        "code": "talisman_1",
        "name": "Bảo Hộ Phù",
        "min_realm": 1,
        "correct_hits_needed": 10,
        "description": "Phù bảo hộ toàn thân, giảm sát thương nhận",
        "effects": {
            "damage_reduction": 0.15,  # Giảm 15% sát thương
            "duration": 2,  # Hiệu lực 2 trận
        }
    },
    {
        "code": "talisman_2",
        "name": "Tăng Công Phù",
        "min_realm": 3,
        "correct_hits_needed": 15,
        "description": "Phù tăng sát thương, cộng thêm công kích",
        "effects": {
            "atk_bonus_pct": 20.0,  # Tăng 20% sát thương
            "duration": 2,
        }
    },
    {
        "code": "talisman_3",
        "name": "Hồi Phục Phù",
        "min_realm": 5,
        "correct_hits_needed": 20,
        "description": "Phù hồi phục sức khỏe trong trận đấu",
        "effects": {
            "hp_restore_pct": 30.0,  # Hồi 30% HP
            "duration": 1,
        }
    },
    {
        "code": "talisman_4",
        "name": "Phản Công Phù",
        "min_realm": 8,
        "correct_hits_needed": 25,
        "description": "Phù phản công, bất kỳ khi nào bị đánh sẽ phản lại",
        "effects": {
            "reflect_damage_pct": 25.0,  # Phản lại 25% sát thương
            "duration": 2,
        }
    },
    {
        "code": "talisman_5",
        "name": "Trúc Chi Phù",
        "min_realm": 11,
        "correct_hits_needed": 30,
        "description": "Phù chính xác, tăng tỉ lệ chí mạng",
        "effects": {
            "crit_chance_bonus": 15.0,  # Tăng 15% tỉ lệ chí mạng
            "duration": 2,
        }
    },
    {
        "code": "talisman_6",
        "name": "Trời Địa Phù",
        "min_realm": 14,
        "correct_hits_needed": 35,
        "description": "Phù tối thượng, kết hợp tất cả hiệu ứng",
        "effects": {
            "damage_reduction": 10.0,  # -10% sát thương
            "atk_bonus_pct": 15.0,  # +15% sát thương
            "hp_restore_pct": 20.0,  # Hồi 20% HP
            "reflect_damage_pct": 15.0,  # Phản lại 15% sát thương
            "crit_chance_bonus": 10.0,  # +10% chí mạng
            "duration": 3,
        }
    },
]

# Bảng giá mua công thức phù (Linh Thạch)
TALISMAN_RECIPE_PRICES = {
    "talisman_1": 100,
    "talisman_2": 300,
    "talisman_3": 600,
    "talisman_4": 1200,
    "talisman_5": 2000,
    "talisman_6": 3500,
}

# Mapping nhanh
TALISMAN_RECIPES_BY_CODE = {t["code"]: t for t in TALISMAN_RECIPES}

# Tên phù
TALISMAN_NAMES = {
    "talisman_1": "Bảo Hộ Phù",
    "talisman_2": "Tăng Công Phù",
    "talisman_3": "Hồi Phục Phù",
    "talisman_4": "Phản Công Phù",
    "talisman_5": "Trúc Chi Phù",
    "talisman_6": "Trời Địa Phù",
}

# ---------------------------------------------------------------------------
# Phiên 8: Công Pháp (Tâm Pháp & Bí Pháp) - Rơi từ Boss
# ---------------------------------------------------------------------------
# 5 cấp công pháp x 2 loại (tâm pháp +HP, bí pháp +ATK)
# Rơi khi đánh boss thắng; tỉ lệ rơi phụ thuộc cấp độ
TECHNIQUE_GRADES = ("Xâm Cơ", "Dị Nhân", "Thiên Tài", "Thánh Tích", "Thần Tích")  # 5 cấp
TECHNIQUE_COLORS = ("#808080", "#4CAF50", "#2196F3", "#FF9800", "#F44336")  # Xám, Xanh lá, Xanh dương, Cam, Đỏ
TECHNIQUE_LINES_MAP = (2, 3, 4, 5, 6)  # Số dòng chỉ số cho mỗi cấp

TECHNIQUES = [
    {"code": "qingfeng_jian", "name": "Thanh Phong Kiếm", "kind": "secret", "grade": 0, "emoji": "🌪️", "size": (3, 3), "hp_mult": 0.0000, "atk_mult": 0.1800},
    {"code": "danjian_fa", "name": "Đơn Kiếm Pháp", "kind": "secret", "grade": 0, "emoji": "🌟", "size": (2, 2), "hp_mult": 0.0000, "atk_mult": 0.0800},
    {"code": "shuangjian_fa", "name": "Song Kiếm Pháp", "kind": "secret", "grade": 0, "emoji": "🏵️", "size": (2, 2), "hp_mult": 0.0000, "atk_mult": 0.0800},
    {"code": "kuangjian_fa", "name": "Cuồng Kiếm Pháp", "kind": "secret", "grade": 0, "emoji": "🎆", "size": (2, 3), "hp_mult": 0.0000, "atk_mult": 0.1200},
    {"code": "lingfa_jian", "name": "Linh Pháp Kiếm", "kind": "secret", "grade": 0, "emoji": "🗡️", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0200},
    {"code": "liantai_gong", "name": "Luyện Tai Công", "kind": "secret", "grade": 0, "emoji": "⚔️", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0200},
    {"code": "lianjue_gong", "name": "Luyện Quyết Công", "kind": "secret", "grade": 0, "emoji": "🔱", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0400},
    {"code": "jianqi_gong", "name": "Kiếm Khí Công", "kind": "secret", "grade": 0, "emoji": "⚡", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0400},
    {"code": "qilin_gong", "name": "Kỳ Lân Công", "kind": "secret", "grade": 0, "emoji": "🔥", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0200},
    {"code": "fengwu_gong", "name": "Phong Vũ Công", "kind": "secret", "grade": 0, "emoji": "💨", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0400},
    {"code": "dantian_gong", "name": "Đan Điền Công", "kind": "heart", "grade": 0, "emoji": "🌺", "size": (3, 3), "hp_mult": 0.1800, "atk_mult": 0.0000},
    {"code": "taiji_gong", "name": "Thái Cực Công", "kind": "heart", "grade": 0, "emoji": "💓", "size": (2, 2), "hp_mult": 0.0800, "atk_mult": 0.0000},
    {"code": "wuwei_gong", "name": "Vô Vị Công", "kind": "heart", "grade": 0, "emoji": "❤️", "size": (2, 2), "hp_mult": 0.0800, "atk_mult": 0.0000},
    {"code": "hunyuan_gong", "name": "Hỗn Nguyên Công", "kind": "heart", "grade": 0, "emoji": "🔴", "size": (2, 3), "hp_mult": 0.1200, "atk_mult": 0.0000},
    {"code": "taichi_basic", "name": "Thái Cực Công Cơ Bản", "kind": "heart", "grade": 0, "emoji": "💝", "size": (1, 1), "hp_mult": 0.0200, "atk_mult": 0.0000},
    {"code": "duyinyang", "name": "Độc Âm Dương", "kind": "heart", "grade": 0, "emoji": "💗", "size": (1, 1), "hp_mult": 0.0200, "atk_mult": 0.0000},
    {"code": "qihai_gong", "name": "Khí Hải Công", "kind": "heart", "grade": 0, "emoji": "💕", "size": (1, 2), "hp_mult": 0.0400, "atk_mult": 0.0000},
    {"code": "jiuyang_gong", "name": "Cửu Dương Công", "kind": "heart", "grade": 0, "emoji": "💖", "size": (1, 2), "hp_mult": 0.0400, "atk_mult": 0.0000},
    {"code": "qingxu_gong", "name": "Thanh Hư Công", "kind": "heart", "grade": 0, "emoji": "🎀", "size": (1, 1), "hp_mult": 0.0200, "atk_mult": 0.0000},
    {"code": "yinyang_jue", "name": "Âm Dương Quyết", "kind": "heart", "grade": 0, "emoji": "🌀", "size": (1, 2), "hp_mult": 0.0400, "atk_mult": 0.0000},
    {"code": "yuanli_jian", "name": "Viễn Lý Kiếm", "kind": "secret", "grade": 1, "emoji": "🌪️", "size": (3, 3), "hp_mult": 0.0000, "atk_mult": 0.2200},
    {"code": "tianya_jian", "name": "Thiên Ngoại Kiếm", "kind": "secret", "grade": 1, "emoji": "🌟", "size": (2, 2), "hp_mult": 0.0000, "atk_mult": 0.1000},
    {"code": "yuanrong_gong", "name": "Viên Dung Công", "kind": "secret", "grade": 1, "emoji": "🏵️", "size": (2, 2), "hp_mult": 0.0000, "atk_mult": 0.1000},
    {"code": "shenhuo_jue", "name": "Thần Hỏa Quyết", "kind": "secret", "grade": 1, "emoji": "🎆", "size": (2, 3), "hp_mult": 0.0000, "atk_mult": 0.1500},
    {"code": "chixiao_jian", "name": "Chích Tiếu Kiếm", "kind": "secret", "grade": 1, "emoji": "🗡️", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0250},
    {"code": "tianyin_gong", "name": "Thiên Âm Công", "kind": "secret", "grade": 1, "emoji": "⚔️", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0250},
    {"code": "xuanwu_jue", "name": "Huyền Vũ Quyết", "kind": "secret", "grade": 1, "emoji": "🔱", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0500},
    {"code": "fengpao_gong", "name": "Phong Pao Công", "kind": "secret", "grade": 1, "emoji": "⚡", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0500},
    {"code": "phoenix_gong", "name": "Phượng Hoàng Công", "kind": "secret", "grade": 1, "emoji": "🔥", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0250},
    {"code": "dragon_gong", "name": "Long Công", "kind": "secret", "grade": 1, "emoji": "💨", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0500},
    {"code": "tianxin_gong", "name": "Thiên Tâm Công", "kind": "heart", "grade": 1, "emoji": "🌺", "size": (3, 3), "hp_mult": 0.2200, "atk_mult": 0.0000},
    {"code": "bagua_zhang", "name": "Bát Quái Chưởng", "kind": "heart", "grade": 1, "emoji": "💗", "size": (2, 2), "hp_mult": 0.1000, "atk_mult": 0.0000},
    {"code": "shaolin_gong", "name": "Thiếu Lâm Công", "kind": "heart", "grade": 1, "emoji": "💓", "size": (2, 2), "hp_mult": 0.1000, "atk_mult": 0.0000},
    {"code": "wudang_jue", "name": "Võ Đương Quyết", "kind": "heart", "grade": 1, "emoji": "❤️", "size": (2, 3), "hp_mult": 0.1500, "atk_mult": 0.0000},
    {"code": "emei_gong", "name": "Émeimei Công", "kind": "heart", "grade": 1, "emoji": "🔴", "size": (2, 2), "hp_mult": 0.1000, "atk_mult": 0.0000},
    {"code": "jiemai_gong", "name": "Nhất Mạch Công", "kind": "heart", "grade": 1, "emoji": "💝", "size": (1, 1), "hp_mult": 0.0250, "atk_mult": 0.0000},
    {"code": "liuhe_jue", "name": "Lục Hợp Quyết", "kind": "heart", "grade": 1, "emoji": "💕", "size": (1, 2), "hp_mult": 0.0500, "atk_mult": 0.0000},
    {"code": "xingyi_quan", "name": "Hình Ý Quyền", "kind": "heart", "grade": 1, "emoji": "💖", "size": (1, 2), "hp_mult": 0.0500, "atk_mult": 0.0000},
    {"code": "daxuan_gong", "name": "Đại Tuyên Công", "kind": "heart", "grade": 1, "emoji": "🎀", "size": (1, 1), "hp_mult": 0.0250, "atk_mult": 0.0000},
    {"code": "fuxue_gong", "name": "Phúc Học Công", "kind": "heart", "grade": 1, "emoji": "🌀", "size": (1, 2), "hp_mult": 0.0500, "atk_mult": 0.0000},
    {"code": "shenmo_jian", "name": "Thần Mộ Kiếm", "kind": "secret", "grade": 2, "emoji": "🌪️", "size": (3, 3), "hp_mult": 0.0000, "atk_mult": 0.2700},
    {"code": "jingxin_gong", "name": "Kinh Tâm Công", "kind": "secret", "grade": 2, "emoji": "🌟", "size": (2, 2), "hp_mult": 0.0000, "atk_mult": 0.1200},
    {"code": "lingxiao_jue", "name": "Linh Tiêu Quyết", "kind": "secret", "grade": 2, "emoji": "🏵️", "size": (2, 2), "hp_mult": 0.0000, "atk_mult": 0.1200},
    {"code": "konghai_gong", "name": "Không Hải Công", "kind": "secret", "grade": 2, "emoji": "🎆", "size": (2, 3), "hp_mult": 0.0000, "atk_mult": 0.1800},
    {"code": "shenmo_gong", "name": "Thần Mộ Công", "kind": "secret", "grade": 2, "emoji": "🗡️", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0300},
    {"code": "youming_jue", "name": "Yêu Minh Quyết", "kind": "secret", "grade": 2, "emoji": "⚔️", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0300},
    {"code": "tengshe_gong", "name": "Đằng Xà Công", "kind": "secret", "grade": 2, "emoji": "🔱", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0600},
    {"code": "yuanjue_gong", "name": "Viên Giác Công", "kind": "secret", "grade": 2, "emoji": "⚡", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0600},
    {"code": "jingyao_gong", "name": "Kinh Yêu Công", "kind": "secret", "grade": 2, "emoji": "🔥", "size": (1, 1), "hp_mult": 0.0000, "atk_mult": 0.0300},
    {"code": "chaoyang_gong", "name": "Triều Dương Công", "kind": "secret", "grade": 2, "emoji": "💨", "size": (1, 2), "hp_mult": 0.0000, "atk_mult": 0.0600},
    {"code": "kongming_gong", "name": "Không Minh Công", "kind": "heart", "grade": 2, "emoji": "🌺", "size": (3, 3), "hp_mult": 0.2700, "atk_mult": 0.0000},
    {"code": "lingxi_gong", "name": "Linh Tích Công", "kind": "heart", "grade": 2, "emoji": "💗", "size": (2, 2), "hp_mult": 0.1200, "atk_mult": 0.0000},
    {"code": "huiyuan_gong", "name": "Hồi Nguyên Công", "kind": "heart", "grade": 2, "emoji": "💓", "size": (2, 2), "hp_mult": 0.1200, "atk_mult": 0.0000},
    {"code": "xianyu_jue", "name": "Tiên Vũ Quyết", "kind": "heart", "grade": 2, "emoji": "❤️", "size": (2, 3), "hp_mult": 0.1800, "atk_mult": 0.0000},
    {"code": "zixiao_gong", "name": "Tử Tiêu Công", "kind": "heart", "grade": 2, "emoji": "🔴", "size": (2, 2), "hp_mult": 0.1200, "atk_mult": 0.0000},
    {"code": "kuafu_gong", "name": "Khôi Phù Công", "kind": "heart", "grade": 2, "emoji": "💝", "size": (1, 1), "hp_mult": 0.0300, "atk_mult": 0.0000},
    {"code": "beiming_jue", "name": "Bắc Minh Quyết", "kind": "heart", "grade": 2, "emoji": "💕", "size": (1, 2), "hp_mult": 0.0600, "atk_mult": 0.0000},
    {"code": "longxiang_gong", "name": "Long Tường Công", "kind": "heart", "grade": 2, "emoji": "💖", "size": (1, 2), "hp_mult": 0.0600, "atk_mult": 0.0000},
    {"code": "chaofeng_gong", "name": "Triều Phong Công", "kind": "heart", "grade": 2, "emoji": "🎀", "size": (1, 1), "hp_mult": 0.0300, "atk_mult": 0.0000},
    {"code": "yuanyang_gong", "name": "Viên Dương Công", "kind": "heart", "grade": 2, "emoji": "🌀", "size": (1, 2), "hp_mult": 0.0600, "atk_mult": 0.0000},
]

# Tỉ lệ rơi công pháp khi đánh boss thắng (phụ thuộc cấp độ) - 60 kỹ năng cấp 0-2
TECHNIQUE_DROP_RATES = {
    0: {"rate": 0.15, "grades": [0]},              # Cảnh giới 0-1: 15% rơi, cấp 0
    1: {"rate": 0.15, "grades": [0]},
    2: {"rate": 0.20, "grades": [0, 1]},           # Cảnh giới 2-5: 20% rơi, cấp 0-1
    3: {"rate": 0.20, "grades": [0, 1]},
    4: {"rate": 0.25, "grades": [0, 1]},
    5: {"rate": 0.25, "grades": [0, 1]},
    6: {"rate": 0.30, "grades": [1, 2]},           # Cảnh giới 6-11: 30% rơi, cấp 1-2
    7: {"rate": 0.30, "grades": [1, 2]},
    8: {"rate": 0.35, "grades": [1, 2]},
    9: {"rate": 0.35, "grades": [1, 2]},
    10: {"rate": 0.40, "grades": [2]},             # Cảnh giới 10-15: 40%+ rơi, cấp 2
    11: {"rate": 0.40, "grades": [2]},
    12: {"rate": 0.40, "grades": [2]},
    13: {"rate": 0.45, "grades": [2]},
    14: {"rate": 0.45, "grades": [2]},
    15: {"rate": 0.50, "grades": [2]},             # Cảnh giới 15 (tối cao): 50% rơi, cấp 2
}


# Size multiplier: công pháp lớn = bonus cao
TECHNIQUE_SIZE_MULT = {
    (1, 1): 0.5,    # Rất nhỏ
    (1, 2): 1.0,    # Nhỏ
    (2, 2): 2.0,    # Trung bình
    (2, 3): 3.0,    # Lớn
    (3, 3): 4.5,    # Rất lớn (1/3 dantian)
}

TECHNIQUE_BY_CODE = {t["code"]: t for t in TECHNIQUES}
TECHNIQUE_NAMES = {t["code"]: t["name"] for t in TECHNIQUES}
TECHNIQUE_EMOJI = {t["code"]: t["emoji"] for t in TECHNIQUES}

# Đan điền: không gian xếp công pháp (số lượng ô, kích cỡ)
DANTIAN_ROWS = 4
DANTIAN_COLS = 5
DANTIAN_TOTAL = DANTIAN_ROWS * DANTIAN_COLS  # 20 ô (giảm từ 30)
DANTIAN_SLOT_SIZE = 60  # pixel
