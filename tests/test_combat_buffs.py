import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest

import game_config as cfg
import game_core as core
import game_hunt as hunt
import game_questions as gq
import techniques_ui
from userdb import LocalConnection, SCHEMA


def talisman_page():
    import game_minigames
    pool = [{"id": i, "hanzi": chr(0x4e00 + i), "pinyin": "UNIQUE_PINYIN"} for i in range(4)]
    game_minigames.render_talisman({"idx": 0, "pool": pool, "words": 4})


class CombatBuffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "user.db")
        self.db = LocalConnection(self.path)
        self.db.batch([(sql, ()) for sql in SCHEMA])
        self.db.execute("INSERT INTO game_profile (user_id, linh_thach) VALUES (?, ?)", (123, 1000))
        self.db_patch = mock.patch.object(core, "get_user_db", return_value=self.db)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.db.close()
        self.tmp.cleanup()

    def test_battle_input_hanzi_pinyin_and_wrong(self):
        word = {"hanzi": "你好", "pinyin": "nǐ hǎo"}
        for value in ("你好", "  你好  ", "nǐ hǎo", "nihao", "ni3 hao3", "NIHAO"):
            self.assertTrue(gq.check_hanzi_or_pinyin(value, word), value)
        for value in ("再见", "再见nihao", "你好x", "", "niha"):
            self.assertFalse(gq.check_hanzi_or_pinyin(value, word), value)
        for value in ("lǜ", "lü4", "lv4", "lu"):
            self.assertTrue(gq.check_hanzi_or_pinyin(value, {"hanzi": "绿", "pinyin": "lǜ"}), value)

    def test_actual_battle_callback_reads_ime_hanzi(self):
        word = {"id": 1, "hanzi": "你好", "pinyin": "nǐ hǎo", "meaning_vi": "xin chào"}
        q = gq.make_question(word, [word], qtype="pinyin")
        for answer, expected in (("你好", True), ("ni3 hao3", True), ("再见", False)):
            b = {"q": q, "over": None, "stage": "fight", "total": 0, "correct": 0, "results": [],
                 "monster": {"hp": 1000, "max": 1000, "atk": 20, "boss": False, "name": "quái"},
                 "php": 100, "patk": 50, "combo": 0, "shield": 0, "taken": 0, "log": []}
            session = {"g_battle": b, "pin_1": answer}
            with mock.patch.object(hunt.st, "session_state", session), \
                 mock.patch.object(hunt, "_next_question"):
                hunt._answer(None, {}, "pin_1")
                self.assertEqual(b["results"], [(1, expected)])
                self.assertEqual(b["php"] == 100, expected)
                self.assertEqual(b["monster"]["hp"] < 1000, expected)

    def test_all_percentage_buffs_use_same_base(self):
        idx = 4
        artifacts = [{"recipe_code": "thanh_phong_kiem", "quality": 1, "upgrade": 2},
                     {"recipe_code": "ho_tam_kinh", "quality": 0, "upgrade": 1}]
        bonuses = core.stat_bonuses(words=500, answers=1000, honor_code=cfg.HONOR_TITLES[0]["code"])
        techniques = [{"dantian_row": 0, "dantian_col": 0, "atk_mult": .20, "hp_mult": .10},
                      {"dantian_row": 1, "dantian_col": 1, "atk_mult": .05, "hp_mult": .02},
                      {"dantian_row": -1, "dantian_col": -1, "atk_mult": .8, "hp_mult": .8}]
        stats = core.player_stats(idx, artifacts, bonuses, techniques)
        atk_flat, atk_pct = core.artifact_bonus(cfg.RECIPE_BY_CODE[artifacts[0]["recipe_code"]], 1, 2)
        hp_flat, hp_pct = core.artifact_bonus(cfg.RECIPE_BY_CODE[artifacts[1]["recipe_code"]], 0, 1)
        cult_atk, cult_hp = core.cultivation_boost(idx)
        base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
        base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
        self.assertAlmostEqual(stats["atk"], base_atk * (1 + cult_atk + bonuses["atk"] + .25 + atk_pct) + atk_flat)
        self.assertAlmostEqual(stats["hp"], base_hp * (1 + cult_hp + bonuses["hp"] + .12 + hp_pct) + hp_flat)
        self.assertEqual(stats["crit"], bonuses["crit"])

    def test_buff_and_crit_not_capped_by_monster_hp(self):
        base, _ = hunt.hit_damage(100, 2, 100, 18, random.Random(7), crit=0)
        boosted, _ = hunt.hit_damage(150, 2, 100, 18, random.Random(7), crit=0)
        critical, is_crit = hunt.hit_damage(150, 2, 100, 18, random.Random(7), crit=1)
        self.assertAlmostEqual(boosted, base * 1.5)
        self.assertAlmostEqual(critical, boosted * cfg.CRIT_MULT)
        self.assertTrue(is_crit)
        self.assertGreater(base, 100 / 18)

    def test_actual_battle_reads_active_profile_techniques(self):
        secret = next(t for t in cfg.TECHNIQUES if t["atk_mult"] > 0)
        heart = next(t for t in cfg.TECHNIQUES if t["hp_mult"] > 0)
        for uid, tech, row in ((123, secret, 0), (123, heart, -1), (456, secret, 0)):
            self.db.execute("INSERT INTO game_techniques (user_id, technique_code, dantian_row, dantian_col) "
                            "VALUES (?, ?, ?, ?)", (uid, tech["code"], row, row))
        state = {"fortune": None, "artifacts": [], "equipped": []}
        ctx = {"idx": 0, "bonuses": {"atk": .1, "hp": .2}, "pool": [], "mastery": {}, "grammar": False}
        with mock.patch.object(core, "current_user_id", return_value=123), \
             mock.patch.object(core, "get_state", return_value=state), \
             mock.patch.object(hunt, "_next_question"):
            class Session(dict):
                __setattr__ = dict.__setitem__
            session = Session()
            with mock.patch.object(hunt.st, "session_state", session):
                hunt.start_battle(0, "normal", ctx)
            battle = session["g_battle"]
            self.assertAlmostEqual(battle["patk"], cfg.PLAYER_BASE_ATK * (1.1 + secret["atk_mult"]))
            self.assertAlmostEqual(battle["pmax"], cfg.PLAYER_BASE_HP * 1.2)
            self.assertEqual(techniques_ui.current_user_id(), 123)

    def test_talisman_does_not_show_pinyin(self):
        core.buy_talisman_recipe(123, "seal_1")
        with mock.patch.object(core, "get_user_db", side_effect=lambda: LocalConnection(self.path)), \
             mock.patch.object(core, "current_user_id", return_value=123), \
             mock.patch.object(core, "get_state", return_value={"ls": 950}), \
             mock.patch("game_minigames.game_ui.speak"):
            app = AppTest.from_function(talisman_page).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox[0].value, "seal_1")
            self.assertEqual(len(app.text_input), 1)
            self.assertTrue(any("font-size:64px" in x.value for x in app.markdown))
            self.assertNotIn("UNIQUE_PINYIN", " ".join(x.value for x in app.markdown))


if __name__ == "__main__":
    unittest.main()
