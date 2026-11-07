# Phiên 5-6: Luyện Đan & Vẽ Phù - Kiến Trúc

```
┌─────────────────────────────────────────────────────────────────┐
│                      ĐỘNG PHỦ (Cultivation Tab)                 │
│                                                                   │
│  Navigation Radio:                                               │
│  🏯 Động Phủ | 🔮 Quẻ Bói | 🃏 Lật Bài | 🗺️ Săn Yêu Thú      │
│  ⚗️ Luyện Đan | 🪬 Vẽ Phù | 🏪 Phường Thị | 📜 Công Pháp Các    │
│  🏅 Huy Hiệu                                                     │
│                                                                   │
│  [User selects ⚗️ Luyện Đan or 🪬 Vẽ Phù]                       │
└─────────────────────────────────────────────────────────────────┘
```

## ⚗️ Luyện Đan (Alchemy) - Flow Diagram

```
START
  ↓
[Check Unlock] → Is Realm ≥ 1? 
  ↓ (Yes)
┌──────────────────────────────────────────────┐
│        ⚗️ LUYỆN ĐAN                           │
├──────────────────────────────────────────────┤
│                                               │
│  📜 Công Thức Tab                            │
│  ├─ Show 5 Pill Recipes                      │
│  ├─ Display: Name, Min Realm, Bonus, Price  │
│  └─ [Mua] Button → craft_pill_recipe()       │
│     → Deduct Linh Thạch, Add to owned        │
│                                               │
│  ⚗️ Luyện Viên Tab                           │
│  ├─ Select Recipe Dropdown                   │
│  ├─ Display Hanzi (from word pool)           │
│  ├─ [Text Input] for Hanzi typing            │
│  ├─ [Speaker Icon] for audio                 │
│  └─ Logic:                                    │
│     - gq.check_hanzi_match(input, correct)   │
│     - Track hits_correct / correct_hits_need │
│     - Show Progress Bar                      │
│     - On Success: craft_pill() → Add to inv  │
│                                               │
│  🧪 Kho Đan Tab                              │
│  ├─ Load get_pills_inventory()               │
│  ├─ Grid Layout (5 cols)                     │
│  └─ Display: Emoji, Name, Qty Badge          │
│                                               │
│  Asset: lo_dan.png (Right Column)            │
│                                               │
└──────────────────────────────────────────────┘
```

## 🪬 Vẽ Phù (Talisman) - Flow Diagram

```
START
  ↓
[Check Unlock] → Is Realm ≥ 1?
  ↓ (Yes)
┌──────────────────────────────────────────────┐
│        🪬 VẼ PHÙ                             │
├──────────────────────────────────────────────┤
│                                               │
│  📜 Công Thức Tab                            │
│  ├─ Show 6 Talisman Recipes                  │
│  ├─ Display: Name, Min Realm, Effects,Price  │
│  └─ [Mua] Button → buy_talisman_recipe()     │
│     → Deduct Linh Thạch, Add to owned        │
│                                               │
│  🪬 Vẽ Phù Tab                               │
│  ├─ Select Recipe Dropdown                   │
│  ├─ Display Hanzi (from word pool)           │
│  ├─ [Text Input] for Hanzi typing            │
│  ├─ [Speaker Icon] for audio                 │
│  └─ Logic:                                    │
│     - gq.check_hanzi_match(input, correct)   │
│     - Track hits_correct / correct_hits_need │
│     - Show Progress Bar                      │
│     - On Success: craft_talisman() → Add inv │
│                                               │
│  🧿 Kho Phù Tab                              │
│  ├─ Load get_talismans_inventory()           │
│  ├─ Grid Layout (5 cols)                     │
│  └─ Display: Emoji, Name, Qty Badge          │
│                                               │
│  Asset: phu_luc.png (Right Column)           │
│                                               │
└──────────────────────────────────────────────┘
```

## 🔄 Data Flow

```
game_config.py
  ├─ PILL_RECIPES (5 recipes)
  │  └─ code, name, min_idx, correct_hits_needed, description, emoji, ...
  ├─ PILL_RECIPE_PRICES (mapping)
  ├─ TALISMAN_RECIPES (6 recipes)
  │  └─ code, name, min_idx, correct_hits_needed, description, effects
  └─ TALISMAN_RECIPE_PRICES (mapping)

game_core.py
  ├─ buy_pill_recipe(code, user_id, linh_thach) → (ok, msg, ls_after)
  ├─ craft_pill(code, user_id, idx) → (ok, msg, quality)
  ├─ get_pills_inventory(user_id) → [(pill, qty), ...]
  ├─ buy_talisman_recipe(user_id, code) → (ok, msg, ls_after)
  ├─ craft_talisman(user_id, code) → (ok, msg)
  └─ get_talismans_inventory(user_id) → [(talisman, qty), ...]

game_questions.py
  ├─ check_hanzi_match(input, correct) → bool
  └─ load_pool(learned_day) → [words]

game_minigames.py
  ├─ render_alchemy(ctx)
  │  └─ Tabs: Công Thức | Luyện Viên | Kho Đan
  └─ render_talisman(ctx)
     └─ Tabs: Công Thức | Vẽ Phù | Kho Phù

cultivation_tab.py
  ├─ NAV: {'alchemy': '⚗️ Luyện Đan', 'talisman': '🪬 Vẽ Phù', ...}
  ├─ UNLOCK_KEY: {'alchemy': 'hunt', 'talisman': 'hunt'}
  └─ _body(): router cho page == 'alchemy'/'talisman'
```

## 📊 Recipe Progression

```
Min Realm 0  → Pill 1  (Hạ Phẩm)         10 hits
              ↓
Min Realm 3  → Pill 2  (Trung Phẩm)      15 hits
              ↓
Min Realm 6  → Pill 3  (Thượng Phẩm)     20 hits
              ↓
Min Realm 10 → Pill 4  (Tối Thượng)      25 hits
              ↓
Min Realm 15 → Pill 5  (Tôn Thần)        30 hits

---

Min Realm 1  → Talisman 1 (Bảo Hộ)       10 hits
              ↓
Min Realm 3  → Talisman 2 (Tăng Công)    15 hits
              ↓
Min Realm 5  → Talisman 3 (Hồi Phục)     20 hits
              ↓
Min Realm 8  → Talisman 4 (Phản Công)    25 hits
              ↓
Min Realm 11 → Talisman 5 (Trúc Chi)     30 hits
              ↓
Min Realm 14 → Talisman 6 (Trời Địa)     35 hits
```

## 🎮 Gameplay Loop (User Perspective)

### First Time Playing Alchemy:
1. Unlock check: "I've reached Realm 1+" ✓
2. Click "⚗️ Luyện Đan" button
3. Tab "📜 Công Thức":
   - See "Hạ Phẩm Yêu Đan" - costs 50 LS
   - Click [Mua] → "✅ Mua thành công" toast
4. Tab "⚗️ Luyện Viên":
   - Select "Hạ Phẩm Yêu Đan"
   - See Hanzi: 靈 (lăng)
   - Hear pronunciation 🔊
   - Type "靈" or "ling" → "✅ Đúng!"
   - Progress bar: 1/10 → ... → 10/10
   - "🎉 Luyện thành công!" → Auto-redirect to Tab 3
5. Tab "🧪 Kho Đan":
   - See new pill in grid: 🧪 Hạ Phẩm (×1)

### Repeat for higher tier pills as Realm increases

## ✨ Visual Styling

### Luyện Đan Tab:
- Card borders: 2px dashed #c9a24b (gold)
- Background: rgba(27,20,36,0.7) (dark)
- Counter badge: background #d4a574, color #000
- Image size: ~60px pills in grid

### Vẽ Phù Tab:
- Card borders: 2px solid #a574d4 (purple)
- Background: rgba(27,20,36,0.7) (dark)
- Counter badge: background #a574d4, color #fff
- Image size: ~60px talismans in grid

### Both:
- Title: ### (H3)
- Sub-title: caption (Đoán đúng nghĩa...)
- Hanzi display: font-size 64px, center aligned
- Pinyin: font-size 14px, color #999
- Progress bar: st.progress() with text

---

## 🔗 Integration Points

1. **Database:** (unchanged - already exists from Phiên 5-6 implementation)
   - `game_pills`: user_id, pill_code, qty
   - `game_pill_recipes`: user_id, recipe_code
   - `game_talismans`: user_id, talisman_code, qty
   - `game_talisman_recipes`: user_id, recipe_code

2. **Session State:**
   - `pill_hits`: int (progress counter during crafting)
   - `talisman_hits`: int (progress counter during crafting)

3. **Game Core Functions:**
   - Used in battle: pill bonus ATK, talisman effects
   - (No changes needed - already integrated)

---

## ✅ Testing Checklist

- [x] Both minigames have correct ims (lo_dan.png, phu_luc.png)
- [x] All recipes have correct fields (min_idx, hits_needed, description, emoji)
- [x] Buy flow: deduct Linh Thạch, add to owned, show toast
- [x] Craft flow: gõ Hán tự, check match, update progress, create item
- [x] Inventory: display in grid, show quantities
- [x] Unlock: both require Realm ≥ 1 (same as Hunt)
- [x] Navigation: tabs appear in order
- [x] Images: correct asset paths (not from Công Pháp Các)

---

## 📝 Files Changed

**game_minigames.py**: +428 lines (render_alchemy, render_talisman)  
**cultivation_tab.py**: +~10 lines (NAV, UNLOCK_KEY, routing)  
**game_config.py**: +4 fields per recipe (min_idx, hits, description, emoji)  
**test_phien_5_6.py**: +70 lines (new test file)  
**PHIEN_5_6_SUMMARY.md**: documentation  

**Total commits**: 3 (implementation, fixes, documentation)
