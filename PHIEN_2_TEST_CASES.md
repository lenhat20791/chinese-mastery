# 🧪 PHIÊN 2 - TEST SCENARIOS

## **Test Case 1: Streamlit Startup**
```
Command: streamlit run app.py
Expected:
  ✓ App loads without errors
  ✓ Home page displays current honor (if equipped)
  ✓ No red errors in console
```

## **Test Case 2: Navigate to Honors Tab**
```
Steps:
  1. Click "🏅 Huy Hiệu" in navigation
  2. Scroll to "Danh Hào" section
Expected:
  ✓ Shows "Danh Hào" section (not hidden)
  ✓ Selectbox displays available honors for current realm
  ✓ Shows effects: "+X% công, +Y% HP"
```

## **Test Case 3: Equip Honor**
```
Steps:
  1. In Danh Hào section, select different honor from dropdown
  2. Reload page (F5)
  3. Go to Home page
Expected:
  ✓ Selected honor is saved to DB
  ✓ Home page shows "🏅 [Honor Name]" after reload
  ✓ Stats update with new honor bonus
```

## **Test Case 4: Progression - User at Realm 0**
```
Setup: New user or user at realm_idx 0
Expected:
  ✓ Only "Sơ nhập tiên lộ" available
  ✓ Can equip "Sơ nhập tiên lộ" only
  ✓ Effects: +3% công
```

## **Test Case 5: Progression - User at Realm 2**
```
Setup: User at realm_idx >= 2 (Kim Đan Kỳ or higher)
Expected:
  ✓ Both "Sơ nhập tiên lộ" and "Chân nhân" available
  ✓ Can equip "Chân nhân" → +5% công, +5% HP
  ✓ Selectbox shows both honors
```

## **Test Case 6: Max Realm - User at Realm 15**
```
Setup: User at realm_idx 15 (Tiên Đế)
Expected:
  ✓ All 10 honors available in selectbox
  ✓ Can equip "Vĩnh hằng Tiên Đế" → +25% công, +25% HP
  ✓ Stats display updated bonus
```

## **Test Case 7: Unequip Honor**
```
Steps:
  1. In selectbox, select "— không đeo —"
  2. Reload page
Expected:
  ✓ Honor unequipped from DB
  ✓ Home page shows no honor badge
  ✓ Stats bonus removed
```

## **Test Case 8: Old User with Old Badges**
```
Setup: User with old badge in equipped_title
Expected:
  ✓ Danh Hào tab shows old badge unavailable
  ✓ User can select new honor from available list
  ✓ Old badge code disappears after switching to new honor
  ✓ No errors or crashes
```

## **Test Case 9: Combat Bonus - Verify Effects in Hunt**
```
Steps:
  1. Equip "Chân nhân" (+5% ATK, +5% HP)
  2. Enter hunt (🗺️ Săn Yêu Thú)
  3. Check stats display
Expected:
  ✓ ATK stat higher than without honor
  ✓ HP stat higher than without honor
  ✓ Effects persist through combat
```

## **Test Case 10: Badges vs Honors - Both Display**
```
Steps:
  1. Go to 🏅 Huy Hiệu tab
  2. Look for "Huy Hiệu Thành Tích" section
  3. Look for "Huy Hiệu Ẩn" section
Expected:
  ✓ Danh Hào section at top (new)
  ✓ Huy Hiệu Thành Tích section still there (old)
  ✓ Huy Hiệu Ẩn section still there (old)
  ✓ No overlap or conflicts
```

## **Regression Tests (Old Functionality)**
```
✓ Match game (🃏 Lật Bài) shows 2-color buttons
✓ Fortune game (🔮 Quẻ Bói) works normally
✓ Hunt (🗺️ Săn Yêu Thú) displays stats correctly
✓ Market (🏪 Phường Thị) works normally
✓ Artifacts display correctly
```

---

## **Quick Terminal Check**
```bash
# Unit tests
python -c "
import game_config as cfg, game_core as core
assert len(cfg.HONOR_TITLES) == 10
assert len(core.available_honors(0)) == 1
assert len(core.available_honors(15)) == 10
print('✓ All unit tests passed')
"
```

---

## **Expected Behaviors**

### ✅ Correct
- User at realm_idx 0 can only equip first honor
- User at realm_idx 15 can equip any of 10 honors
- Honor effects add to existing bonuses
- Old badges not deleted, new honors coexist
- Selectbox in Danh Hào tab shows "— không đeo —" + available honors

### ❌ Bug Indicators
- Danh Hào section not visible (should show if any honors available)
- Selectbox shows unavailable honors (should only show for realm_idx)
- Effects not applied to stats
- Crashes when loading with old badge code
- "Không đeo —" option appears as duplicate honor
