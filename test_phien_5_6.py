"""Quick test for Phien 5-6 Alchemy and Talisman minigames."""
import game_config as cfg
import game_minigames


def test_pill_recipes_structure():
    """Test that PILL_RECIPES have required fields."""
    for recipe in cfg.PILL_RECIPES:
        assert "code" in recipe, f"PILL_RECIPES missing 'code': {recipe}"
        assert "name" in recipe, f"PILL_RECIPES missing 'name': {recipe}"
        assert "min_realm" in recipe, f"PILL_RECIPES missing 'min_realm': {recipe}"
        assert "ingredients" in recipe, f"PILL_RECIPES missing 'ingredients': {recipe}"
        assert "description" in recipe, f"PILL_RECIPES missing 'description': {recipe}"
        assert "emoji" in recipe, f"PILL_RECIPES missing 'emoji': {recipe}"
    print(f"[OK] All {len(cfg.PILL_RECIPES)} PILL_RECIPES have required fields")


def test_talisman_recipes_structure():
    """Test that TALISMAN_RECIPES have required fields."""
    for recipe in cfg.TALISMAN_RECIPES:
        assert "code" in recipe, f"TALISMAN_RECIPES missing 'code': {recipe}"
        assert "name" in recipe, f"TALISMAN_RECIPES missing 'name': {recipe}"
        assert "min_realm" in recipe, f"TALISMAN_RECIPES missing 'min_realm': {recipe}"
        assert "correct_hits_needed" in recipe, f"TALISMAN_RECIPES missing 'correct_hits_needed': {recipe}"
        assert "description" in recipe, f"TALISMAN_RECIPES missing 'description': {recipe}"
    print(f"[OK] All {len(cfg.TALISMAN_RECIPES)} TALISMAN_RECIPES have required fields")


def test_recipe_prices():
    """Test that all recipes have prices."""
    for recipe in cfg.PILL_RECIPES:
        price = cfg.PILL_RECIPE_PRICES.get(recipe["code"])
        assert price is not None, f"PILL_RECIPE_PRICES missing price for {recipe['code']}"
    print(f"[OK] All PILL_RECIPES have prices in PILL_RECIPE_PRICES")
    
    for recipe in cfg.TALISMAN_RECIPES:
        price = cfg.TALISMAN_RECIPE_PRICES.get(recipe["code"])
        assert price is not None, f"TALISMAN_RECIPE_PRICES missing price for {recipe['code']}"
    print(f"[OK] All TALISMAN_RECIPES have prices in TALISMAN_RECIPE_PRICES")


def test_render_functions_exist():
    """Test that render functions exist."""
    assert hasattr(game_minigames, "render_alchemy"), "render_alchemy function not found"
    assert hasattr(game_minigames, "render_talisman"), "render_talisman function not found"
    print("[OK] render_alchemy and render_talisman functions exist")


def test_nav_entries():
    """Test that NAV has new entries."""
    from cultivation_tab import NAV
    assert "alchemy" in NAV, "NAV missing 'alchemy' entry"
    assert "talisman" in NAV, "NAV missing 'talisman' entry"
    print("[OK] NAV entries added: alchemy and talisman")


def test_unlock_keys():
    """Test that UNLOCK_KEY has new entries."""
    from cultivation_tab import UNLOCK_KEY
    assert "alchemy" in UNLOCK_KEY, "UNLOCK_KEY missing 'alchemy' entry"
    assert "talisman" in UNLOCK_KEY, "UNLOCK_KEY missing 'talisman' entry"
    assert UNLOCK_KEY["alchemy"] == "hunt", "Alchemy should unlock after hunt"
    assert UNLOCK_KEY["talisman"] == "hunt", "Talisman should unlock after hunt"
    print("[OK] UNLOCK_KEY entries correct (both unlock after hunt)")


if __name__ == "__main__":
    test_pill_recipes_structure()
    test_talisman_recipes_structure()
    test_recipe_prices()
    test_render_functions_exist()
    test_nav_entries()
    test_unlock_keys()
    print("\n[SUCCESS] All tests passed! Phien 5-6 structure is correct.")
