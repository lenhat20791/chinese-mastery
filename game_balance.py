"""Phiên 10: Kiểm thử cân bằng quái, boss và người chơi.

Rà soát công thức tính chỉ số tổng hợp, kiểm tra mốc đầu/giữa/cuối game,
với/không pháp bảo, cân nhắc sút sức mạnh (depth) và combo.
"""
import math

import game_config as cfg
import game_core as core
import game_hunt as hunt


# ---------------------------------------------------------------------------
# Hàm kiểm thử cân bằng
# ---------------------------------------------------------------------------

def player_composite_score(idx, artifacts=None, bonuses=None):
    """Tính chỉ số tổng hợp của người chơi: ATK + HP (chuẩn hóa)."""
    stats = core.player_stats(idx, artifacts or [], bonuses or {})
    # Chỉ số tổng hợp = ATK + (HP / 10) để cân đối tỷ lệ
    return stats["atk"] + stats["hp"] / 10.0


def monster_composite_score(realm_idx, kind="normal", wins=0):
    """Tính chỉ số tổng hợp quái: damage + (HP / 10)."""
    dmg, hp = hunt.monster_stats(realm_idx, kind=kind, wins=wins)
    return dmg + hp / 10.0


def boss_composite_score(realm_idx):
    """Tính chỉ số tổng hợp boss."""
    return monster_composite_score(realm_idx, kind="boss")


def elite_composite_score(realm_idx, wins=0):
    """Tính chỉ số tổng hợp tinh anh."""
    return monster_composite_score(realm_idx, kind="elite", wins=wins)


def power_ratio(player_score, enemy_score):
    """Tỷ lệ sức mạnh: player_score / enemy_score. > 1 = người chơi mạnh hơn."""
    return player_score / enemy_score if enemy_score > 0 else float('inf')


def difficulty_level(ratio):
    """Xếp loại độ khó dựa vào tỷ lệ sức mạnh.
    
    Tỷ lệ >= 1.5: Quá dễ (gật đầu)
    Tỷ lệ 1.0-1.5: Phù hợp
    Tỷ lệ 0.7-1.0: Khó
    Tỷ lệ < 0.7: Quá khó (bất khả)
    """
    if ratio >= 1.5:
        return "quá_dễ"
    elif ratio >= 1.0:
        return "phù_hợp"
    elif ratio >= 0.7:
        return "khó"
    else:
        return "quá_khó"


# ---------------------------------------------------------------------------
# Chỉ số tại các mốc game
# ---------------------------------------------------------------------------

def benchmark_early_game():
    """Mốc đầu game: Realm 0 (Linh Khí Kỳ - Sơ Kỳ)."""
    idx = 0
    p_no_art = player_composite_score(idx)
    p_with_art = player_composite_score(idx, artifacts=[
        {"recipe_code": "thanh_phong_kiem", "quality": 2, "upgrade": 0}
    ])
    m_normal = monster_composite_score(idx, kind="normal")
    m_elite = elite_composite_score(idx)
    boss = boss_composite_score(idx)
    
    return {
        "stage": "Đầu game (Realm 0)",
        "player_no_artifact": p_no_art,
        "player_with_artifact": p_with_art,
        "monster_normal": m_normal,
        "monster_elite": m_elite,
        "boss": boss,
        "ratio_no_art": power_ratio(p_no_art, m_normal),
        "ratio_with_art": power_ratio(p_with_art, m_elite),
        "ratio_vs_boss": power_ratio(p_with_art, boss),
    }


def benchmark_mid_game():
    """Mốc giữa game: Realm 8 (Độ Kiếp Kỳ - Hậu Kỳ)."""
    idx = 8
    # Pháp bảo tốt nhất mở được ở realm 8
    artifacts = [
        {"recipe_code": "han_bang_chau", "quality": 2, "upgrade": 2},  # Linh Bảo
        {"recipe_code": "cuu_uu_phien", "quality": 2, "upgrade": 2},
    ]
    p_no_art = player_composite_score(idx)
    p_with_art = player_composite_score(idx, artifacts=artifacts)
    m_normal = monster_composite_score(idx, kind="normal")
    m_elite = elite_composite_score(idx)
    boss = boss_composite_score(idx)
    
    return {
        "stage": "Giữa game (Realm 8 - Độ Kiếp Kỳ)",
        "player_no_artifact": p_no_art,
        "player_with_artifact": p_with_art,
        "monster_normal": m_normal,
        "monster_elite": m_elite,
        "boss": boss,
        "ratio_no_art": power_ratio(p_no_art, m_normal),
        "ratio_with_art": power_ratio(p_with_art, m_elite),
        "ratio_vs_boss": power_ratio(p_with_art, boss),
    }


def benchmark_end_game():
    """Mốc cuối game: Realm 15 (Tiên Đế)."""
    idx = 15
    # Pháp bảo tốt nhất (Tiên Khí - cấp cao nhất)
    artifacts = [
        {"recipe_code": "ngoc_hu_tien_kiem", "quality": 2, "upgrade": 9},  # Tiên Khí
    ]
    p_no_art = player_composite_score(idx)
    p_with_art = player_composite_score(idx, artifacts=artifacts)
    m_normal = monster_composite_score(idx, kind="normal")
    m_elite = elite_composite_score(idx)
    boss = boss_composite_score(idx)
    
    return {
        "stage": "Cuối game (Realm 15 - Tiên Đế)",
        "player_no_artifact": p_no_art,
        "player_with_artifact": p_with_art,
        "monster_normal": m_normal,
        "monster_elite": m_elite,
        "boss": boss,
        "ratio_no_art": power_ratio(p_no_art, m_normal),
        "ratio_with_art": power_ratio(p_with_art, m_elite),
        "ratio_vs_boss": power_ratio(p_with_art, boss),
    }


def benchmark_with_depth():
    """Kiểm tra ảnh hưởng của depth (cự sâu) đến cân bằng."""
    realm_idx = 8
    results = {}
    for wins in [0, 5, 10, 15, 20, 25]:
        depth_mult = hunt.depth_mult(wins)
        m_normal = monster_composite_score(realm_idx, kind="normal", wins=wins)
        m_elite = elite_composite_score(realm_idx, wins=wins)
        p_with_art = player_composite_score(realm_idx, artifacts=[
            {"recipe_code": "han_bang_chau", "quality": 2, "upgrade": 2},
        ])
        results[f"wins_{wins}"] = {
            "depth_mult": depth_mult,
            "monster_normal_score": m_normal,
            "ratio_vs_monster": power_ratio(p_with_art, m_normal),
            "difficulty": difficulty_level(power_ratio(p_with_art, m_normal)),
        }
    return {"realm": realm_idx, "results": results}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_balance():
    """Kiểm tra cân bằng cơ bản."""
    errors = []
    warnings = []
    
    # Kiểm tra số lượng quái và boss
    if len(cfg.MONSTERS) < 5:
        errors.append(f"Quái quá ít: {len(cfg.MONSTERS)} (khuyến cáo >= 5)")
    if len(cfg.BOSSES) < 3:
        errors.append(f"Boss quá ít: {len(cfg.BOSSES)} (khuyến cáo >= 3)")
    
    # Kiểm tra hệ số sức mạnh
    if cfg.POWER_PER_REALM < 1.1 or cfg.POWER_PER_REALM > 1.5:
        warnings.append(f"POWER_PER_REALM = {cfg.POWER_PER_REALM} (bình thường 1.2-1.3)")
    
    # Kiểm tra công thức quái/boss
    if cfg.MONSTER_ATK_RATIO < 0.08 or cfg.MONSTER_ATK_RATIO > 0.15:
        warnings.append(f"MONSTER_ATK_RATIO = {cfg.MONSTER_ATK_RATIO} (bình thường 0.10-0.12)")
    
    if cfg.BOSS_ATK_RATIO < 0.12 or cfg.BOSS_ATK_RATIO > 0.18:
        warnings.append(f"BOSS_ATK_RATIO = {cfg.BOSS_ATK_RATIO} (bình thường 0.13-0.15)")
    
    if cfg.MONSTER_HITS < 3 or cfg.MONSTER_HITS > 10:
        warnings.append(f"MONSTER_HITS = {cfg.MONSTER_HITS} (bình thường 6-8)")
    
    if cfg.BOSS_HITS < 12 or cfg.BOSS_HITS > 20:
        warnings.append(f"BOSS_HITS = {cfg.BOSS_HITS} (bình thường 12-18)")
    
    # Kiểm tra depth scaling
    if cfg.DEPTH_MAX < 2.0 or cfg.DEPTH_MAX > 3.0:
        warnings.append(f"DEPTH_MAX = {cfg.DEPTH_MAX} (bình thường 2.0-2.5)")
    
    # Kiểm tra mốc chỉ số
    try:
        early = benchmark_early_game()
        if early["ratio_no_art"] < 0.5:
            errors.append(f"Đầu game quá khó (ratio {early['ratio_no_art']:.2f})")
        if early["ratio_no_art"] > 3.0:
            warnings.append(f"Đầu game quá dễ (ratio {early['ratio_no_art']:.2f})")
        
        mid = benchmark_mid_game()
        if mid["ratio_with_art"] < 0.8:
            warnings.append(f"Giữa game khó (ratio {mid['ratio_with_art']:.2f})")
        
        end = benchmark_end_game()
        if end["ratio_with_art"] < 0.8:
            warnings.append(f"Cuối game khó (ratio {end['ratio_with_art']:.2f})")
    except Exception as e:
        errors.append(f"Lỗi khi kiểm tra mốc chỉ số: {e}")
    
    return {"errors": errors, "warnings": warnings}


def print_benchmark_report():
    """In báo cáo cân bằng ra console."""
    print("\n" + "="*80)
    print("BAOCAO CAN BANG PHIEN 10")
    print("="*80)
    
    for name, func in [("Đầu game", benchmark_early_game), 
                       ("Giữa game", benchmark_mid_game),
                       ("Cuối game", benchmark_end_game)]:
        report = func()
        print(f"\n{name}:")
        print(f"  Người chơi (không pháp bảo): {report['player_no_artifact']:.2f}")
        print(f"  Người chơi (có pháp bảo): {report['player_with_artifact']:.2f}")
        print(f"  Quái thường: {report['monster_normal']:.2f}")
        print(f"  Tinh anh: {report['monster_elite']:.2f}")
        print(f"  Boss: {report['boss']:.2f}")
        print(f"  Tỷ lệ (không pháp bảo / quái): {report['ratio_no_art']:.2f} ({difficulty_level(report['ratio_no_art'])})")
        print(f"  Tỷ lệ (có pháp bảo / tinh anh): {report['ratio_with_art']:.2f} ({difficulty_level(report['ratio_with_art'])})")
        print(f"  Tỷ lệ (có pháp bảo / boss): {report['ratio_vs_boss']:.2f} ({difficulty_level(report['ratio_vs_boss'])})")
    
    print("\n" + "-"*80)
    print("KIỂM TRA DEPTH SCALING (Realm 8)")
    print("-"*80)
    depth_report = benchmark_with_depth()
    for wins_label, data in depth_report["results"].items():
        print(f"  {wins_label} (depth ×{data['depth_mult']:.2f}): "
              f"Tỷ lệ = {data['ratio_vs_monster']:.2f} ({data['difficulty']})")
    
    print("\n" + "-"*80)
    print("KIỂM THỰC")
    print("-"*80)
    validation = validate_balance()
    if validation["errors"]:
        print("❌ LỖI:")
        for err in validation["errors"]:
            print(f"  - {err}")
    else:
        print("✓ Không có lỗi cung chỉ")
    
    if validation["warnings"]:
        print("\n⚠️  CẢNH BÁO:")
        for warn in validation["warnings"]:
            print(f"  - {warn}")
    else:
        print("\n✓ Không có cảnh báo")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print_benchmark_report()
