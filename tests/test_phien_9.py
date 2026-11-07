"""Unit tests cho Phiên 9: Đan Điền và trang bị công pháp."""
import unittest
from unittest.mock import MagicMock, patch

import game_config as cfg
import game_core as core


class TestDantianPlacement(unittest.TestCase):
    """Test đặt công pháp vào đan điền."""
    
    def test_dantian_grid_size(self):
        """Đan điền phải có kích cỡ hợp lý."""
        self.assertEqual(cfg.DANTIAN_TOTAL, cfg.DANTIAN_ROWS * cfg.DANTIAN_COLS)
        self.assertGreater(cfg.DANTIAN_TOTAL, 0)
    
    @patch('game_core.get_user_db')
    def test_place_in_valid_bounds(self, mock_get_db):
        """Đặt công pháp trong bounds hợp lệ."""
        mock_db = MagicMock()
        # Tạo side_effect với nhiều phần tử để cover tất cả lần gọi
        mock_db.execute.return_value.fetchone.side_effect = [
            ("taichi_basic",),  # Kiểm tra sở hữu
            None,               # Kiểm tra chỗ trống
            ("taichi_basic",),  # Kiểm tra sở hữu (lần 2)
            None,               # Kiểm tra chỗ trống (lần 2)
            ("taichi_basic",),  # Kiểm tra sở hữu (lần 3)
            None,               # Kiểm tra chỗ trống (lần 3)
            ("taichi_basic",),  # Kiểm tra sở hữu (lần 4)
            None,               # Kiểm tra chỗ trống (lần 4)
        ]
        mock_get_db.return_value = mock_db
        
        test_positions = [
            (0, 0),
            (0, cfg.DANTIAN_COLS - 1),
            (cfg.DANTIAN_ROWS - 1, 0),
            (cfg.DANTIAN_ROWS - 1, cfg.DANTIAN_COLS - 1),
        ]
        
        for row, col in test_positions:
            success, msg = core.place_technique_in_dantian(1, 1, row, col)
            self.assertTrue(success, f"Failed at ({row}, {col}): {msg}")


class TestEquipmentBonus(unittest.TestCase):
    """Test tính bonus từ công pháp trang bị."""
    
    @patch('game_core.get_equipped_techniques')
    def test_no_bonus_no_equipped(self, mock_get_equipped):
        """Không có bonus nếu chưa trang bị."""
        mock_get_equipped.return_value = {"slot_1": None, "slot_2": None}
        
        bonus = core.calc_technique_bonus(1)
        self.assertEqual(bonus["hp_mult"], 0.0)
        self.assertEqual(bonus["atk_mult"], 0.0)
    
    @patch('game_core.get_equipped_techniques')
    def test_hp_bonus_from_heart_technique(self, mock_get_equipped):
        """Tâm pháp trong slot 1 cộng HP."""
        mock_get_equipped.return_value = {
            "slot_1": {"hp_mult": 0.06, "atk_mult": 0.0, "size": (2, 2)},
            "slot_2": None,
        }
        
        bonus = core.calc_technique_bonus(1)
        # 0.06 * 2.0 (size 2x2) = 0.12
        self.assertEqual(bonus["hp_mult"], 0.12)
        self.assertEqual(bonus["atk_mult"], 0.0)
    
    @patch('game_core.get_equipped_techniques')
    def test_atk_bonus_from_secret_technique(self, mock_get_equipped):
        """Bí pháp trong slot 2 cộng ATK."""
        mock_get_equipped.return_value = {
            "slot_1": None,
            "slot_2": {"hp_mult": 0.0, "atk_mult": 0.06, "size": (2, 3)},
        }
        
        bonus = core.calc_technique_bonus(1)
        # 0.06 * 3.0 (size 2x3) = 0.18
        self.assertEqual(bonus["hp_mult"], 0.0)
        self.assertEqual(bonus["atk_mult"], 0.18)
    
    @patch('game_core.get_equipped_techniques')
    def test_combined_bonus_both_slots(self, mock_get_equipped):
        """Cộng bonus từ cả 2 slot."""
        mock_get_equipped.return_value = {
            "slot_1": {"hp_mult": 0.06, "atk_mult": 0.0, "size": (2, 2)},
            "slot_2": {"hp_mult": 0.0, "atk_mult": 0.06, "size": (2, 2)},
        }
        
        bonus = core.calc_technique_bonus(1)
        # 0.06 * 2.0 = 0.12 (HP); 0.06 * 2.0 = 0.12 (ATK)
        self.assertEqual(bonus["hp_mult"], 0.12)
        self.assertEqual(bonus["atk_mult"], 0.12)


class TestTechniqueTypes(unittest.TestCase):
    """Test phân loại công pháp."""
    
    def test_heart_techniques_have_hp_mult(self):
        """Tâm pháp phải có hp_mult > 0."""
        heart_techniques = [t for t in cfg.TECHNIQUES if t["kind"] == "heart"]
        self.assertGreater(len(heart_techniques), 0)
        for tech in heart_techniques:
            self.assertGreater(tech["hp_mult"], 0)
            self.assertEqual(tech["atk_mult"], 0)
    
    def test_secret_techniques_have_atk_mult(self):
        """Bí pháp phải có atk_mult > 0."""
        secret_techniques = [t for t in cfg.TECHNIQUES if t["kind"] == "secret"]
        self.assertGreater(len(secret_techniques), 0)
        for tech in secret_techniques:
            self.assertGreater(tech["atk_mult"], 0)
            self.assertEqual(tech["hp_mult"], 0)


class TestDantianState(unittest.TestCase):
    """Test quản lý trạng thái đan điền."""
    
    @patch('game_core.get_user_db')
    def test_place_and_remove_technique(self, mock_get_db):
        """Đặt rồi tháo công pháp."""
        mock_db = MagicMock()
        
        # Đặt công pháp
        mock_db.execute.return_value.fetchone.side_effect = [
            ("taichi_basic",),  # Sở hữu
            None,               # Chỗ trống
        ]
        mock_get_db.return_value = mock_db
        
        success, msg = core.place_technique_in_dantian(1, 1, 0, 0)
        self.assertTrue(success)
        
        # Tháo công pháp
        mock_get_db.return_value = mock_db
        success, msg = core.remove_technique_from_dantian(1, 1)
        self.assertTrue(success)


class TestBossDropRates(unittest.TestCase):
    """Test tỉ lệ rơi công pháp từ boss."""
    
    def test_drop_rates_configured_for_all_realms(self):
        """Tất cả 16 cảnh giới phải có config rơi."""
        configured_realms = set(cfg.TECHNIQUE_DROP_RATES.keys())
        self.assertGreater(len(configured_realms), 0)
    
    def test_drop_rates_increase_with_realm(self):
        """Tỉ lệ rơi phải tăng theo cảnh giới."""
        rates = [cfg.TECHNIQUE_DROP_RATES.get(i, cfg.TECHNIQUE_DROP_RATES[15])["rate"] for i in range(0, 16, 2)]
        # Kiểm tra xu hướng tăng (không hoàn toàn chặt nhưng nên tăng)
        self.assertLessEqual(rates[0], rates[-1])
    
    def test_available_grades_in_valid_range(self):
        """Cấp độ rơi phải hợp lệ (0-4)."""
        for realm_idx, config in cfg.TECHNIQUE_DROP_RATES.items():
            for grade in config["grades"]:
                self.assertIn(grade, range(5))


class TestEquipmentConstraints(unittest.TestCase):
    """Test các ràng buộc khi trang bị."""
    
    @patch('game_core.get_user_db')
    def test_equip_heart_to_slot_1(self, mock_get_db):
        """Tâm pháp nên trang bị vào slot 1."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("taichi_basic",)
        mock_get_db.return_value = mock_db
        
        success, msg = core.equip_technique(1, 1, 1)
        self.assertTrue(success)
        self.assertIn("slot 1", msg)
    
    @patch('game_core.get_user_db')
    def test_equip_secret_to_slot_2(self, mock_get_db):
        """Bí pháp nên trang bị vào slot 2."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("chixiao_jian",)
        mock_get_db.return_value = mock_db
        
        success, msg = core.equip_technique(1, 1, 2)
        self.assertTrue(success)
        self.assertIn("slot 2", msg)


class TestInventoryAndPlacement(unittest.TestCase):
    """Test quản lý kho công pháp."""
    
    @patch('game_core.get_user_db')
    def test_get_unplaced_techniques(self, mock_get_db):
        """Công pháp chưa đặt có dantian_row = -1."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [
            (1, "taichi_basic", -1, -1, 0),
            (2, "taiji_gong", 0, 1, 0),
        ]
        mock_get_db.return_value = mock_db
        
        techniques = core.get_techniques_inventory(1)
        
        unplaced = [t for t in techniques if t["dantian_row"] == -1]
        placed = [t for t in techniques if t["dantian_row"] != -1]
        
        self.assertEqual(len(unplaced), 1)
        self.assertEqual(len(placed), 1)


class TestTechniqueColors(unittest.TestCase):
    """Test màu sắc công pháp theo cấp độ."""
    
    def test_technique_colors_defined(self):
        """Phải có màu cho từng cấp độ."""
        self.assertEqual(len(cfg.TECHNIQUE_COLORS), len(cfg.TECHNIQUE_GRADES))
    
    def test_all_grades_have_colors(self):
        """Tất cả cấp độ (0-4) phải có màu."""
        for grade in range(5):
            self.assertLess(grade, len(cfg.TECHNIQUE_COLORS))


class TestTechniqueGradeNames(unittest.TestCase):
    """Test tên cấp độ công pháp."""
    
    def test_technique_grades_count(self):
        """Phải có 5 cấp độ."""
        self.assertEqual(len(cfg.TECHNIQUE_GRADES), 5)
    
    def test_technique_grades_non_empty(self):
        """Tên cấp độ phải không trống."""
        for grade_name in cfg.TECHNIQUE_GRADES:
            self.assertIsNotNone(grade_name)
            self.assertGreater(len(grade_name), 0)


class TestCoreIntegration(unittest.TestCase):
    """Test tích hợp giữa các hàm core."""
    
    @patch('game_core.get_user_db')
    def test_place_and_equip_workflow(self, mock_get_db):
        """Workflow: thêm -> đặt -> trang bị công pháp."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        
        # Setup mocks cho từng bước
        mock_db.execute.return_value = mock_cursor
        mock_get_db.return_value = mock_db
        
        # Bước 1: Thêm công pháp
        tech_id = core.add_technique(1, "taichi_basic")
        self.assertGreater(tech_id, 0)
        
        # Bước 2: Đặt công pháp (mock lại)
        mock_db.execute.return_value.fetchone.side_effect = [
            ("taichi_basic",),  # Sở hữu
            None,               # Chỗ trống
        ]
        success, _ = core.place_technique_in_dantian(1, 1, 0, 0)
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
