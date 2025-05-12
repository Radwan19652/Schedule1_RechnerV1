import json
import os
from typing import List, Dict, Set, Tuple

class Calculator:
    """Berechnet Effekte, Kosten, Verkaufspreis, Profit und Addiction."""

    BASE_PRICES: Dict[str, float] = {
        "Weed":    35.0,
        "Meth":    70.0,
        "Cocaine":150.0
    }
    INGREDIENT_PRICES: Dict[str, float] = {
        "Cuke": 2.0, "Flu Medicine": 5.0, "Gasoline": 5.0,
        "Donut": 3.0, "Energy Drink": 6.0, "Mouth Wash": 4.0,
        "Motor Oil": 6.0, "Banana": 2.0, "Chili": 7.0,
        "Iodine": 8.0, "Paracetamol": 3.0, "Viagra": 4.0,
        "Horse Semen": 9.0, "Mega Bean": 7.0, "Addy": 9.0,
        "Battery": 8.0
    }
    EFFECT_MULTIPLIERS: Dict[str, float] = {
        "Anti-Gravity": 0.54, "Athletic": 0.32, "Balding": 0.30,
        "Bright-Eyed": 0.40, "Calming": 0.10, "Calorie-Dense": 0.28,
        "Cyclopean": 0.56, "Electrifying": 0.50, "Energizing": 0.22,
        "Euphoric": 0.18, "Focused": 0.16, "Foggy": 0.36,
        "Glowing": 0.48, "Jennerising": 0.42, "Long Faced": 0.52,
        "Munchies": 0.12, "Refreshing": 0.14, "Shrinking": 0.60,
        "Slippery": 0.34, "Sneaky": 0.24, "Spicy": 0.38,
        "Thought-Provoking": 0.44, "Tropic Thunder": 0.46,
        "Zombifying": 0.58
    }
    ADDICTION_LEVELS: Dict[str, int] = {
        "Cuke":1, "Flu Medicine":4, "Gasoline":5, "Donut":1,
        "Energy Drink":6, "Mouth Wash":3, "Motor Oil":7,
        "Banana":1, "Chili":9, "Iodine":11, "Paracetamol":1,
        "Viagra":2, "Horse Semen":13, "Mega Bean":8, "Addy":12,
        "Battery":10
    }

    def __init__(self, interactions_path: str = None):
        if interactions_path is None:
            base_dir = os.path.dirname(__file__)
            interactions_path = os.path.normpath(
                os.path.join(base_dir, "..", "data", "interactions.json")
            )
        with open(interactions_path, encoding="utf-8") as f:
            self.items_data: Dict[str, Dict] = json.load(f)

    def apply_item(self, current: Set[str], item: str) -> Set[str]:
        info = self.items_data[item]
        new_effects = set(current)
        # 1) Default-Effekt nur hinzufügen, wenn vorher < 8 Effekte
        default = info["base_effect"]
        if default not in new_effects and len(new_effects) < 8:
            new_effects.add(default)
        # 2) Replacements anwenden
        for old, new in info.get("replacements", []):
            if old in new_effects:
                new_effects.remove(old)
                new_effects.add(new)
        return new_effects

    def get_combined_effects(self, sequence: List[str]) -> List[str]:
        effects: Set[str] = set()
        for item in sequence:
            effects = self.apply_item(effects, item)
        return list(effects)

    def calculate_cost(self, sequence: List[str]) -> float:
        return sum(self.INGREDIENT_PRICES[item] for item in sequence)

    def calculate_sale_price(self, effects: List[str], base: str) -> float:
        total_mult = sum(self.EFFECT_MULTIPLIERS.get(e, 0.0) for e in effects)
        return self.BASE_PRICES[base] * (1 + total_mult)

    def calculate_profit(self, effects: List[str], cost: float, base: str) -> float:
        sale = round(self.calculate_sale_price(effects, base))
        return sale - cost

    def calculate_addiction(self, sequence: List[str]) -> int:
        return sum(self.ADDICTION_LEVELS.get(item, 0) for item in sequence)
