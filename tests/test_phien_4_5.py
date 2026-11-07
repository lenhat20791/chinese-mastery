"""Test cases cho Phiên 4 & 5: Alchemy System và Mini-game Luyện Đan"""
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import game_config as cfg
import game_core as core


class TestAlchemy(unittest.TestCase):
    """Phiên 4: Luyện Đan - test các hàm cơ bản"""
    
    def setUp(self):
        """Tạo user DB tạm thời cho testing."""
        # Patch trước khi tạo connection - patch tại game_core module
        self.patcher = mock.patch('game_core.get_user_db')
        self.mock_db = self.patcher.start()
        
        # Tạo DB test riêng cho từng test
        import sqlite3
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        
        # Tạo schema
        for sql in [
            """CREATE TABLE IF NOT EXISTS word_mastery (
                user_id INTEGER, vocab_id INTEGER, last_status TEXT, PRIMARY KEY (user_id, vocab_id))""",
            """CREATE TABLE IF NOT EXISTS game_inventory (
                user_id INTEGER, item_code TEXT, qty INTEGER, PRIMARY KEY (user_id, item_code))""",
            """CREATE TABLE IF NOT EXISTS game_pills (
                user_id INTEGER, pill_code TEXT, qty INTEGER, PRIMARY KEY (user_id, pill_code))""",
            """CREATE TABLE IF NOT EXISTS game_pill_recipes (
                user_id INTEGER, recipe_code TEXT, PRIMARY KEY (user_id, recipe_code))""",
        ]:
            self.conn.execute(sql)
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
    
    def tearDown(self):
        self.conn.close()
        self.patcher.stop()
    
    def test_inventory_basic(self):
        """Test thêm/lấy/tiêu hao vật phẩm."""
        # Lấy kho trống
        qty = core.get_inventory_qty(self.user_id, "r0_0")
        self.assertEqual(qty, 0)
        
        # Thêm vật phẩm
        core.add_inventory(self.user_id, "r0_0", 5)
        qty = core.get_inventory_qty(self.user_id, "r0_0")
        self.assertEqual(qty, 5)
        
        # Tiêu hao
        ok = core.consume_inventory(self.user_id, "r0_0", 2)
        self.assertTrue(ok)
        qty = core.get_inventory_qty(self.user_id, "r0_0")
        self.assertEqual(qty, 3)
        
        # Tiêu hao quá nhiều
        ok = core.consume_inventory(self.user_id, "r0_0", 10)
        self.assertFalse(ok)
    
    def test_pill_buy_recipe(self):
        """Test mua công thức luyện đan."""
        # Không đủ tiền
        ok, msg, ls = core.buy_pill_recipe("pill_1", self.user_id, 10)
        self.assertFalse(ok)
        self.assertIn("Thiếu", msg)
        
        # Mua thành công
        ok, msg, ls = core.buy_pill_recipe("pill_1", self.user_id, 100)
        self.assertTrue(ok)
        self.assertEqual(ls, 50)
        
        # Mua lại → lỗi đã mua
        ok, msg, ls = core.buy_pill_recipe("pill_1", self.user_id, 50)
        self.assertFalse(ok)
        self.assertIn("đã mua", msg.lower())
    
    def test_pill_owned(self):
        """Test lấy danh sách công thức đã mua."""
        # Ban đầu không có
        recipes = core.get_pill_recipes_owned(self.user_id)
        self.assertEqual(len(recipes), 0)
        
        # Mua 2 công thức
        core.buy_pill_recipe("pill_1", self.user_id, 5000)
        core.buy_pill_recipe("pill_2", self.user_id, 5000)
        
        recipes = core.get_pill_recipes_owned(self.user_id)
        self.assertEqual(len(recipes), 2)
        codes = {r["code"] for r in recipes}
        self.assertEqual(codes, {"pill_1", "pill_2"})
    
    def test_can_craft_pill(self):
        """Test kiểm tra điều kiện luyện đan."""
        # Chưa mua công thức
        ok, reason = core.can_craft_pill("pill_1", self.user_id, 0)
        self.assertFalse(ok)
        self.assertIn("chưa mua", reason.lower())
        
        # Mua công thức nhưng không đủ nguyên liệu
        self.conn.execute("INSERT INTO game_pill_recipes VALUES (?, ?)", (self.user_id, "pill_1"))
        self.conn.commit()
        ok, reason = core.can_craft_pill("pill_1", self.user_id, 0)
        self.assertFalse(ok)
        self.assertIn("thiếu", reason.lower())
        
        # Chuẩn bị nguyên liệu đủ
        core.add_inventory(self.user_id, "r0_0", 2)
        core.add_inventory(self.user_id, "r0_1", 1)
        ok, reason = core.can_craft_pill("pill_1", self.user_id, 0)
        self.assertTrue(ok)
    
    def test_craft_pill_success(self):
        """Test luyện đan thành công."""
        # Chuẩn bị
        self.conn.execute("INSERT INTO game_pill_recipes VALUES (?, ?)", (self.user_id, "pill_1"))
        self.conn.commit()
        core.add_inventory(self.user_id, "r0_0", 2)
        core.add_inventory(self.user_id, "r0_1", 1)
        
        # Luyện đan (thành công)
        rng = random.Random(42)
        success, msg = core.craft_pill("pill_1", self.user_id, 0, rng)
        self.assertTrue(success)
        self.assertIn("✅", msg)
        
        # Kiểm tra đan được thêm vào kho
        pills = core.get_pills_inventory(self.user_id)
        self.assertEqual(len(pills), 1)
        self.assertEqual(pills[0]["code"], "pill_1")
        self.assertEqual(pills[0]["qty"], 1)
        
        # Kiểm tra nguyên liệu bị tiêu hao
        qty_0 = core.get_inventory_qty(self.user_id, "r0_0")
        qty_1 = core.get_inventory_qty(self.user_id, "r0_1")
        self.assertEqual(qty_0, 0)
        self.assertEqual(qty_1, 0)
    
    def test_craft_pill_failure(self):
        """Test luyện đan thất bại nhưng vẫn tiêu hao nguyên liệu."""
        # Chuẩn bị
        self.conn.execute("INSERT INTO game_pill_recipes VALUES (?, ?)", (self.user_id, "pill_5"))
        self.conn.commit()
        core.add_inventory(self.user_id, "r3_2", 4)
        core.add_inventory(self.user_id, "r3_4", 3)
        core.add_inventory(self.user_id, "r3_5", 1)
        
        # Luyện đan pill_5 (40% thành công) với RNG trả 0.5 → thất bại
        class MockRng:
            def random(self):
                return 0.5  # > 0.40 → thất bại
        
        rng = MockRng()
        success, msg = core.craft_pill("pill_5", self.user_id, 15, rng)
        self.assertFalse(success)
        self.assertIn("❌", msg)
        
        # Nguyên liệu vẫn bị tiêu hao
        qty_2 = core.get_inventory_qty(self.user_id, "r3_2")
        qty_4 = core.get_inventory_qty(self.user_id, "r3_4")
        qty_5 = core.get_inventory_qty(self.user_id, "r3_5")
        self.assertEqual(qty_2, 0)
        self.assertEqual(qty_4, 0)
        self.assertEqual(qty_5, 0)


class TestAlchemistGame(unittest.TestCase):
    """Phiên 5: Mini-game Luyện Đan"""
    
    def setUp(self):
        """Tạo user DB tạm thời cho testing."""
        # Patch tại game_core module
        self.patcher = mock.patch('game_core.get_user_db')
        self.mock_db = self.patcher.start()
        
        import sqlite3
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        
        # Tạo schema
        for sql in [
            """CREATE TABLE IF NOT EXISTS word_mastery (
                user_id INTEGER, vocab_id INTEGER, last_status TEXT, PRIMARY KEY (user_id, vocab_id))""",
            """CREATE TABLE IF NOT EXISTS game_inventory (
                user_id INTEGER, item_code TEXT, qty INTEGER, PRIMARY KEY (user_id, item_code))""",
            """CREATE TABLE IF NOT EXISTS game_pill_recipes (
                user_id INTEGER, recipe_code TEXT, PRIMARY KEY (user_id, recipe_code))""",
        ]:
            self.conn.execute(sql)
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
    
    def tearDown(self):
        self.conn.close()
        self.patcher.stop()
    
    def test_build_pool_learned_words(self):
        """Test tạo pool từ từ đã học."""
        # Thêm 5 từ đã học
        for i in range(5):
            self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", 
                            (self.user_id, 100 + i, "MASTERED"))
        self.conn.commit()
        
        # Tạo pool cho pill_1 (cần 3 từ)
        pool = core.build_alchemist_pool(self.user_id, "pill_1")
        self.assertEqual(len(pool), 3)
        self.assertTrue(all(100 <= w <= 104 for w in pool))
    
    def test_build_pool_mixed_words(self):
        """Test tạo pool với từ đã học + chưa học."""
        # 2 từ đã học
        self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", (self.user_id, 100, "MASTERED"))
        self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", (self.user_id, 101, "REVIEW"))
        
        # 3 từ chưa học
        for i in range(3):
            self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", 
                            (self.user_id, 200 + i, "NEW"))
        self.conn.commit()
        
        # Tạo pool cho pill_3 (cần 5 từ)
        pool = core.build_alchemist_pool(self.user_id, "pill_3")
        self.assertEqual(len(pool), 5)
        
        # Pool phải chứa tất cả 2 từ đã học
        learned_in_pool = [w for w in pool if w < 200]
        self.assertEqual(len(learned_in_pool), 2)
    
    def test_words_learned_count(self):
        """Test đếm số từ đã học."""
        # Ban đầu 0 từ
        count = core.get_words_learned_count(self.user_id)
        self.assertEqual(count, 0)
        
        # Thêm 3 từ MASTERED
        for i in range(3):
            self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", 
                            (self.user_id, 100 + i, "MASTERED"))
        
        # Thêm 2 từ REVIEW
        for i in range(2):
            self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", 
                            (self.user_id, 110 + i, "REVIEW"))
        
        # Thêm 2 từ NEW (không tính)
        for i in range(2):
            self.conn.execute("INSERT INTO word_mastery VALUES (?, ?, ?)", 
                            (self.user_id, 120 + i, "NEW"))
        self.conn.commit()
        
        count = core.get_words_learned_count(self.user_id)
        self.assertEqual(count, 5)


if __name__ == "__main__":
    unittest.main()
