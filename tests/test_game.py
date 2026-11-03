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
        recipe = cfg.RECIPE_BY_CODE["lk1"]
        self.assertEqual(core.recipe_craft_cost(recipe), 400)
        self.assertEqual(core.recipe_price(recipe), 150)
        for recipe in cfg.RECIPES:
            mats = core.recipe_materials(recipe)
            self.assertTrue(mats)
            for code, _ in mats:
                self.assertIn(code, cfg.ITEMS)

    def test_combat_math(self):
        hp, atk = game_hunt.monster_stats(0)
        self.assertAlmostEqual(hp, cfg.PLAYER_BASE_ATK * cfg.MONSTER_HITS)
        dmg = game_hunt.hit_damage(1000, 5, hp, cfg.MONSTER_MIN_HITS, random.Random(1))
        self.assertLessEqual(dmg, hp / cfg.MONSTER_MIN_HITS + 1)
        loot = game_hunt.roll_loot(2, True, random.Random(3))
        self.assertTrue(all(code.startswith("r2_") for code in loot))
        self.assertEqual(game_hunt.scale_loot({"r0_0": 3}, 0, random.Random(1)), {})

    def test_map_svg(self):
        svg = game_hunt.build_map_svg([0, 1], 0)
        self.assertIn("<svg", svg)
        self.assertGreaterEqual(svg.count("<polygon points"), cfg.REGION_COUNT)


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
        ok, _ = core.buy_recipe("lk1", 0)
        self.assertTrue(ok)
        ok, msg, quality = core.craft("lk1", 0, rng=random.Random(2))
        self.assertTrue(ok, msg)
        state = core.get_state()
        self.assertEqual(len(state["artifacts"]), 1)
        self.assertEqual(state["ls"], 1000 - 150 - 400)
        self.assertEqual(state["inventory"]["r0_0"], 4)
        ok, _ = core.equip(state["artifacts"][0]["id"], 0)
        self.assertTrue(ok)
        self.assertIsNotNone(core.equipped_artifact(core.get_state()))
        ok, _, _ = core.craft("lk1", 0)
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
