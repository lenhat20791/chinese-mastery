"""Phiên 10: Tests cân bằng quái, boss và người chơi.

Kiểm thử:
- Công thức tính chỉ số tổng hợp
- Mốc đầu/giữa/cuối game
- Tác động pháp bảo, depth, combo
- Tỷ lệ sức mạnh hợp lý
"""
import pytest

import game_balance as balance
import game_config as cfg
import game_core as core
import game_hunt as hunt


class TestBalanceBasics:
    """Kiểm tra công thức cơ bản."""
    
    def test_player_composite_score(self):
        """Chỉ số tổng hợp người chơi phải > 0."""
        score = balance.player_composite_score(0)
        assert score > 0
    
    def test_monster_composite_score(self):
        """Chỉ số tổng hợp quái phải > 0."""
        score = balance.monster_composite_score(0)
        assert score > 0
    
    def test_power_ratio_positive(self):
        """Tỷ lệ sức mạnh phải > 0."""
        ratio = balance.power_ratio(100, 50)
        assert ratio == 2.0
        assert ratio > 0
    
    def test_difficulty_levels(self):
        """Xếp loại độ khó phải đúng."""
        assert balance.difficulty_level(2.0) == "quá_dễ"
        assert balance.difficulty_level(1.2) == "phù_hợp"
        assert balance.difficulty_level(0.8) == "khó"
        assert balance.difficulty_level(0.5) == "quá_khó"


class TestEarlyGameBalance:
    """Kiểm tra cân bằng đầu game (Realm 0)."""
    
    def test_player_stats_realm_0(self):
        """Chỉ số người chơi realm 0 phải là cơ bản."""
        idx = 0
        stats = core.player_stats(idx, [], {})
        assert stats["atk"] == cfg.PLAYER_BASE_ATK
        assert stats["hp"] == cfg.PLAYER_BASE_HP
    
    def test_monster_realm_0_normal(self):
        """Quái thường realm 0."""
        dmg, hp = hunt.monster_stats(0, kind="normal")
        assert hp > 0
        assert dmg > 0
        # Kiểm tra công thức
        expected_hp = cfg.PLAYER_BASE_ATK * cfg.MONSTER_HITS
        assert abs(hp - expected_hp) < 1  # Cho phép sai số làm tròn
    
    def test_early_game_benchmark(self):
        """Mốc đầu game phải phù hợp."""
        report = balance.benchmark_early_game()
        # Không pháp bảo: người chơi gần bằng hoặc yếu hơn quái
        assert report["ratio_no_art"] <= 1.2, f"Quá dễ: {report['ratio_no_art']}"
        # Có pháp bảo: người chơi phải mạnh hơn quái
        assert report["ratio_with_art"] >= 1.0, f"Quá khó: {report['ratio_with_art']}"


class TestMidGameBalance:
    """Kiểm tra cân bằng giữa game (Realm 8)."""
    
    def test_mid_game_benchmark(self):
        """Mốc giữa game phải phù hợp."""
        report = balance.benchmark_mid_game()
        # Người chơi không pháp bảo: phải gần tương đương hoặc hơn một chút
        ratio_no_art = report["ratio_no_art"]
        assert 0.8 <= ratio_no_art <= 2.0, f"Tỷ lệ {ratio_no_art} ngoài 0.8-2.0"
        
        # Có pháp bảo: mạnh hơn tinh anh (pháp bảo là phần thưởng)
        ratio_with_art = report["ratio_with_art"]
        assert ratio_with_art >= 1.0, f"Với pháp bảo phải mạnh hơn tinh anh: {ratio_with_art}"


class TestEndGameBalance:
    """Kiểm tra cân bằng cuối game (Realm 15)."""
    
    def test_end_game_benchmark(self):
        """Mốc cuối game phải phù hợp."""
        report = balance.benchmark_end_game()
        # Người chơi có pháp bảo tốt nhất: mạnh hơn tinh anh (phần thưởng)
        ratio = report["ratio_with_art"]
        assert ratio >= 1.0, f"Phải mạnh hơn tinh anh: {ratio}"


class TestDepthScaling:
    """Kiểm tra tác động của depth (cự sâu)."""
    
    def test_depth_mult_increases(self):
        """Depth multiplier phải tăng theo số trận thắng."""
        d1 = hunt.depth_mult(0)
        d2 = hunt.depth_mult(5)
        d3 = hunt.depth_mult(10)
        assert d1 < d2 < d3
        assert d1 == 1.0
    
    def test_depth_mult_capped(self):
        """Depth multiplier phải bị giới hạn."""
        d_max = hunt.depth_mult(100)
        assert d_max <= cfg.DEPTH_MAX
        assert d_max == cfg.DEPTH_MAX
    
    def test_depth_balance_report(self):
        """Báo cáo depth phải hợp lý."""
        report = balance.benchmark_with_depth()
        results = report["results"]
        
        # Khi depth tăng, độ khó phải tăng
        for wins in [0, 5, 10, 15, 20, 25]:
            key = f"wins_{wins}"
            assert key in results
            data = results[key]
            assert data["ratio_vs_monster"] > 0
        
        # So sánh tỷ lệ: depth tăng -> tỷ lệ giảm (quái mạnh hơn)
        ratio_0 = results["wins_0"]["ratio_vs_monster"]
        ratio_25 = results["wins_25"]["ratio_vs_monster"]
        assert ratio_0 > ratio_25, f"Depth 0: {ratio_0}, Depth 25: {ratio_25}"


class TestArtifactImpact:
    """Kiểm tra tác động pháp bảo."""
    
    def test_artifact_increases_atk(self):
        """Pháp bảo công phải tăng ATK."""
        idx = 0
        stats_no_art = core.player_stats(idx, [], {})
        stats_with_art = core.player_stats(idx, [
            {"recipe_code": "thanh_phong_kiem", "quality": 2, "upgrade": 0}
        ], {})
        assert stats_with_art["atk"] > stats_no_art["atk"]
    
    def test_artifact_increases_hp(self):
        """Pháp bảo thủ phải tăng HP."""
        idx = 1
        stats_no_art = core.player_stats(idx, [], {})
        stats_with_art = core.player_stats(idx, [
            {"recipe_code": "ho_tam_kinh", "quality": 2, "upgrade": 0}
        ], {})
        assert stats_with_art["hp"] > stats_no_art["hp"]
    
    def test_two_artifacts(self):
        """Hai pháp bảo phải tăng chỉ số đáng kể."""
        idx = 5
        artifacts = [
            {"recipe_code": "han_bang_chau", "quality": 2, "upgrade": 0},
            {"recipe_code": "cuu_uu_phien", "quality": 2, "upgrade": 0},
        ]
        stats_no_art = core.player_stats(idx, [], {})
        stats_with_art = core.player_stats(idx, artifacts, {})
        
        atk_increase = (stats_with_art["atk"] - stats_no_art["atk"]) / stats_no_art["atk"]
        hp_increase = (stats_with_art["hp"] - stats_no_art["hp"]) / stats_no_art["hp"]
        
        # Ít nhất phải tăng 10%
        assert atk_increase > 0.1 or hp_increase > 0.1


class TestRealmProgression:
    """Kiểm tra tiến trình qua các cảnh giới."""
    
    def test_player_stats_scale_with_realm(self):
        """Chỉ số người chơi phải tăng theo cảnh giới."""
        stats_0 = core.player_stats(0, [], {})
        stats_5 = core.player_stats(5, [], {})
        stats_15 = core.player_stats(15, [], {})
        
        assert stats_0["atk"] < stats_5["atk"] < stats_15["atk"]
        assert stats_0["hp"] < stats_5["hp"] < stats_15["hp"]
    
    def test_monster_stats_scale_with_realm(self):
        """Chỉ số quái phải tăng theo cảnh giới."""
        dmg_0, hp_0 = hunt.monster_stats(0)
        dmg_5, hp_5 = hunt.monster_stats(5)
        dmg_15, hp_15 = hunt.monster_stats(15)
        
        assert hp_0 < hp_5 < hp_15
        assert dmg_0 < dmg_5 < dmg_15
    
    def test_boss_scales_with_realm(self):
        """Boss phải tăng theo cảnh giới."""
        dmg_0, hp_0 = hunt.monster_stats(0, kind="boss")
        dmg_5, hp_5 = hunt.monster_stats(5, kind="boss")
        dmg_15, hp_15 = hunt.monster_stats(15, kind="boss")
        
        assert hp_0 < hp_5 < hp_15
        assert dmg_0 < dmg_5 < dmg_15


class TestValidation:
    """Kiểm tra validation cân bằng."""
    
    def test_validate_balance(self):
        """Kiểm tra cân bằng không có lỗi nghiêm trọng."""
        result = balance.validate_balance()
        # Có thể có cảnh báo nhưng không nên có lỗi
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
    
    def test_no_critical_errors(self):
        """Không có lỗi nghiêm trọng."""
        result = balance.validate_balance()
        # Báo cáo không có cảnh báo quá khó/quá dễ
        critical_errors = [e for e in result["errors"] if "khó" in e or "dễ" in e]
        # Có thể có warning nhưng không critical
        assert len(critical_errors) == 0


class TestComboCalculation:
    """Kiểm tra tác động combo."""
    
    def test_hit_damage_increases_with_combo(self):
        """Sát thương phải tăng theo combo."""
        import random
        atk = 100
        max_hp = 1000
        min_hits = 4
        
        dmg_no_combo = hunt.hit_damage(atk, 0, max_hp, min_hits, random.Random(42))[0]
        dmg_combo_2 = hunt.hit_damage(atk, 2, max_hp, min_hits, random.Random(42))[0]
        dmg_combo_5 = hunt.hit_damage(atk, 5, max_hp, min_hits, random.Random(42))[0]
        
        # Sát thương tăng với combo
        assert dmg_no_combo < dmg_combo_2
        assert dmg_combo_2 <= dmg_combo_5
    
    def test_combo_capped(self):
        """Combo bonus phải bị giới hạn."""
        atk = 100
        max_hp = 1000
        min_hits = 4
        
        import random
        dmg_combo_5 = hunt.hit_damage(atk, 5, max_hp, min_hits, random.Random(42))[0]
        dmg_combo_10 = hunt.hit_damage(atk, 10, max_hp, min_hits, random.Random(42))[0]
        assert dmg_combo_5 == dmg_combo_10


class TestEliteMonsters:
    """Kiểm tra tinh anh (mạnh hơn quái thường)."""
    
    def test_elite_hp_higher(self):
        """Tinh anh phải có HP cao hơn quái thường."""
        normal_dmg, normal_hp = hunt.monster_stats(5, kind="normal")
        elite_dmg, elite_hp = hunt.monster_stats(5, kind="elite")
        
        assert elite_hp > normal_hp
        assert elite_dmg > normal_dmg
    
    def test_elite_multipliers(self):
        """Tinh anh phải nhân hệ số chính xác."""
        idx = 8
        normal_dmg, normal_hp = hunt.monster_stats(idx, kind="normal")
        elite_dmg, elite_hp = hunt.monster_stats(idx, kind="elite")
        
        hp_ratio = elite_hp / normal_hp
        dmg_ratio = elite_dmg / normal_dmg
        
        assert abs(hp_ratio - cfg.ELITE_HP_MULT) < 0.01
        assert abs(dmg_ratio - cfg.ELITE_ATK_MULT) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
