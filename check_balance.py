import game_balance as balance

print('=== AFTER REBALANCING ===')
print()
report = balance.benchmark_early_game()
print('Early Game:')
print('  Player (no art):', round(report['player_no_artifact'], 2))
print('  Monster normal:', round(report['monster_normal'], 2))
print('  Ratio:', round(report['ratio_no_art'], 2), '<- should be 0.8-1.2')
print()

report = balance.benchmark_mid_game()
print('Mid Game:')
print('  Player (with art):', round(report['player_with_artifact'], 2))
print('  Elite:', round(report['monster_elite'], 2))
print('  Ratio:', round(report['ratio_with_art'], 2), '<- should be 0.9-1.2')
print()

report = balance.benchmark_end_game()
print('End Game:')
print('  Player (with art):', round(report['player_with_artifact'], 2))
print('  Elite:', round(report['monster_elite'], 2))
print('  Ratio:', round(report['ratio_with_art'], 2), '<- should be 0.9-1.2')
