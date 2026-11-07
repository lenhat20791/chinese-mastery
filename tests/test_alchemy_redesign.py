import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest

import game_alchemy as alchemy
import game_config as cfg
import game_core as core
import game_hunt
from userdb import LocalConnection, SCHEMA


def words(count):
    return [{"id": i, "hanzi": f"字{i}", "pinyin": f"pin{i}", "meaning_vi": f"nghĩa {i}"}
            for i in range(count)]


def render_alchemy_test():
    import game_alchemy
    import streamlit as st
    pool = [{"id": i, "hanzi": f"word{i}", "pinyin": f"pin{i}", "meaning_vi": f"meaning {i}"}
            for i in range(4)]
    @st.fragment
    def body():
        game_alchemy.render({"idx": 0, "pool": pool, "words": 4})
    body()


class AlchemyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "test.db")
        self.db = LocalConnection(self.path)
        self.db.batch([(sql, ()) for sql in SCHEMA])
        self.db.execute("INSERT INTO game_profile (user_id, linh_thach) VALUES (1, 10000)")
        self.patch = mock.patch.object(core, "get_user_db", return_value=self.db)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.db.close()
        self.tmp.cleanup()

    def test_exact_recipes(self):
        expected = [(0, 5, 20, .90, 50), (2, 10, 50, .85, 200),
                    (6, 20, 150, .75, 500), (9, 30, 250, .65, 1500),
                    (3, 40, 0, .50, 3000)]
        for recipe, (realm, ingredients, heal, probability, price) in zip(cfg.PILL_RECIPES, expected):
            self.assertEqual((recipe["min_realm"], recipe["ingredients"], recipe["heal"], recipe["success_rate"]),
                             (realm, ingredients, heal, probability))
            self.assertEqual(cfg.PILL_RECIPE_PRICES[recipe["code"]], price)
        self.assertEqual(len(cfg.PILL_RECIPES), 5)

    def test_board_uses_learned_and_unlearned(self):
        pool = words(20)
        board = alchemy.build_board(pool[:4], pool, random.Random(3))
        self.assertEqual(len(board["cards"]), 30)
        self.assertTrue(all(any(a["hanzi"] == w["hanzi"] for a in board["answers"]) for w in pool[:4]))
        self.assertEqual(sum(a["hanzi"] in {w["hanzi"] for w in pool[:4]} for a in board["answers"]), 4)
        board = alchemy.build_board(pool[:15], pool, random.Random(3))
        self.assertTrue(all(int(a["hanzi"][1:]) < 15 for a in board["answers"]))
        self.assertEqual(len(board["answers"]), 10)

    def test_correct_wrong_and_exhaustion(self):
        board = alchemy.build_board(words(1), words(1), random.Random(5))
        game = {"board": board, "ingredients": 0}
        for i in range(3):
            alchemy.choose_card(game, i)
        self.assertEqual(game["ingredients"], 1)
        self.assertEqual({c["status"] for c in board["cards"]}, {"done"})
        self.assertFalse(alchemy.board_has_match(board))
        board = alchemy.build_board(words(2), words(2), random.Random(1))
        game = {"board": board, "ingredients": 0}
        indexes = [next(i for i, c in enumerate(board["cards"]) if c["text"] == text)
                   for text in ("字0", "pin1", "nghĩa 0")]
        for index in indexes:
            alchemy.choose_card(game, index)
        self.assertEqual(game["ingredients"], 0)
        self.assertTrue(all(board["cards"][i]["status"] == "bad" for i in indexes))
        self.assertFalse(alchemy.board_has_match(board))

    def test_multiple_boards_keep_ingredients(self):
        game = {"board": alchemy.build_board(words(10), words(10), random.Random(1)),
                "ingredients": 0, "round": 0}
        with mock.patch.object(alchemy.st, "session_state", {"alchemy_game": game}), \
             mock.patch.object(alchemy, "all_words", return_value=words(10)), \
             mock.patch.object(alchemy, "active_variant", return_value="zh"):
            for round_number in range(2):
                board = game["board"]
                for answer in board["answers"]:
                    for kind, text in answer.items():
                        index = next(i for i, card in enumerate(board["cards"])
                                     if card["kind"] == kind and card["text"] == text and card["status"] == "idle")
                        alchemy.choose_card(game, index)
                self.assertFalse(alchemy.board_has_match(board))
                self.assertEqual(game["ingredients"], (round_number + 1) * 10)
                alchemy._new_board({"pool": words(4)})
            self.assertEqual(game["round"], 2)

    def test_purchase_legacy_removal_craft_and_thresholds(self):
        self.db.execute("INSERT INTO game_pill_recipes VALUES (1, 'pill_1')")
        self.db.execute("INSERT INTO game_pills VALUES (1, 'pill_1', 9)")
        self.assertEqual(core.get_pill_recipes_owned(1), [])
        self.assertEqual(core.get_pills_inventory(1), [])
        for recipe in cfg.PILL_RECIPES:
            code, realm, need = recipe["code"], recipe["min_realm"], recipe["ingredients"]
            self.assertTrue(core.buy_pill_recipe(code, 1, 10000)[0])
            self.assertFalse(core.buy_pill_recipe(code, 1, 10000)[0])
            if realm:
                self.assertFalse(core.craft_pill(code, 1, realm - 1, need)[0])
            self.assertFalse(core.craft_pill(code, 1, realm, need - 1)[0])
            for roll, expected in ((recipe["success_rate"] - .001, True), (recipe["success_rate"], False)):
                self.assertEqual(core.craft_pill(code, 1, realm, need,
                                                 rng=mock.Mock(random=lambda: roll))[0], expected)
            self.assertEqual(core.get_pill_inventory_qty(1, code), 1)

    def test_heal_and_revival_preserves_battle(self):
        core.add_pill(1, "elixir_1", 1)
        core.add_pill(1, "elixir_5", 1)
        b = {"php": 95, "pmax": 100, "over": None, "monster": {"hp": 70, "atk": 200, "name": "quái"},
             "shield": 0, "taken": 0, "log": [], "combo": 0, "player_realm": 3}
        ok, _ = core.use_pill_in_battle(b, "elixir_1", 1, 0)
        self.assertTrue(ok)
        self.assertEqual(b["php"], 100)
        self.assertEqual(core.get_pill_inventory_qty(1, "elixir_1"), 0)
        with mock.patch.object(core, "current_user_id", return_value=1):
            game_hunt._fight_turn(b, False, "đáp án")
        self.assertTrue(b["revive_pending"])
        self.assertIsNone(b["over"])
        self.assertEqual(b["monster"]["hp"], 70)
        self.assertTrue(core.use_revival_pill(1, b)[0])
        self.assertEqual(b["php"], 50)
        self.assertFalse(b["revive_pending"])
        self.assertEqual(b["monster"]["hp"], 70)
        self.assertEqual(core.get_pill_inventory_qty(1, "elixir_5"), 0)

    def test_healing_requires_realm_and_never_wastes_pill(self):
        for recipe in cfg.PILL_RECIPES[:4]:
            code, realm = recipe["code"], recipe["min_realm"]
            core.add_pill(1, code, 1)
            b = {"php": 1, "pmax": 1000}
            if realm:
                self.assertFalse(core.use_pill_in_battle(b, code, 1, realm - 1)[0])
                self.assertEqual(core.get_pill_inventory_qty(1, code), 1)
            self.assertTrue(core.use_pill_in_battle(b, code, 1, realm)[0])
            self.assertEqual(b["php"], 1 + recipe["heal"])
        core.add_pill(1, "elixir_1", 1)
        self.assertFalse(core.use_pill_in_battle({"php": 100, "pmax": 100}, "elixir_1", 1, 0)[0])
        self.assertEqual(core.get_pill_inventory_qty(1, "elixir_1"), 1)

    def test_revival_choice_advances_or_settles_without_resetting_run(self):
        core.add_pill(1, "elixir_5", 1)
        b = {"php": 0, "pmax": 120, "revive_pending": True, "player_realm": 3,
             "monster": {"hp": 42}, "loot": {"r0_0": 2}, "log": [], "over": None}
        session = {"g_battle": b, "g_run": {"wins": 3}}
        with mock.patch.object(game_hunt.st, "session_state", session), \
             mock.patch.object(core, "current_user_id", return_value=1), \
             mock.patch.object(game_hunt, "_next_question") as next_question:
            game_hunt._revive({"idx": 3})
            next_question.assert_called_once()
            self.assertEqual(b["php"], 60)
            self.assertEqual(b["monster"]["hp"], 42)
            self.assertEqual(b["loot"], {"r0_0": 2})
            self.assertEqual(session["g_run"], {"wins": 3})
        b["revive_pending"] = True
        with mock.patch.object(game_hunt.st, "session_state", session), \
             mock.patch.object(game_hunt, "_settle_battle") as settle:
            game_hunt._decline_revival({"idx": 3})
            self.assertEqual(b["over"], "lose")
            settle.assert_called_once()

    def test_no_revival_without_eligible_pill_and_quality_pill_is_untouched(self):
        core.add_inventory(1, "pham_dan", 1)
        core.add_pill(1, "elixir_5", 1)
        b = {"php": 1, "pmax": 100, "over": None, "monster": {"hp": 70, "atk": 200, "name": "quái"},
             "shield": 0, "taken": 0, "log": [], "combo": 0, "player_realm": 2}
        with mock.patch.object(core, "current_user_id", return_value=1):
            game_hunt._fight_turn(b, False, "đáp án")
        self.assertEqual(b["over"], "lose")
        self.assertFalse(b.get("revive_pending", False))
        self.assertEqual(core.get_pill_inventory_qty(1, "elixir_5"), 1)
        self.assertEqual(core.get_inventory_qty(1, "pham_dan"), 1)

    def test_ui_matching_crafting_and_result_dialog(self):
        core.buy_pill_recipe("elixir_1", 1, 10000)
        with mock.patch.object(core, "get_user_db", side_effect=lambda: LocalConnection(self.path)), \
             mock.patch.object(core, "current_user_id", return_value=1), \
             mock.patch.object(core, "get_state", return_value={"ls": 9950}), \
             mock.patch.object(alchemy, "all_words", return_value=[
                 {"id": i, "hanzi": f"word{i}", "pinyin": f"pin{i}", "meaning_vi": f"meaning {i}"}
                 for i in range(10)]), \
             mock.patch.object(core.random, "random", return_value=0):
            app = AppTest.from_function(render_alchemy_test).run()
            self.assertFalse(app.exception)
            next(b for b in app.button if b.label == "▶️ Bắt đầu").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(next(b for b in app.button if b.label == "⚗️ Luyện đan").disabled)
            for answer in app.session_state["alchemy_game"]["board"]["answers"][:5]:
                for kind, text in answer.items():
                    board = app.session_state["alchemy_game"]["board"]
                    index = next(i for i, c in enumerate(board["cards"])
                                 if c["kind"] == kind and c["text"] == text and c["status"] == "idle")
                    next(b for b in app.button if b.key == f"alchemy_card_0_{index}").click().run()
                    self.assertFalse(app.exception)
            self.assertFalse(next(b for b in app.button if b.label == "⚗️ Luyện đan").disabled)
            next(b for b in app.button if b.label == "⚗️ Luyện đan").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(core.get_pill_inventory_qty(1, "elixir_1"), 1)
            self.assertTrue(any("thành công" in element.value for element in app.success))

    def test_ui_failure_dialog_resets_ingredients(self):
        core.buy_pill_recipe("elixir_1", 1, 10000)
        with mock.patch.object(core, "get_user_db", side_effect=lambda: LocalConnection(self.path)), \
             mock.patch.object(core, "current_user_id", return_value=1), \
             mock.patch.object(core, "get_state", return_value={"ls": 9950}), \
             mock.patch.object(alchemy, "all_words", return_value=words(10)), \
             mock.patch.object(core.random, "random", return_value=0.99):
            app = AppTest.from_function(render_alchemy_test).run()
            next(b for b in app.button if b.label == "▶️ Bắt đầu").click().run()
            app.session_state["alchemy_game"]["ingredients"] = 5
            app.run()
            next(b for b in app.button if b.label == "⚗️ Luyện đan").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("thất bại" in element.value for element in app.error))
            self.assertEqual(core.get_pill_inventory_qty(1, "elixir_1"), 0)
            self.assertIsNone(app.session_state.filtered_state.get("alchemy_game"))


if __name__ == "__main__":
    unittest.main()
