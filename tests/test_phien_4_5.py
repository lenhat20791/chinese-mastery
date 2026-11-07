"""Test cases cho Phiên 4 & 5: Alchemy System và Mini-game Luyện Đan"""
import random
import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest import mock

import game_config as cfg
import game_core as core


class _TestConnection(sqlite3.Connection):
    def batch(self, statements):
        with self:
            for sql, params in statements:
                self.execute(sql, params)


class TestAlchemy(unittest.TestCase):
    """Phiên 4: Luyện Đan - test các hàm cơ bản"""
    
    def setUp(self):
        """Tạo user DB tạm thời cho testing."""
        # Patch trước khi tạo connection - patch tại game_core module
        self.patcher = mock.patch('game_core.get_user_db')
        self.mock_db = self.patcher.start()
        
        # Tạo DB test riêng cho từng test
        import sqlite3
        self.conn = sqlite3.connect(':memory:', factory=_TestConnection)
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
            """CREATE TABLE IF NOT EXISTS game_profile (
                user_id INTEGER PRIMARY KEY, linh_thach INTEGER DEFAULT 0)""",
        ]:
            self.conn.execute(sql)
        self.conn.commit()
        
        self.mock_db.return_value = self.conn
        self.user_id = 1
        self.conn.execute("INSERT INTO game_profile VALUES (1, 5000)")
        self.conn.commit()
    
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
