"""Cấu hình trò chơi tu tiên: mọi con số cân bằng nằm ở đây để chỉnh mà không sửa logic."""

TZ_OFFSET_HOURS = 7  # ngày chơi tính theo giờ Việt Nam (server mây chạy giờ UTC)

# ---------------------------------------------------------------------------
# Cảnh giới: 16 đại cảnh giới x 3 tiểu kỳ, trải đều theo số từ đã học (0 -> HSK 5)
# ---------------------------------------------------------------------------
MAJOR_REALMS = [
    "Linh Khí Kỳ", "Trúc Cơ Kỳ", "Kim Đan Kỳ", "Nguyên Anh Kỳ", "Xuất Khiếu Kỳ", "Hóa Thần Kỳ",
    "Luyện Hư Kỳ", "Hợp Thể Kỳ", "Độ Kiếp Kỳ", "Tán Tiên", "Kim Tiên", "Chân Tiên",
    "Địa Tiên", "Đại La Kim Tiên", "Tiên Tôn", "Tiên Đế",
]
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
DAILY_FULL_PLAYS = 10      # 10 trận đầu mỗi ngày nhận 100%
DAILY_MID_PLAYS = 30       # trận 11-30 nhận MULT_MID, từ trận 31 nhận MULT_LOW
MULT_MID = 0.4
MULT_LOW = 0.1

MATCH_MAX_PAIRS = 6
MATCH_MIN_PAIRS = 3
MATCH_PAIR_REWARD = 2
MATCH_PERFECT_BONUS = 2

SENTENCE_ROUNDS = 5
SENTENCE_REWARD = 3
SENTENCE_PERFECT_BONUS = 4

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
    "sentence": {"realm_idx": 1, "words": 30},
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
SPECIAL_EVENTS = 3          # số sự kiện thăm dò trước khi gặp boss ở động phủ / bí cảnh
SPECIAL_MIN_KILLS = 5       # số yêu thú đã hạ trong vùng để mở nơi đặc biệt

SKILLS = ["Kiếm Khí Tung Hoành", "Ngự Kiếm Trảm", "Linh Quang Chưởng", "Phong Lôi Chỉ", "Thanh Liên Kiếm Ý"]
TRAPS = [
    ("Cơ Quan Chữ Hán", "Một trận pháp khắc chữ Hán chặn lối, cần giải mã để đi qua."),
    ("Rương Cổ Phong Ấn", "Chiếc rương cổ phát ra linh quang, ấn chú trên nắp đòi một đáp án."),
    ("Bia Đá Thượng Cổ", "Tấm bia đá hiện lên văn tự, chỉ ai hiểu mới được qua."),
    ("Linh Trận Thủ Hộ", "Linh trận thủ hộ xoay chuyển, chờ một lời đáp đúng."),
]

# ---------------------------------------------------------------------------
# Vùng đất: mỗi vùng gồm 2 đại cảnh giới, 2 khu săn thường và 1 nơi đặc biệt có boss
# monsters: (mã, tên, emoji). Ảnh tùy chọn: assets/monsters/<mã>.png (hoặc .webp/.jpg)
# items: 6 vật phẩm [3 phổ thông, 2 hiếm, 1 quý]: (tên, emoji)
# ---------------------------------------------------------------------------
REGIONS = [
    {
        "name": "Thanh Vân Địa Giới",
        "zones": [
            ("Thanh Vân Sơn Cước", [("da_lang", "Dã Lang Yêu", "🐺"), ("thanh_xa", "Thanh Xà Tinh", "🐍")]),
            ("Hắc Thủy Đầm", [("hac_quy", "Hắc Thủy Quy", "🐢"), ("doc_thiem", "Độc Thiềm Yêu", "🐸")]),
        ],
        "special": ("Cổ Động Phủ Vô Danh", "động phủ", ("khoi_loi", "Thủ Phủ Khôi Lỗi", "🗿")),
        "items": [("Hắc Thiết", "⛏️"), ("Yêu Lang Bì", "🧵"), ("Thanh Linh Thảo", "🌿"),
                  ("Tinh Thiết", "🔩"), ("Hạ Phẩm Yêu Đan", "🔮"), ("Linh Mộc Tâm", "🪵")],
    },
    {
        "name": "Xích Mộc Cương Vực",
        "zones": [
            ("Xích Diễm Cốc", [("diem_ho", "Xích Diễm Hổ", "🐅"), ("hoa_dieu", "Hỏa Linh Điểu", "🦅")]),
            ("Vạn Mộc Lâm", [("co_moc", "Cổ Mộc Yêu", "🌳"), ("huyet_dang", "Huyết Đằng Ma", "🌿")]),
        ],
        "special": ("Huyết Nguyệt Bí Cảnh", "bí cảnh", ("nguyet_vuong", "Huyết Nguyệt Yêu Vương", "🦇")),
        "items": [("Huyền Thiết", "⛏️"), ("Hỏa Giao Lân", "🐉"), ("Tử Linh Chi", "🍄"),
                  ("Xích Tinh Thạch", "🔶"), ("Trung Phẩm Yêu Đan", "🔮"), ("Kim Đan Tinh Hoa", "✨")],
    },
    {
        "name": "Hàn Lôi Cực Địa",
        "zones": [
            ("Hàn Băng Nguyên", [("tuyet_lang", "Tuyết Nguyên Lang", "🐺"), ("bang_ho", "Băng Phách Linh Hồ", "🦊")]),
            ("Tử Điện Sơn Mạch", [("loi_bao", "Lôi Văn Báo", "🐆"), ("dien_giao", "Tử Điện Giao", "🐉")]),
        ],
        "special": ("Thiên Lôi Cấm Địa", "cấm địa", ("loi_thu", "Thiên Lôi Thần Thú", "⚡")),
        "items": [("Hàn Thiết", "⛏️"), ("Băng Giao Cốt", "🦴"), ("Tuyết Liên Diệp", "🌸"),
                  ("Hàn Ngọc", "💎"), ("Lôi Tinh", "⚡"), ("Thiên Lôi Mộc", "🪵")],
    },
    {
        "name": "Cửu U Vân Hải",
        "zones": [
            ("Cửu U Hoang Mạc", [("sa_hat", "Sa Mạc Yêu Hạt", "🦂"), ("cot_long", "U Minh Cốt Long", "💀")]),
            ("Vân Hải Tiên Đảo", [("van_kinh", "Vân Hải Kình", "🐋"), ("bich_giao", "Bích Ba Giao Long", "🐲")]),
        ],
        "special": ("Thượng Cổ Chiến Trường", "chiến trường", ("chien_tuong", "Chiến Tướng Vong Hồn", "👹")),
        "items": [("U Minh Thiết", "⛏️"), ("Hoang Mạc Sa Tinh", "🏜️"), ("Vân Hải Linh Tảo", "🌊"),
                  ("Cốt Ngọc", "🦴"), ("Giao Long Đan", "🔮"), ("Chiến Hồn Tinh", "👻")],
    },
    {
        "name": "Hỗn Độn Bất Chu",
        "zones": [
            ("Hỗn Độn Hải", [("ma_ngu", "Hỗn Độn Ma Ngư", "🦈"), ("cu_mang", "Tiên Hải Cự Mãng", "🐙")]),
            ("Bất Chu Sơn", [("bach_vien", "Thần Sơn Bạch Viên", "🦍"), ("ky_lan", "Địa Hỏa Kỳ Lân", "🦄")]),
        ],
        "special": ("Tiên Ma Chi Môn", "cổ môn", ("ma_tuong", "Thủ Môn Ma Tướng", "😈")),
        "items": [("Hỗn Độn Thiết", "⛏️"), ("Tiên Hải Lân", "🐟"), ("Bất Chu Linh Chi", "🍄"),
                  ("Thần Sơn Ngọc", "💎"), ("Kỳ Lân Giác", "🦄"), ("Tiên Ma Tinh Phách", "🌑")],
    },
    {
        "name": "Ngọc Hư Tiên Cảnh",
        "zones": [
            ("Ngọc Hư Vân Hải", [("van_hac", "Ngọc Hư Vân Hạc", "🦢"), ("tien_xa", "Tiên Vân Xà", "🐍")]),
            ("Bích Tiêu Tiên Sơn", [("bich_ho", "Bích Tiêu Linh Hổ", "🐯"), ("thanh_loan", "Thanh Loan Tiên Điểu", "🦜")]),
        ],
        "special": ("Thái Cổ Thần Điện", "thần điện", ("than_dien", "Thần Điện Thủ Hộ Giả", "🛡️")),
        "items": [("Ngọc Hư Kim", "⛏️"), ("Tiên Vân Lân", "☁️"), ("Bích Tiêu Tiên Thảo", "🌿"),
                  ("Tiên Linh Ngọc", "💎"), ("Thanh Loan Vũ", "🪶"), ("Thái Cổ Thần Tinh", "🌟")],
    },
    {
        "name": "Cửu Thiên Tinh Hà",
        "zones": [
            ("Tinh Hà Cổ Đạo", [("tinh_thu", "Tinh Hà Cự Thú", "🐘"), ("nguyet_ho", "Nguyệt Quang Linh Hồ", "🦊")]),
            ("Hồng Mông Cổ Địa", [("hong_ma", "Hồng Mông Ma Viên", "🦧"), ("dia_long", "Địa Mạch Long", "🐲")]),
        ],
        "special": ("Hồng Hoang Cấm Khu", "cấm khu", ("hong_hoang", "Hồng Hoang Cự Linh", "🗿")),
        "items": [("Tinh Hà Thiết", "⛏️"), ("Nguyệt Quang Bì", "🧵"), ("Hồng Mông Linh Thảo", "🌱"),
                  ("Tinh Thần Sa", "🌌"), ("Địa Mạch Long Đan", "🔮"), ("Hồng Hoang Cốt", "🦴")],
    },
    {
        "name": "Thiên Đế Cố Cảnh",
        "zones": [
            ("Thiên Đế Phế Tích", [("phe_tich", "Phế Tích Hồn Linh", "👻"), ("kim_quang", "Kim Quang Thần Điểu", "🦚")]),
            ("Vạn Đạo Thiên Lộ", [("dao_thu", "Vạn Đạo Thủ Hộ Thú", "🦁"), ("thien_long", "Thiên Long Ấu Thể", "🐉")]),
        ],
        "special": ("Chí Tôn Thiên Môn", "thiên môn", ("chi_ton", "Chí Tôn Thủ Vệ", "👑")),
        "items": [("Thiên Đế Thiết", "⛏️"), ("Kim Quang Vũ", "🪶"), ("Vạn Đạo Linh Thảo", "🌿"),
                  ("Thiên Lộ Tinh Ngọc", "💎"), ("Thiên Long Giác", "🐲"), ("Chí Tôn Đạo Quả", "🍑")],
    },
]
REGION_COUNT = 8
assert len(REGIONS) == REGION_COUNT

ITEM_RARITIES = ("common", "rare", "precious")
RARITY_LABEL = {"common": "Phổ thông", "rare": "Hiếm", "precious": "Quý"}
ITEM_LAYOUT = ("common", "common", "common", "rare", "rare", "precious")


def build_items():
    """Danh mục vật phẩm: mã -> thông tin. Mã dạng r{vùng}_{chỉ số}."""
    items = {}
    for r, region in enumerate(REGIONS):
        for i, (name, emoji) in enumerate(region["items"]):
            items[f"r{r}_{i}"] = {"code": f"r{r}_{i}", "name": name, "emoji": emoji, "region": r,
                                  "rarity": ITEM_LAYOUT[i]}
    items["pham_dan"] = {"code": "pham_dan", "name": "Tụ Phẩm Đan", "emoji": "💊", "region": None,
                         "rarity": "special"}
    return items


ITEMS = build_items()

# Rơi vật phẩm: (số lần quay phổ thông, số lượng mỗi lần) ...
DROP_NORMAL = {"common_rolls": 2, "common_qty": (1, 2), "rare_chance": 0.12}
DROP_BOSS = {"common_rolls": 4, "common_qty": (1, 3), "rare_rolls": 2, "rare_qty": (1, 2), "precious_chance": 0.40}
DROP_EVENT = {"common_chance": 0.7, "common_qty": (1, 2)}

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

# Mã bí phương (khớp tên ảnh): tên, cấp, vùng nguyên liệu, cảnh giới tối thiểu
RECIPES = [
    {"code": "lk1", "name": "Thanh Phong Kiếm", "tier": "linh_khi", "region": 0, "min_idx": 0},
    {"code": "lk2", "name": "Hộ Tâm Kính", "tier": "linh_khi", "region": 0, "min_idx": 1},
    {"code": "pb1", "name": "Xích Diễm Đao", "tier": "phap_bao", "region": 1, "min_idx": 2},
    {"code": "pb2", "name": "Huyền Quy Thuẫn", "tier": "phap_bao", "region": 1, "min_idx": 3},
    {"code": "lb1", "name": "Hàn Băng Châu", "tier": "linh_bao", "region": 2, "min_idx": 4},
    {"code": "lb2", "name": "Cửu U Phiên", "tier": "linh_bao", "region": 3, "min_idx": 6},
    {"code": "tb1", "name": "Vân Hải Chung", "tier": "tien_bao", "region": 3, "min_idx": 7},
    {"code": "tb2", "name": "Hỗn Độn Ấn", "tier": "tien_bao", "region": 4, "min_idx": 8},
    {"code": "tk1", "name": "Ngọc Hư Tiên Kiếm", "tier": "tien_khi", "region": 5, "min_idx": 10},
    {"code": "tk2", "name": "Tinh Hà Thần Châu", "tier": "tien_khi", "region": 6, "min_idx": 12},
]
RECIPE_BY_CODE = {r["code"]: r for r in RECIPES}

ARTIFACT_ATK_RATIO = 0.7   # cộng thêm so với sức công gốc tại cảnh giới tối thiểu của pháp bảo
ARTIFACT_HP_RATIO = 0.5
UPGRADE_MAX = 9
UPGRADE_STAT_STEP = 0.10
UPGRADE_LS_RATIO = 0.12    # trên giá chế tạo, nhân (1 + 0.4 * cấp hiện tại)
UPGRADE_BASE_MATERIALS = 2

# ---------------------------------------------------------------------------
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
