"""Test cases cho Phiên 6: Vẽ Phù (Talisman System)"""
import sqlite3
import unittest
from unittest import mock

import game_config as cfg
import game_core as core


class TestTalismanSystem(unittest.TestCase):
    """Phiên 6: Vẽ Phù - test các hàm cơ bản"""
    
    def setUp(self):
        """Tạo user DB tạm thời cho testing."""
        self.patcher = mock.patch('game_core.get_user_db')
        self.mock_db = self.patcher.start()
        
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        
        # Tạo schema
        for sql in [
            """CREATE TABLE IF NOT EXISTS word_mastery (
                user_id INTEGER, vocab_id INTEGER, last_status TEXT, PRIMARY KEY (user_id, vocab_id))""",
            """CREATE TABLE IF NOT EXISTS game_profile (
                user_id INTEGER PRIMARY KEY, linh_thach INTEGER DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS game_talismans (
                user_id INTEGER, talisman_code TEXT, qty INTEGER DEFAULT 0, PRIMARY KEY (user_id, talisman_code))""",
            """CREATE TABLE IF NOT EXISTS game_talisman_recipes (
                user_id INTEGER, recipe_code TEXT, PRIMARY KEY (user_id, recipe_code))""",
            """CREATE TABLE IF NOT EXISTS game_counters (
                user_id INTEGER, key TEXT, value INTEGER DEFAULT 0, PRIMARY KEY (user_id, key))""",
        ]:
            self.conn.execute(sql)
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
        
        # Tạo profile người chơi
        self.conn.execute(
            "INSERT INTO game_profile (user_id, linh_thach) VALUES (?, ?)",
            (self.user_id, 5000)
        )
        self.conn.commit()
        
        # Mock realm_info để trả về realm 5 (cảnh giới Xuất Khiếu Kỳ · Hậu Kỳ, idx=5)
        self.realm_patcher = mock.patch('game_core.realm_info')
        self.mock_realm = self.realm_patcher.start()
        self.mock_realm.return_value = {
            "stage": 17,
            "idx": 5,
            "sub": 2,
            "name": "Xuất Khiếu Kỳ · Hậu Kỳ",
            "major_name": "Xuất Khiếu Kỳ",
            "next_need": 1400,
            "progress": 0.5
        }
        
        # Mock get_words_learned_count
        self.words_patcher = mock.patch('game_core.get_words_learned_count')
        self.mock_words = self.words_patcher.start()
        self.mock_words.return_value = 500
    
    def tearDown(self):
        self.conn.close()
        self.patcher.stop()
        self.realm_patcher.stop()
        self.words_patcher.stop()
    
    def test_buy_talisman_recipe_success(self):
        """Test mua công thức phù thành công."""
        ok, msg, ls = core.buy_talisman_recipe(self.user_id, "talisman_1")
        self.assertTrue(ok)
        self.assertIn("thành công", msg)
        self.assertEqual(ls, 5000 - 100)  # 100 là giá talisman_1
    
    def test_buy_talisman_recipe_not_enough_ls(self):
        """Test mua công thức phù không đủ Linh Thạch."""
        # Đặt Linh Thạch quá ít
        self.conn.execute(
            "UPDATE game_profile SET linh_thach = 50 WHERE user_id = ?",
            (self.user_id,)
        )
        self.conn.commit()
        
        ok, msg, ls = core.buy_talisman_recipe(self.user_id, "talisman_1")
        self.assertFalse(ok)
        self.assertIn("Linh Thạch", msg)
        self.assertEqual(ls, 50)
    
    def test_buy_talisman_recipe_already_owned(self):
        """Test mua công thức phù đã sở hữu rồi."""
        # Mua lần 1
        ok, msg, ls = core.buy_talisman_recipe(self.user_id, "talisman_1")
        self.assertTrue(ok)
        
        # Mua lần 2 → thất bại
        ok, msg, ls = core.buy_talisman_recipe(self.user_id, "talisman_1")
        self.assertFalse(ok)
        self.assertIn("đã mua", msg)
    
    def test_get_talisman_recipes_owned(self):
        """Test lấy danh sách công thức phù sở hữu."""
        # Chưa mua gì
        recipes = core.get_talisman_recipes_owned(self.user_id)
        self.assertEqual(len(recipes), 0)
        
        # Mua 2 công thức
        core.buy_talisman_recipe(self.user_id, "talisman_1")
        core.buy_talisman_recipe(self.user_id, "talisman_3")
        
        recipes = core.get_talisman_recipes_owned(self.user_id)
        self.assertEqual(len(recipes), 2)
        codes = [r["code"] for r in recipes]
        self.assertIn("talisman_1", codes)
        self.assertIn("talisman_3", codes)
    
    def test_craft_talisman_success(self):
        """Test xây dựng phù thành công."""
        # Mua công thức trước
        core.buy_talisman_recipe(self.user_id, "talisman_3")
        
        # Xây dựng phù
        result = core.craft_talisman(self.user_id, "talisman_3")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["talisman_code"], "talisman_3")
        self.assertIn("thành công", result["message"])
    
    def test_craft_talisman_realm_too_low(self):
        """Test xây dựng phù khi cảnh giới quá thấp."""
        # Mock realm_info để trả về realm 1 (quá thấp cho talisman_6)
        self.mock_realm.return_value = {
            "stage": 2,
            "idx": 0,
            "sub": 2,
            "name": "Linh Khí Kỳ · Hậu Kỳ",
            "major_name": "Linh Khí Kỳ",
            "next_need": 200,
            "progress": 0.5
        }
        
        # Mua công thức
        core.buy_talisman_recipe(self.user_id, "talisman_6")
        
        # Xây dựng phù → thất bại vì cảnh giới quá thấp
        result = core.craft_talisman(self.user_id, "talisman_6")
        
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "REALM_TOO_LOW")
    
    def test_craft_talisman_no_recipe(self):
        """Test xây dựng phù mà chưa mua công thức."""
        result = core.craft_talisman(self.user_id, "talisman_1")
        
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "RECIPE_NOT_OWNED")
    
    def test_get_talismans_inventory(self):
        """Test lấy kho phù."""
        # Kho trống
        inv = core.get_talismans_inventory(self.user_id)
        self.assertEqual(len(inv), 0)
        
        # Xây dựng 2 phù
        core.buy_talisman_recipe(self.user_id, "talisman_1")
        core.craft_talisman(self.user_id, "talisman_1")
        
        core.buy_talisman_recipe(self.user_id, "talisman_2")
        core.craft_talisman(self.user_id, "talisman_2")
        core.craft_talisman(self.user_id, "talisman_2")  # Xây 2 lần
        
        inv = core.get_talismans_inventory(self.user_id)
        self.assertEqual(len(inv), 2)
        
        # Kiểm tra số lượng
        t1 = next(t for t in inv if t["code"] == "talisman_1")
        t2 = next(t for t in inv if t["code"] == "talisman_2")
        self.assertEqual(t1["qty"], 1)
        self.assertEqual(t2["qty"], 2)
    
    def test_talisman_inventory_qty(self):
        """Test lấy số lượng phù."""
        qty = core.get_talisman_inventory_qty(self.user_id, "talisman_1")
        self.assertEqual(qty, 0)
        
        # Xây dựng phù
        core.buy_talisman_recipe(self.user_id, "talisman_1")
        core.craft_talisman(self.user_id, "talisman_1")
        
        qty = core.get_talisman_inventory_qty(self.user_id, "talisman_1")
        self.assertEqual(qty, 1)
    
    def test_consume_talisman(self):
        """Test tiêu hao phù."""
        # Xây dựng 3 phù
        core.buy_talisman_recipe(self.user_id, "talisman_1")
        core.craft_talisman(self.user_id, "talisman_1")
        core.craft_talisman(self.user_id, "talisman_1")
        core.craft_talisman(self.user_id, "talisman_1")
        
        # Tiêu hao 1
        ok = core.consume_talisman(self.user_id, "talisman_1", 1)
        self.assertTrue(ok)
        qty = core.get_talisman_inventory_qty(self.user_id, "talisman_1")
        self.assertEqual(qty, 2)
        
        # Tiêu hao 2 lần nữa
        ok = core.consume_talisman(self.user_id, "talisman_1", 2)
        self.assertTrue(ok)
        qty = core.get_talisman_inventory_qty(self.user_id, "talisman_1")
        self.assertEqual(qty, 0)
        
        # Tiêu hao khi không có → thất bại
        ok = core.consume_talisman(self.user_id, "talisman_1", 1)
        self.assertFalse(ok)


class TestTalismanUnlock(unittest.TestCase):
    """Test điều kiện mở khóa phù"""
    
    def setUp(self):
        self.patcher = mock.patch('game_core.get_user_db')
        self.mock_db = self.patcher.start()
        
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        
        for sql in [
            """CREATE TABLE IF NOT EXISTS word_mastery (
                user_id INTEGER, vocab_id INTEGER, last_status TEXT, PRIMARY KEY (user_id, vocab_id))""",
            """CREATE TABLE IF NOT EXISTS game_profile (
                user_id INTEGER PRIMARY KEY, linh_thach INTEGER DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS game_talisman_recipes (
                user_id INTEGER, recipe_code TEXT, PRIMARY KEY (user_id, recipe_code))""",
        ]:
            self.conn.execute(sql)
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
    
    def tearDown(self):
        self.conn.close()
        self.patcher.stop()
    
    def test_talisman_unlock_condition_met(self):
        """Test mở khóa phù khi đã học >= 4 từ."""
        # Đã học >= 4 từ
        for i in range(4):
            self.conn.execute(
                "INSERT INTO word_mastery (user_id, vocab_id, last_status) VALUES (?, ?, 'MASTERED')",
                (self.user_id, i)
            )
        self.conn.commit()
        
        words_learned = core.get_words_learned_count(self.user_id)
        self.assertGreaterEqual(words_learned, 4)
    
    def test_talisman_unlock_condition_not_met(self):
        """Test mở khóa phù khi chưa học đủ từ."""
        # Chỉ học 2 từ
        for i in range(2):
            self.conn.execute(
                "INSERT INTO word_mastery (user_id, vocab_id, last_status) VALUES (?, ?, 'MASTERED')",
                (self.user_id, i)
            )
        self.conn.commit()
        
        words_learned = core.get_words_learned_count(self.user_id)
        self.assertLess(words_learned, 4)


if __name__ == '__main__':
    unittest.main()
