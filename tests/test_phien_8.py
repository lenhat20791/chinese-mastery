"""Unit tests cho Phiên 8: Công Pháp (Tâm Pháp & Bí Pháp)."""
import random
import unittest
from unittest.mock import MagicMock, patch, ANY

import game_config as cfg
import game_core as core
from userdb import Row


class TestTechniqueRoll(unittest.TestCase):
    """Test quay công pháp từ boss."""
    
    def test_roll_technique_no_drop(self):
        """Không rơi công pháp nếu may mắn xui."""
        rng = random.Random(42)
        # Xin xích rng để không rơi
        code, grade = core.roll_technique(0, rng=rng)
        if code is None:
            self.assertIsNone(code)
            self.assertIsNone(grade)
    
    def test_roll_technique_high_realm_high_rate(self):
        """Cảnh giới cao có tỉ lệ rơi cao."""
        # Thử 1000 lần ở cảnh giới 15 (50% rơi)
        drops = 0
        for seed in range(10):
            rng = random.Random(seed)
            drops += sum(1 for _ in range(100) if core.roll_technique(15, rng=rng)[0] is not None)
        # Kỳ vọng ~500 lần rơi từ 1000 lần thử
        self.assertGreater(drops, 300)
    
    def test_roll_technique_grade_in_available(self):
        """Cấp độ rơi phải trong danh sách được phép."""
        rng = random.Random(999)
        for realm_idx in [0, 5, 10, 15]:
            for _ in range(20):
                code, grade = core.roll_technique(realm_idx, rng=rng)
                if code is not None:
                    available_grades = cfg.TECHNIQUE_DROP_RATES.get(
                        realm_idx, cfg.TECHNIQUE_DROP_RATES[15]
                    )["grades"]
                    self.assertIn(grade, available_grades)
    
    def test_roll_technique_code_valid(self):
        """Công pháp rơi phải hợp lệ."""
        rng = random.Random(1)
        for _ in range(50):
            code, grade = core.roll_technique(5, rng=rng)
            if code is not None:
                self.assertIn(code, cfg.TECHNIQUE_BY_CODE)
                technique = cfg.TECHNIQUE_BY_CODE[code]
                self.assertEqual(technique["grade"], grade)


class TestAddTechnique(unittest.TestCase):
    """Test thêm công pháp vào kho."""
    
    @patch('game_core.get_user_db')
    def test_add_technique_success(self, mock_get_db):
        """Thêm công pháp thành công."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db
        
        technique_id = core.add_technique(1, "taichi_basic")
        self.assertEqual(technique_id, 1)
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('game_core.get_user_db')
    def test_add_technique_invalid_code(self, mock_get_db):
        """Lỗi khi mã công pháp không hợp lệ."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        technique_id = core.add_technique(1, "invalid_technique")
        self.assertEqual(technique_id, -1)
        mock_db.execute.assert_not_called()


class TestGetTechniquesInventory(unittest.TestCase):
    """Test lấy danh sách công pháp."""
    
    @patch('game_core.get_user_db')
    def test_get_techniques_inventory_empty(self, mock_get_db):
        """Kho trống nếu người chơi chưa có công pháp."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []
        mock_get_db.return_value = mock_db
        
        techniques = core.get_techniques_inventory(1)
        self.assertEqual(len(techniques), 0)
    
    @patch('game_core.get_user_db')
    def test_get_techniques_inventory_with_items(self, mock_get_db):
        """Trả về danh sách công pháp với thông tin đầy đủ."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [
            (1, "taichi_basic", -1, -1, 0),
            (2, "taiji_gong", 0, 1, 0),
        ]
        mock_get_db.return_value = mock_db
        
        techniques = core.get_techniques_inventory(1)
        self.assertEqual(len(techniques), 2)
        self.assertEqual(techniques[0]["code"], "taichi_basic")
        self.assertEqual(techniques[0]["dantian_row"], -1)
        self.assertEqual(techniques[1]["code"], "taiji_gong")
        self.assertEqual(techniques[1]["dantian_row"], 0)
        self.assertEqual(techniques[1]["dantian_col"], 1)


class TestPlaceTechniqueInDantian(unittest.TestCase):
    """Test đặt công pháp vào đan điền."""
    
    @patch('game_core.get_user_db')
    def test_place_technique_bounds_valid(self, mock_get_db):
        """Đặt công pháp thành công trong bounds hợp lệ."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.side_effect = [
            ("taichi_basic",),  # Kiểm tra sở hữu
            None,               # Kiểm tra chỗ trống
        ]
        mock_get_db.return_value = mock_db
        
        success, msg = core.place_technique_in_dantian(1, 1, 0, 0)
        self.assertTrue(success)
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
    
    @patch('game_core.get_user_db')
    def test_place_technique_bounds_invalid_row(self, mock_get_db):
        """Lỗi nếu vị trí ngoài bounds (row)."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        success, msg = core.place_technique_in_dantian(1, 1, -1, 0)
        self.assertFalse(success)
        self.assertIn("không hợp lệ", msg.lower())
    
    @patch('game_core.get_user_db')
    def test_place_technique_bounds_invalid_col(self, mock_get_db):
        """Lỗi nếu vị trí ngoài bounds (col)."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        success, msg = core.place_technique_in_dantian(1, 1, 0, cfg.DANTIAN_COLS)
        self.assertFalse(success)
        self.assertIn("không hợp lệ", msg.lower())
    
    @patch('game_core.get_user_db')
    def test_place_technique_not_owned(self, mock_get_db):
        """Lỗi nếu không sở hữu công pháp."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None
        mock_get_db.return_value = mock_db
        
        success, msg = core.place_technique_in_dantian(1, 999, 0, 0)
        self.assertFalse(success)
        self.assertIn("không tồn tại", msg.lower())
    
    @patch('game_core.get_user_db')
    def test_place_technique_spot_occupied(self, mock_get_db):
        """Lỗi nếu chỗ đã có công pháp khác."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.side_effect = [
            ("taichi_basic",),  # Kiểm tra sở hữu OK
            (999,),             # Kiểm tra chỗ trống: có công pháp khác
        ]
        mock_get_db.return_value = mock_db
        
        success, msg = core.place_technique_in_dantian(1, 1, 0, 0)
        self.assertFalse(success)
        self.assertIn("đã có", msg.lower())


class TestRemoveTechniqueFromDantian(unittest.TestCase):
    """Test tháo công pháp khỏi đan điền."""
    
    @patch('game_core.get_user_db')
    def test_remove_technique_success(self, mock_get_db):
        """Tháo công pháp thành công."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        success, msg = core.remove_technique_from_dantian(1, 1)
        self.assertTrue(success)
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


class TestEquipTechnique(unittest.TestCase):
    """Test trang bị công pháp."""
    
    @patch('game_core.get_user_db')
    def test_equip_technique_slot_1(self, mock_get_db):
        """Trang bị công pháp vào slot 1."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("taichi_basic",)
        mock_get_db.return_value = mock_db
        
        success, msg = core.equip_technique(1, 1, 1)
        self.assertTrue(success)
        self.assertIn("slot 1", msg)
    
    @patch('game_core.get_user_db')
    def test_equip_technique_invalid_slot(self, mock_get_db):
        """Lỗi với slot không hợp lệ."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        success, msg = core.equip_technique(1, 1, 0)
        self.assertFalse(success)
        self.assertIn("không hợp lệ", msg.lower())
    
    @patch('game_core.get_user_db')
    def test_equip_technique_not_owned(self, mock_get_db):
        """Lỗi nếu không sở hữu công pháp."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None
        mock_get_db.return_value = mock_db
        
        success, msg = core.equip_technique(1, 999, 1)
        self.assertFalse(success)


class TestUnequipTechnique(unittest.TestCase):
    """Test tháo công pháp từ slot."""
    
    @patch('game_core.get_user_db')
    def test_unequip_technique_slot_1(self, mock_get_db):
        """Tháo công pháp từ slot 1."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = (1,)
        mock_get_db.return_value = mock_db
        
        success, msg = core.unequip_technique(1, 1)
        self.assertTrue(success)
        self.assertIn("slot 1", msg)
    
    @patch('game_core.get_user_db')
    def test_unequip_technique_invalid_slot(self, mock_get_db):
        """Lỗi với slot không hợp lệ."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        success, msg = core.unequip_technique(1, 3)
        self.assertFalse(success)


class TestGetEquippedTechniques(unittest.TestCase):
    """Test lấy công pháp đang trang bị."""
    
    @patch('game_core.get_user_db')
    def test_get_equipped_techniques_none(self, mock_get_db):
        """Trả về rỗng nếu chưa trang bị."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None
        mock_get_db.return_value = mock_db
        
        equipped = core.get_equipped_techniques(1)
        self.assertIsNone(equipped["slot_1"])
        self.assertIsNone(equipped["slot_2"])
    
    @patch('game_core.get_user_db')
    def test_get_equipped_techniques_with_items(self, mock_get_db):
        """Trả về công pháp đang trang bị."""
        mock_db = MagicMock()
        equipped_row = (1, 2)
        technique_rows = [("taichi_basic",), ("taiji_gong",)]
        
        call_count = [0]
        def side_effect_func(*args, **kwargs):
            mock_result = MagicMock()
            if "game_techniques_equipped" in args[0]:
                mock_result.fetchone.return_value = equipped_row
            else:
                result = technique_rows[call_count[0]]
                call_count[0] += 1
                mock_result.fetchone.return_value = result
            return mock_result
        
        mock_db.execute.side_effect = side_effect_func
        mock_get_db.return_value = mock_db
        
        equipped = core.get_equipped_techniques(1)
        self.assertIsNotNone(equipped["slot_1"])
        self.assertEqual(equipped["slot_1"]["code"], "taichi_basic")


class TestCalcTechniqueBonus(unittest.TestCase):
    """Test tính bonus từ công pháp trang bị."""
    
    @patch('game_core.get_equipped_techniques')
    def test_calc_technique_bonus_no_equipped(self, mock_get_equipped):
        """Không có bonus nếu chưa trang bị."""
        mock_get_equipped.return_value = {"slot_1": None, "slot_2": None}
        
        bonus = core.calc_technique_bonus(1)
        self.assertEqual(bonus["hp_mult"], 0.0)
        self.assertEqual(bonus["atk_mult"], 0.0)
    
    @patch('game_core.get_equipped_techniques')
    def test_calc_technique_bonus_one_equipped(self, mock_get_equipped):
        """Tính bonus khi trang bị 1 công pháp."""
        mock_get_equipped.return_value = {
            "slot_1": {
                "hp_mult": 0.06,
                "atk_mult": 0.0,
                "size": (1, 2),
            },
            "slot_2": None,
        }
        
        bonus = core.calc_technique_bonus(1)
        # 0.06 * 1.0 (size 1x2 mult) = 0.06
        self.assertEqual(bonus["hp_mult"], 0.06)
        self.assertEqual(bonus["atk_mult"], 0.0)
    
    @patch('game_core.get_equipped_techniques')
    def test_calc_technique_bonus_both_equipped(self, mock_get_equipped):
        """Tính bonus khi trang bị 2 công pháp."""
        mock_get_equipped.return_value = {
            "slot_1": {
                "hp_mult": 0.06,
                "atk_mult": 0.0,
                "size": (2, 2),
            },
            "slot_2": {
                "hp_mult": 0.0,
                "atk_mult": 0.05,
                "size": (1, 2),
            },
        }
        
        bonus = core.calc_technique_bonus(1)
        # 0.06 * 2.0 (size 2x2 mult) = 0.12; 0.05 * 1.0 (size 1x2 mult) = 0.05
        self.assertEqual(bonus["hp_mult"], 0.12)
        self.assertEqual(bonus["atk_mult"], 0.05)


class TestTechniqueConfig(unittest.TestCase):
    """Test cấu hình công pháp."""
    
    def test_techniques_exist(self):
        """Phải có ít nhất 10 công pháp."""
        self.assertGreaterEqual(len(cfg.TECHNIQUES), 10)
    
    def test_technique_codes_unique(self):
        """Các mã công pháp phải độc nhất."""
        codes = [t["code"] for t in cfg.TECHNIQUES]
        self.assertEqual(len(codes), len(set(codes)))
    
    def test_technique_grades_valid(self):
        """Cấp độ công pháp phải hợp lệ (0-4)."""
        for technique in cfg.TECHNIQUES:
            self.assertIn(technique["grade"], range(5))
    
    def test_technique_kind_valid(self):
        """Loại công pháp phải là 'heart' hoặc 'secret'."""
        for technique in cfg.TECHNIQUES:
            self.assertIn(technique["kind"], ["heart", "secret"])
    
    def test_technique_by_code_lookup(self):
        """Lookup bằng mã phải hoạt động."""
        for technique in cfg.TECHNIQUES:
            self.assertEqual(cfg.TECHNIQUE_BY_CODE[technique["code"]], technique)
    
    def test_dantian_dimensions(self):
        """Đan điền phải có kích cỡ hợp lý."""
        self.assertGreater(cfg.DANTIAN_ROWS, 0)
        self.assertGreater(cfg.DANTIAN_COLS, 0)
        self.assertEqual(cfg.DANTIAN_TOTAL, cfg.DANTIAN_ROWS * cfg.DANTIAN_COLS)


if __name__ == "__main__":
    unittest.main()
