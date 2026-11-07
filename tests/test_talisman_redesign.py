import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import game_config as cfg
import game_core as core
import game_hunt
from streamlit.testing.v1 import AppTest
from userdb import LocalConnection, SCHEMA


def _render_test_game():
    import streamlit as st
    import game_minigames

    pool = [{"id": i, "hanzi": chr(0x4e00 + i), "pinyin": ""} for i in range(4)]
    ctx = {"pool": pool, "words": 4, "idx": 0}
    if st.session_state.get("test_game") == "alchemy":
        game_minigames.render_alchemy(ctx)
    else:
        game_minigames.render_talisman(ctx)


class TalismanRedesignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = LocalConnection(str(Path(self.tmp.name) / "test.db"))
        self.db.batch([(sql, ()) for sql in SCHEMA])
        self.db.execute("INSERT INTO game_profile (user_id, linh_thach) VALUES (1, 10000)")
        self.patch_db = mock.patch("game_core.get_user_db", return_value=self.db)
        self.patch_db.start()

    def tearDown(self):
        self.patch_db.stop()
        self.db.close()
        self.tmp.cleanup()

    def test_recipe_design(self):
        expected = [
            ("Liệt Diễm Phù", 0, 5, 3, True, 0, 50),
            ("Lôi Thần Phù", 2, 7, 5, True, 0, 200),
            ("Hàng Yêu Diệt Ma Phù", 5, 10, 8, True, 0, 600),
            ("Tru Hồn Trảm Phách Phù", 8, 14, 10, False, 1, 1200),
            ("Thiên Địa Tru Tiên Phù", 5, 18, 12, False, 1, 2000),
            ("Hỗn Độn Tạo Hóa Phù", 5, 25, 18, False, 1, 3500),
        ]
        for recipe, (name, realm, hits, damage, boss, shield, price) in zip(cfg.TALISMAN_RECIPES, expected):
            self.assertEqual((recipe["name"], recipe["min_realm"], recipe["correct_hits_needed"]),
                             (name, realm, hits))
            self.assertEqual(recipe["effects"], {"damage_pct": damage, "boss_only": boss, "shield": shield})
            self.assertEqual(cfg.TALISMAN_RECIPE_PRICES[recipe["code"]], price)
        self.assertEqual(len(cfg.TALISMAN_RECIPES), 6)

    def test_purchase_craft_and_remove_legacy(self):
        self.db.execute("INSERT INTO game_talisman_recipes VALUES (1, 'talisman_1')")
        self.db.execute("INSERT INTO game_talismans VALUES (1, 'talisman_1', 3)")
        self.assertEqual(core.get_talisman_recipes_owned(1), [])
        self.assertEqual(core.get_talismans_inventory(1), [])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM game_talisman_recipes").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM game_talismans").fetchone()[0], 0)
        ok, _, balance = core.buy_talisman_recipe(1, "seal_1")
        self.assertTrue(ok)
        self.assertEqual(balance, 9950)
        self.assertEqual(self.db.execute("SELECT linh_thach FROM game_profile WHERE user_id = 1").fetchone()[0], 9950)
        self.assertFalse(core.buy_talisman_recipe(1, "seal_1")[0])
        self.assertTrue(core.craft_talisman(1, "seal_1", 4)["success"])
        self.assertEqual(core.get_talisman_inventory_qty(1, "seal_1"), 1)
        core.buy_talisman_recipe(1, "seal_4")
        self.assertEqual(core.craft_talisman(1, "seal_4", 4)["error"], "REALM_TOO_LOW")

    def test_word_cycle_persists_across_draws_and_pool_changes(self):
        pool = [{"id": i, "hanzi": str(i)} for i in range(4)]
        rng = random.Random(12)
        first = core.talisman_word(1, "zh", pool, rng=rng)
        self.assertEqual(first, core.talisman_word(1, "zh", pool, rng=rng))
        visited = [first["id"]]
        for _ in range(3):
            visited.append(core.talisman_word(1, "zh", pool, advance=True, rng=rng)["id"])
        self.assertEqual(set(visited), {0, 1, 2, 3})
        added = pool + [{"id": 4, "hanzi": "4"}]
        self.assertEqual(core.talisman_word(1, "zh", added, advance=True, rng=rng)["id"], 4)
        self.assertIn(core.talisman_word(1, "zh", added, advance=True, rng=rng)["id"], range(5))
        self.assertEqual(core.talisman_word(1, "en", pool, rng=rng)["id"],
                         core.talisman_word(1, "en", pool, rng=rng)["id"])



    def test_battle_damage_shields_limit_and_boss_restriction(self):
        for code in ("seal_1", "seal_4"):
            self.db.execute("INSERT INTO game_talismans VALUES (1, ?, 3)", (code,))
        b = {"stage": "fight", "over": None, "monster": {"boss": False, "hp": 100, "name": "quái"},
             "base_atk": 100, "php": 100, "shield": 0, "taken": 0, "log": []}
        with mock.patch.object(game_hunt.st, "session_state", {"g_battle": b}), \
             mock.patch.object(core, "current_user_id", return_value=1), \
             mock.patch.object(game_hunt.st, "toast"):
            game_hunt._use_talisman("seal_1", {"idx": 0})
            self.assertEqual(core.get_talisman_inventory_qty(1, "seal_1"), 3)
            game_hunt._use_talisman("seal_4", {"idx": 0})
            self.assertEqual(b["monster"]["hp"], 90)
            game_hunt._use_talisman("seal_4", {"idx": 0})
            self.assertEqual(b["monster"]["hp"], 80)
            game_hunt._use_talisman("seal_4", {"idx": 0})
            self.assertEqual(core.get_talisman_inventory_qty(1, "seal_4"), 1)
            game_hunt._monster_strikes(b, 20, "quái")
            game_hunt._monster_strikes(b, 20, "quái")
            self.assertEqual(b["php"], 100)
            game_hunt._monster_strikes(b, 20, "quái")
            self.assertEqual(b["php"], 80)

    def test_talisman_kills_boss_and_settles(self):
        self.db.execute("INSERT INTO game_talismans VALUES (1, 'seal_1', 1)")
        b = {"stage": "fight", "over": None, "monster": {"boss": True, "hp": 2, "name": "boss"},
             "base_atk": 100, "log": []}
        with mock.patch.object(game_hunt.st, "session_state", {"g_battle": b}), \
             mock.patch.object(core, "current_user_id", return_value=1), \
             mock.patch.object(game_hunt, "_settle_battle") as settle:
            game_hunt._use_talisman("seal_1", {"idx": 0})
            self.assertEqual(b["over"], "win")
            self.assertEqual(b["monster"]["hp"], 0)
            settle.assert_called_once()

    def test_talisman_ui_five_correct_answers_and_wrong_answer(self):
        core.buy_talisman_recipe(1, "seal_1")
        with mock.patch.object(core, "get_user_db", side_effect=lambda: LocalConnection(str(Path(self.tmp.name) / "test.db"))), \
             mock.patch.object(core, "current_user_id", return_value=1), \
             mock.patch.object(core, "get_state", return_value={"ls": 9950}), \
             mock.patch("game_minigames.game_ui.speak"):
            app = AppTest.from_function(_render_test_game).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox[0].value, "seal_1")
            app.text_input[0].set_value("错")
            next(b for b in app.button if b.label == "Xác nhận").click().run()
            self.assertEqual(core.get_talisman_inventory_qty(1, "seal_1"), 0)
            for _ in range(5):
                pool = [{"id": i, "hanzi": chr(0x4e00 + i), "pinyin": ""} for i in range(4)]
                word = core.talisman_word(1, "zh", pool)
                app.text_input[0].set_value(word["hanzi"])
                next(b for b in app.button if b.label == "Xác nhận").click().run()
                self.assertFalse(app.exception)
            self.assertEqual(core.get_talisman_inventory_qty(1, "seal_1"), 1)



if __name__ == "__main__":
    unittest.main()
