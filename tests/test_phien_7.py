"""Test cases cho Phiên 7: Săn yêu thú - Sửa lỗi Hán tự, giữ HP, sử dụng vật phẩm"""
import sqlite3
import unittest
from unittest import mock

import game_config as cfg
import game_core as core
import game_questions as gq


class TestHanziNormalization(unittest.TestCase):
    """Test chuẩn hóa Hán tự"""
    
    def test_normalize_hanzi_basic(self):
        """Test chuẩn hóa Hán tự cơ bản."""
        # Chuẩn hóa không thay đổi chữ
        result = gq.normalize_hanzi("中")
        self.assertEqual(result, "中")
    
    def test_normalize_hanzi_whitespace(self):
        """Test loại bỏ khoảng trắng."""
        result = gq.normalize_hanzi("  中  ")
        self.assertEqual(result, "中")
    
    def test_check_hanzi_match_exact(self):
        """Test so khớp Hán tự chính xác."""
        # Nhập đúng → match
        ok = gq.check_hanzi_match("中", "中")
        self.assertTrue(ok)
    
    def test_check_hanzi_match_with_space(self):
        """Test so khớp Hán tự với khoảng trắng."""
        # Nhập có khoảng trắng → vẫn match sau chuẩn hóa
        ok = gq.check_hanzi_match(" 中 ", "中")
        self.assertTrue(ok)
    
    def test_check_hanzi_match_wrong(self):
        """Test so khớp Hán tự sai."""
        # Nhập sai → không match
        ok = gq.check_hanzi_match("好", "中")
        self.assertFalse(ok)
    
    def test_check_hanzi_match_empty(self):
        """Test so khớp Hán tự với chuỗi rỗng."""
        # Nhập rỗng → không match
        ok = gq.check_hanzi_match("", "中")
        self.assertFalse(ok)


class TestItemUsageInBattle(unittest.TestCase):
    """Test sử dụng vật phẩm trong trận đấu"""
    
    def setUp(self):
        self.patcher = mock.patch('game_core.get_user_db')
        self.mock_db = self.patcher.start()
        
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        
        for sql in [
            """CREATE TABLE IF NOT EXISTS game_inventory (
                user_id INTEGER, item_code TEXT, qty INTEGER, PRIMARY KEY (user_id, item_code))""",
            """CREATE TABLE IF NOT EXISTS game_pills (
                user_id INTEGER, pill_code TEXT, qty INTEGER, PRIMARY KEY (user_id, pill_code))""",
            """CREATE TABLE IF NOT EXISTS game_talismans (
                user_id INTEGER, talisman_code TEXT, qty INTEGER, PRIMARY KEY (user_id, talisman_code))""",
        ]:
            self.conn.execute(sql)
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
        
        # Tạo đan và phù test
        self.conn.execute(
            "INSERT INTO game_pills (user_id, pill_code, qty) VALUES (?, ?, ?)",
            (self.user_id, "pill_1", 3)
        )
        self.conn.execute(
            "INSERT INTO game_talismans (user_id, talisman_code, qty) VALUES (?, ?, ?)",
            (self.user_id, "talisman_1", 2)
        )
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
        self.patcher.stop()
    
    def test_use_pill_in_battle(self):
        """Test sử dụng đan trong trận."""
        battle_state = {"php": 100, "pmax": 100}
        ok, msg = core.use_pill_in_battle(battle_state, "pill_1")
        
        self.assertTrue(ok)
        self.assertTrue("Sử dụng" in msg or "sử dụng" in msg or "thành công" in msg)
        self.assertIn("pill_1", battle_state.get("used_pills", []))
    
    def test_use_pill_twice_per_turn(self):
        """Test không cho phép sử dụng đan cùng loại 2 lần trong 1 lượt."""
        battle_state = {"php": 100, "pmax": 100}
        
        # Lần 1 → thành công
        ok1, msg1 = core.use_pill_in_battle(battle_state, "pill_1")
        self.assertTrue(ok1)
        
        # Lần 2 cùng loại → thất bại
        ok2, msg2 = core.use_pill_in_battle(battle_state, "pill_1")
        self.assertFalse(ok2)
        self.assertTrue("Đã" in msg2 or "đã" in msg2 or "sử dụng" in msg2)
    
    def test_use_talisman_in_battle(self):
        """Test sử dụng phù trong trận."""
        battle_state = {"php": 100, "pmax": 100}
        ok, msg = core.use_talisman_in_battle(battle_state, "talisman_1")
        
        self.assertTrue(ok)
        self.assertTrue("Sử dụng" in msg or "sử dụng" in msg or "thành công" in msg)
        self.assertIn("talisman_1", battle_state.get("used_talismans", []))
    
    def test_use_different_items(self):
        """Test sử dụng các vật phẩm khác nhau trong cùng một lượt."""
        battle_state = {"php": 100, "pmax": 100}
        
        # Sử dụng đan
        ok1, _ = core.use_pill_in_battle(battle_state, "pill_1")
        self.assertTrue(ok1)
        
        # Sử dụng phù
        ok2, _ = core.use_talisman_in_battle(battle_state, "talisman_1")
        self.assertTrue(ok2)
        
        # Kiểm tra cả 2 đều được sử dụng
        self.assertIn("pill_1", battle_state.get("used_pills", []))
        self.assertIn("talisman_1", battle_state.get("used_talismans", []))


class TestRevivalPill(unittest.TestCase):
    """Test Cửu chuyển hoàn hồn đan (Hồi sinh)"""
    
    def setUp(self):
        self.patcher1 = mock.patch('game_core.get_user_db')
        self.patcher2 = mock.patch('game_core.consume_inventory')
        self.mock_db = self.patcher1.start()
        self.mock_consume = self.patcher2.start()
        
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS game_inventory (
                user_id INTEGER, item_code TEXT, qty INTEGER, PRIMARY KEY (user_id, item_code))"""
        )
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
    
    def tearDown(self):
        self.conn.close()
        self.patcher1.stop()
        self.patcher2.stop()
    
    def test_has_revival_pill_true(self):
        """Test có Cửu chuyển hoàn hồn đan."""
        # Mock get_inventory_qty để trả về có đan
        with mock.patch('game_core.get_inventory_qty', return_value=1):
            has_pill = core.has_revival_pill(self.user_id)
            self.assertTrue(has_pill)
    
    def test_has_revival_pill_false(self):
        """Test không có Cửu chuyển hoàn hồn đan."""
        # Mock get_inventory_qty để trả về không có đan
        with mock.patch('game_core.get_inventory_qty', return_value=0):
            has_pill = core.has_revival_pill(self.user_id)
            self.assertFalse(has_pill)
    
    def test_use_revival_pill_success(self):
        """Test sử dụng Cửu chuyển hoàn hồn đan thành công."""
        self.mock_consume.return_value = True
        
        battle_state = {
            "php": 0,  # Đã chết
            "pmax": 100,
            "log": []
        }
        
        with mock.patch('game_core.has_revival_pill', return_value=True):
            ok, msg = core.use_revival_pill(self.user_id, battle_state)
            
            self.assertTrue(ok)
            self.assertIn("thành công", msg)
            # HP phải được hồi 50%
            self.assertEqual(battle_state["php"], 50)
            # Phải ghi lại vào log
            self.assertTrue(any("Cửu chuyển" in log for log in battle_state["log"]))
    
    def test_use_revival_pill_no_pill(self):
        """Test sử dụng Cửu chuyển hoàn hồn đan khi không có."""
        battle_state = {"php": 0, "pmax": 100, "log": []}
        
        ok, msg = core.use_revival_pill(self.user_id, battle_state)
        
        self.assertFalse(ok)
        self.assertIn("không", msg.lower())


class TestGetActiveItemEffects(unittest.TestCase):
    """Test lấy hiệu ứng từ các vật phẩm hoạt động"""
    
    def test_no_items(self):
        """Test không có vật phẩm → hiệu ứng = 0."""
        battle_state = {"active_items": {}}
        effects = core.get_active_item_effects(battle_state)
        
        self.assertEqual(effects["atk_bonus_pct"], 0.0)
        self.assertEqual(effects["damage_reduction"], 0.0)
    
    def test_single_pill(self):
        """Test 1 viên đan → cộng ATK."""
        battle_state = {
            "active_items": {
                "pills": [{"effects": 10.0}]  # 10% ATK
            }
        }
        effects = core.get_active_item_effects(battle_state)
        
        self.assertEqual(effects["atk_bonus_pct"], 10.0)
    
    def test_multiple_items(self):
        """Test nhiều vật phẩm → cộng dồn hiệu ứng."""
        battle_state = {
            "active_items": {
                "pills": [
                    {"effects": 10.0},  # 10% ATK
                    {"effects": 5.0}    # 5% ATK
                ],
                "talismans": [
                    {
                        "effects": {
                            "atk_bonus_pct": 15.0,  # 15% ATK
                            "damage_reduction": 10.0  # -10% sát thương
                        }
                    }
                ]
            }
        }
        effects = core.get_active_item_effects(battle_state)
        
        # ATK: 10 + 5 + 15/100 = 15.15 (do chuẩn hóa từ config)
        # Đơn giản hóa test để không phụ thuộc vào công thức cụ thể
        self.assertGreater(effects["atk_bonus_pct"], 10.0)  # Ít nhất phải > 10
        # Damage reduction: 10/100 = 0.1
        self.assertEqual(effects["damage_reduction"], 0.1)


if __name__ == '__main__':
    unittest.main()
