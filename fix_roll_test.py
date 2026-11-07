#!/usr/bin/env python3
"""Cập nhật test roll technique."""

content = open('tests/test_phien_8.py', 'r', encoding='utf-8').read()

old = '''    def test_roll_technique_high_realm_high_rate(self):
        """Cảnh giới cao có tỉ lệ rơi cao."""
        rng = random.Random(0)
        # Thử 100 lần ở cảnh giới 15 (50% rơi)
        drops = sum(1 for _ in range(100) if core.roll_technique(15, rng=rng)[0] is not None)
        # Kỳ vọng ~50 lần rơi
        self.assertGreater(drops, 30)'''

new = '''    def test_roll_technique_high_realm_high_rate(self):
        """Cảnh giới cao có tỉ lệ rơi cao."""
        # Thử 1000 lần ở cảnh giới 15 (50% rơi)
        drops = 0
        for seed in range(10):
            rng = random.Random(seed)
            drops += sum(1 for _ in range(100) if core.roll_technique(15, rng=rng)[0] is not None)
        # Kỳ vọng ~500 lần rơi từ 1000 lần thử
        self.assertGreater(drops, 300)'''

content = content.replace(old, new)

with open('tests/test_phien_8.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Cap nhat test roll technique")
