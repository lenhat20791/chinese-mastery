import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import game_config as cfg
import game_core as core
import game_hunt
import game_questions as gq


class PureLogicTests(unittest.TestCase):
    def test_thresholds(self):
        t = cfg.SUB_THRESHOLDS
        self.assertEqual(len(t), 48)
        self.assertEqual(t[0], 0)
        self.assertEqual(t, sorted(t))
        self.assertLessEqual(t[-1], cfg.HSK5_WORDS)

    def test_realm_info(self):
        self.assertEqual(core.realm_info(0)["idx"], 0)
        self.assertEqual(core.realm_info(1199)["idx"], 8)
        self.assertEqual(core.realm_info(1200)["idx"], 9)
        self.assertIsNone(core.realm_info(5000)["next_need"])

    def test_multiplier(self):
        self.assertEqual(core.play_multiplier(0), 1.0)
        self.assertEqual(core.play_multiplier(9), 1.0)
        self.assertEqual(core.play_multiplier(10), cfg.MULT_MID)
        self.assertEqual(core.play_multiplier(30), cfg.MULT_LOW)

    def test_pity(self):
        rng = random.Random(1)
        self.assertEqual(core.roll_quality(cfg.QUALITY_ODDS, 0, cfg.PITY_HIGH_AT - 1, rng)[0], 2)
        q, _, _ = core.roll_quality(cfg.QUALITY_ODDS, cfg.PITY_MID_AT - 1, 0, rng)
        self.assertGreaterEqual(q, 1)
        counts = [0, 0, 0]
        pm = ph = 0
        for _ in range(6000):
            q, pm, ph = core.roll_quality(cfg.QUALITY_ODDS, pm, ph, rng)
            counts[q] += 1
        self.assertGreater(counts[0], counts[1])
        self.assertGreater(counts[1], counts[2])

    def test_pinyin(self):
        word = {"pinyin": "nǐ hǎo"}
        for ok in ("nǐ hǎo", "ni3 hao3", "nihao", "NI HAO"):
            self.assertTrue(gq.check_pinyin(ok, word), ok)
        self.assertFalse(gq.check_pinyin("ni", word))
        self.assertFalse(gq.check_pinyin("", word))
        self.assertTrue(gq.check_pinyin("lv4", {"pinyin": "lǜ"}))

    def test_tokenize(self):
        self.assertEqual(gq.tokenize_sentence("我喜欢你。", ["喜欢"]), ["我", "喜欢", "你"])

    def test_question_types(self):
        pool = [{"id": i, "hanzi": f"字{i}", "pinyin": f"zi{i}", "meaning_vi": f"nghĩa {i}",
                 "example_zh": f"这是字{i}。", "example_cloze": "这是______。"} for i in range(6)]
        for qtype in gq.QTYPES:
            q = gq.make_question(pool[0], pool, qtype)
            if q["options"] is not None:
                self.assertEqual(sum(o["ok"] for o in q["options"]), 1)
                self.assertEqual(len({o["label"] for o in q["options"]}), len(q["options"]))
        self.assertTrue(gq.evaluate(gq.make_question(pool[0], pool, "pinyin"), "zi0"))

    def test_economy(self):
        recipe = cfg.RECIPE_BY_CODE["thanh_phong_kiem"]
        self.assertEqual(core.recipe_craft_cost(recipe), 400)
        self.assertEqual(core.recipe_price(recipe), 150)
        for recipe in cfg.RECIPES:
            mats = core.recipe_materials(recipe)
            self.assertTrue(mats)
            for code, _ in mats:
                self.assertIn(code, cfg.ITEMS)

    def test_stat_bonuses(self):
        zero = core.stat_bonuses()
        self.assertEqual((zero["crit"], zero["hp"], zero["dao_tam"]), (0, 0, 0))
        big = core.stat_bonuses(words=10**6, answers=10**6, streak=10**6)
        self.assertLess(big["crit"], cfg.CRIT_MAX)
        self.assertLess(big["hp"], cfg.CAN_CO_HP_MAX + 1e-9)
        self.assertLess(big["dao_tam"], cfg.DAO_TAM_MAX)
        mid = core.stat_bonuses(words=1250, answers=3000, streak=90)
        self.assertAlmostEqual(mid["crit"], cfg.CRIT_MAX / 2)
        self.assertAlmostEqual(mid["dao_tam"], cfg.DAO_TAM_MAX / 2)
        base = core.player_stats(3)
        boosted = core.player_stats(3, bonuses=mid)
        self.assertAlmostEqual(boosted["hp"], base["hp"] * (1 + mid["hp"]))
        self.assertAlmostEqual(boosted["crit"], mid["crit"])

    def test_cultivation_boost(self):
        """Kiểm tra boost chỉ số cơ bản theo tu vi: +5% ATK và +5% HP mỗi cấp."""
        # Test hàm cultivation_boost
        atk_pct_0, hp_pct_0 = core.cultivation_boost(0)
        self.assertEqual((atk_pct_0, hp_pct_0), (0, 0))
        
        atk_pct_1, hp_pct_1 = core.cultivation_boost(1)
        self.assertAlmostEqual(atk_pct_1, cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
        self.assertAlmostEqual(hp_pct_1, cfg.CULTIVATION_BOOST_HP_PCT / 100.0)
        
        atk_pct_10, hp_pct_10 = core.cultivation_boost(10)
        self.assertAlmostEqual(atk_pct_10, 10 * cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
        self.assertAlmostEqual(hp_pct_10, 10 * cfg.CULTIVATION_BOOST_HP_PCT / 100.0)
        
        # Test player_stats với cultivation boost
        stats_0 = core.player_stats(0)
        stats_1 = core.player_stats(1)
        stats_10 = core.player_stats(10)
        
        # Ở realm 0: không có boost
        expected_atk_0 = cfg.PLAYER_BASE_ATK
        expected_hp_0 = cfg.PLAYER_BASE_HP
        self.assertAlmostEqual(stats_0["atk"], expected_atk_0)
        self.assertAlmostEqual(stats_0["hp"], expected_hp_0)
        
        # Ở realm 1: +5% boost
        expected_atk_1 = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** 1 * (1 + cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
        expected_hp_1 = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** 1 * (1 + cfg.CULTIVATION_BOOST_HP_PCT / 100.0)
        self.assertAlmostEqual(stats_1["atk"], expected_atk_1)
        self.assertAlmostEqual(stats_1["hp"], expected_hp_1)
        
        # Ở realm 10: +50% boost
        expected_atk_10 = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** 10 * (1 + 10 * cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
        expected_hp_10 = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** 10 * (1 + 10 * cfg.CULTIVATION_BOOST_HP_PCT / 100.0)
        self.assertAlmostEqual(stats_10["atk"], expected_atk_10)
        self.assertAlmostEqual(stats_10["hp"], expected_hp_10)
        
        # Test: cultivation boost KHÔNG cộng dồn với bonus khác
        # Nếu có bonus từ Căn cơ, chỉ cộng thêm một lần
        bonus = core.stat_bonuses(words=1250)  # trả về bonus từ Căn cơ
        stats_1_with_bonus = core.player_stats(1, bonuses=bonus)
        # Expected: base_atk_1 * (1 + cultivation_boost) * (1 + can_co_bonus)
        base_atk_1_with_cult = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** 1 * (1 + cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
        expected_atk_1_with_bonus = base_atk_1_with_cult * (1 + bonus["atk"])
        self.assertAlmostEqual(stats_1_with_bonus["atk"], expected_atk_1_with_bonus)

    def test_combat_math(self):
        atk, hp = game_hunt.monster_stats(0)
        self.assertAlmostEqual(hp, cfg.PLAYER_BASE_ATK * cfg.MONSTER_HITS)
        dmg, crit = game_hunt.hit_damage(1000, 5, hp, cfg.MONSTER_MIN_HITS, random.Random(1), crit=1.0)
        self.assertTrue(crit)
        self.assertLessEqual(dmg, hp / cfg.MONSTER_MIN_HITS + 1)
        loot = game_hunt.roll_loot(2, "boss", random.Random(3))
        self.assertTrue(all(code.startswith("r2_") for code in loot))
        normal = game_hunt.roll_loot(1, "normal", random.Random(3))
        self.assertTrue(all(int(code[-1]) < 3 for code in normal))
        self.assertEqual(game_hunt.scale_loot({"r0_0": 3}, 0, random.Random(1)), {})

    def test_depth_scaling(self):
        base_atk, base_hp = game_hunt.monster_stats(3)
        atk, hp = game_hunt.monster_stats(3, wins=5)
        self.assertAlmostEqual(hp, base_hp * (1 + 5 * cfg.DEPTH_STEP))
        self.assertAlmostEqual(game_hunt.monster_stats(3, wins=10 ** 6)[1], base_hp * cfg.DEPTH_MAX)
        self.assertGreater(game_hunt.monster_stats(3, "elite")[1], base_hp)

    def test_areas(self):
        self.assertEqual(len(cfg.AREAS), 2 * len(cfg.MAJOR_REALMS))
        for area in cfg.AREAS:
            self.assertEqual(area["item_set"], area["realm"] // 2)
            self.assertEqual("boss" in area, area["kind"] == "elite")
            self.assertIn("\n", game_hunt.area_tooltip(area))
        self.assertTrue(all(r["min_idx"] // 2 == r["region"] for r in cfg.RECIPES))

    def test_cultivation_progression_e2e(self):
        """E2E test: Tăng cấp từ realm 0 -> 15 và xác nhận chỉ số được tính đúng."""
        prev_atk = None
        prev_hp = None
        
        for idx in range(16):
            stats = core.player_stats(idx)
            atk = stats["atk"]
            hp = stats["hp"]
            
            # Kiểm tra chỉ số tăng khi lên cấp (luôn tăng hoặc bằng cấp trước)
            if prev_atk is not None:
                self.assertGreaterEqual(atk, prev_atk, 
                    f"ATK should increase or stay same when level {idx-1} -> {idx}")
                self.assertGreaterEqual(hp, prev_hp,
                    f"HP should increase or stay same when level {idx-1} -> {idx}")
            
            # Kiểm tra cultivation boost được tính đúng
            expected_atk_pct, expected_hp_pct = core.cultivation_boost(idx)
            base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
            base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
            expected_atk = base_atk * (1 + expected_atk_pct)
            expected_hp = base_hp * (1 + expected_hp_pct)
            
            self.assertAlmostEqual(atk, expected_atk, places=5,
                msg=f"Realm {idx}: ATK calculation mismatch (got {atk}, expected {expected_atk})")
            self.assertAlmostEqual(hp, expected_hp, places=5,
                msg=f"Realm {idx}: HP calculation mismatch (got {hp}, expected {expected_hp})")
            
            # Kiểm tra boost % tăng đều đặn: +5% mỗi cấp
            if idx > 0:
                prev_atk_pct, prev_hp_pct = core.cultivation_boost(idx - 1)
                diff_atk_pct = expected_atk_pct - prev_atk_pct
                diff_hp_pct = expected_hp_pct - prev_hp_pct
                expected_diff = cfg.CULTIVATION_BOOST_ATK_PCT / 100.0
                self.assertAlmostEqual(diff_atk_pct, expected_diff, places=9,
                    msg=f"Realm {idx}: ATK boost increment should be {expected_diff}, got {diff_atk_pct}")
                self.assertAlmostEqual(diff_hp_pct, expected_diff, places=9,
                    msg=f"Realm {idx}: HP boost increment should be {expected_diff}, got {diff_hp_pct}")
            
            prev_atk = atk
            prev_hp = hp

    def test_backward_compatibility_realm_0(self):
        """Backward compatibility: Realm 0 (Sơ nhập tiên lộ) không có boost, chỉ số giống như cũ."""
        # Ở realm 0, cultivation boost = 0%
        atk_pct_0, hp_pct_0 = core.cultivation_boost(0)
        self.assertEqual((atk_pct_0, hp_pct_0), (0, 0))
        
        # player_stats(0) không có boost => chỉ số = chỉ số cơ bản
        stats_0 = core.player_stats(0)
        expected_atk_0 = cfg.PLAYER_BASE_ATK
        expected_hp_0 = cfg.PLAYER_BASE_HP
        self.assertAlmostEqual(stats_0["atk"], expected_atk_0)
        self.assertAlmostEqual(stats_0["hp"], expected_hp_0)

    def test_no_double_stacking(self):
        """Kiểm tra: Cultivation boost KHÔNG cộng dồn với bonus từ Căn cơ/Danh hào/Đạo tâm."""
        # Tạo state với nhiều bonus
        bonus = core.stat_bonuses(words=5000, answers=5000, streak=180, honor_code="so_nhap_tien_lo")
        
        # Tính stats ở realm 5 với bonus
        stats_with_bonus = core.player_stats(5, bonuses=bonus)
        
        # Tính chỉ số cơ bản boost + bonus từng bước
        atk_pct, hp_pct = core.cultivation_boost(5)
        base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** 5
        base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** 5
        boosted_base_atk = base_atk * (1 + atk_pct)
        boosted_base_hp = base_hp * (1 + hp_pct)
        
        # Chỉ số cuối = boosted_base * (1 + bonus)
        expected_atk = boosted_base_atk * (1 + bonus["atk"])
        expected_hp = boosted_base_hp * (1 + bonus["hp"])
        
        self.assertAlmostEqual(stats_with_bonus["atk"], expected_atk, places=5)
        self.assertAlmostEqual(stats_with_bonus["hp"], expected_hp, places=5)

    def test_match_modes(self):
        import game_minigames as gm
        words = [{"id": i, "hanzi": h, "pinyin": p, "meaning_vi": m}
                 for i, (h, p, m) in enumerate([("你", "nǐ", "bạn"), ("好", "hǎo", "tốt"),
                                                ("我", "wǒ", "tôi"), ("他", "tā", "anh ấy")])]
        for seed in range(50):
            modes = gm.build_match_modes(words, random.Random(seed))
            self.assertEqual(len(modes), 4)
            self.assertLessEqual(sum(m in ("ap", "ah") for m in modes.values()), 2)
            faces = [gm._right_face(w, modes[w["id"]]) for w in words]
            self.assertEqual(len(set(faces)), 4)


class DatabaseFlowTests(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        import userdb

        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch.object(userdb, "LOCAL_USER_DB", str(Path(self.tmp.name) / "u.db")),
            mock.patch.object(userdb, "_turso_config", return_value=None),
        ]
        for p in self.patches:
            p.start()
        userdb.init_schema()
        st.session_state.clear()
        st.session_state["auth_user_id"] = 1

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_craft_flow(self):
        state = core.get_state()
        self.assertEqual(state["ls"], 0)
        core.apply_changes(ls=1000, items={"r0_0": 10, "r0_1": 10, "r0_2": 10, "r0_3": 3})
        ok, _ = core.buy_recipe("thanh_phong_kiem", 0)
        self.assertTrue(ok)
        ok, msg, quality = core.craft("thanh_phong_kiem", 0, rng=random.Random(2))
        self.assertTrue(ok, msg)
        state = core.get_state()
        self.assertEqual(len(state["artifacts"]), 1)
        self.assertEqual(state["ls"], 1000 - 150 - 400)
        self.assertEqual(state["inventory"]["r0_0"], 4)
        ok, _ = core.equip(state["artifacts"][0]["id"], 0)
        self.assertTrue(ok)
        self.assertEqual(len(core.equipped_artifacts(core.get_state())), 1)
        stats = core.player_stats(0, core.equipped_artifacts(core.get_state()))
        self.assertGreater(stats["atk"], cfg.PLAYER_BASE_ATK)
        ok, _ = core.sell_artifact(state["artifacts"][0]["id"])
        self.assertTrue(ok)
        state = core.get_state()
        self.assertEqual(state["artifacts"], [])
        self.assertEqual(state["equipped"], [None, None])
        self.assertEqual(state["ls"], 1000 - 150 - 400 + 200)
        ok, _, _ = core.craft("thanh_phong_kiem", 0)
        self.assertFalse(ok)

    def test_settle_and_badges(self):
        ls, mult, badges = core.settle(10, 1.0, 60, incr={"matches_played": 10})
        self.assertEqual((ls, mult), (10, 1.0))
        self.assertIn("Sơ Nhập Thư Phòng", badges)
        self.assertIn("Linh Thạch Học Đồ", badges)
        state = core.get_state()
        self.assertEqual(state["plays"], 1)
        self.assertGreater(state["ls"], 10)
        self.assertEqual(core.check_achievements(60), [])

    def test_fortune(self):
        pool = [{"id": i, "hanzi": f"字{i}", "pinyin": f"zi{i}", "meaning_vi": f"nghĩa {i}"} for i in range(5)]
        word, tier = core.draw_fortune(pool, {}, gq.pick_words)
        word2, tier2 = core.draw_fortune(pool, {}, gq.pick_words)
        self.assertEqual((word["id"], tier), (word2["id"], tier2))
        core.start_fortune(word["id"], tier)
        state = core.resolve_fortune(True, 0)
        self.assertEqual(state["fortune"]["status"], "ok")
        self.assertEqual(state["streak"], 1)
        again = core.resolve_fortune(False, 0)
        self.assertEqual(again["fortune"]["status"], "ok")


class ImportToolTests(unittest.TestCase):
    def test_build_rows(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("import_hsk_vocab", Path(__file__).parent.parent / "tools" / "import_hsk_vocab.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        vi = {"hanviet": "ái", "meaning_vi": "yêu", "example_zh": "我爱你。", "example_pinyin": "wǒ ài nǐ",
              "example_vi": "Anh yêu em."}
        cache = {"words": {
            "爱": {"meta": {"traditional": "愛", "pinyin": "ài", "level": 1, "frequency": 5, "pos": []}, "vi": vi},
            "八": {"meta": {"traditional": "八", "pinyin": "bā", "level": 1, "frequency": 1, "pos": []}},
            "有": {"meta": {"traditional": "有", "pinyin": "yǒu", "level": 1, "frequency": 2, "pos": []}, "vi": vi},
        }}
        rows = mod.build_rows(cache, {"有"}, 100, 75, 4)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 100)
        self.assertEqual(rows[0][4], "Ái")
        self.assertEqual(rows[0][8], 75)
        self.assertEqual(rows[0][13], "我 ______ 你。")


if __name__ == "__main__":
    unittest.main()
