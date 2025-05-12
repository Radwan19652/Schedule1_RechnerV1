# schedule1/search_engine.py

import time
import heapq
from typing import List, Tuple, Optional, Callable, Set, Dict

from .calculator import Calculator

class SearchEngine:
    """
    SearchEngine implementiert eine A*-Suche über Misch-Sequenzen.
    Sie nutzt intern die Calculator-Klasse, um Effekte, Kosten, Verkaufspreis
    und Profit zu berechnen.
    """

    def __init__(self, calculator: Calculator):
        self.calc = calculator

    def find_sequence(
        self,
        desired_effects: List[str],
        optimize_for: str = "profit",
        base: str = "Meth",
        min_steps: int = 1,
        max_steps: int = 5,
        allowed_ingredients: Optional[List[str]] = None,
        timeout: float = 30.0,
        abort_callback: Optional[Callable[[], bool]] = None
    ) -> Tuple[List[str], List[str], float, float]:
        """
        Führt eine A*-Suche durch und gibt die beste Sequenz zurück:

        :param desired_effects: Effekte, die mindestens erreicht werden sollen (derzeit nicht aktiv gefiltert).
        :param optimize_for: "profit" oder "cost" (derzeit nur "profit" unterstützt).
        :param base: Basisprodukt für die Preisberechnung.
        :param min_steps: Minimale Schrittzahl (wird als Tiefe ignoriert, da A* immer max_steps sucht).
        :param max_steps: Exakte Anzahl Schritte, die die Sequenz haben soll.
        :param allowed_ingredients: Wenn gesetzt, reguliert die erlaubten Zutaten.
        :param timeout: Maximale Laufzeit in Sekunden (global).
        :param abort_callback: Funktion, die bei True die Suche abbricht.
        :return: (seq, final_effects, total_cost, total_profit)
        """
        start = time.time()
        abort_callback = abort_callback or (lambda: False)

        # Zutatenliste vorbereiten
        ingredients = allowed_ingredients or list(self.calc.items_data.keys())

        # Einzel-Ertrag für Heuristik berechnen
        profit_yields: List[Tuple[float,str]] = []
        for item in ingredients:
            effs = self.calc.apply_item(set(), item)
            sale = self.calc.calculate_sale_price(list(effs), base)
            cost = self.calc.INGREDIENT_PRICES[item]
            profit_yields.append((sale - cost, item))
        profit_yields.sort(key=lambda x: x[0], reverse=True)
        yields_only = [p for p,_ in profit_yields]

        # A*-Priority-Queue initialisieren
        # Eintrag: (f = -(prof + h), g_neg=-prof, seq, effects_set)
        open_list: List[Tuple[float,float,List[str],Set[str]]] = [
            (0.0, 0.0, [], set())
        ]
        closed: Set[Tuple[frozenset,int]] = set()

        best_seq: List[str] = []
        best_eff: List[str] = []
        best_profit: float = float("-inf")
        best_cost: float = 0.0

        while open_list:
            # globaler Abbruch?
            if abort_callback():
                break
            if time.time() - start > timeout:
                break

            f, g_neg, seq, effects = heapq.heappop(open_list)
            current_profit = -g_neg
            depth = len(seq)

            # Zieltest: tiefe erreicht
            if depth == max_steps:
                total_sale = self.calc.calculate_sale_price(list(effects), base)
                total_cost = self.calc.calculate_cost(seq)
                total_profit = total_sale - total_cost
                best_seq, best_eff = seq, list(effects)
                best_profit, best_cost = total_profit, total_cost
                break

            state = (frozenset(effects), depth)
            if state in closed:
                continue
            closed.add(state)

            # expandieren
            for item in ingredients:
                new_seq = seq + [item]
                new_eff = self.calc.apply_item(effects, item)
                cost = self.calc.calculate_cost(new_seq)
                sale = self.calc.calculate_sale_price(list(new_eff), base)
                prof = sale - cost

                steps_left = max_steps - len(new_seq)
                h = sum(yields_only[:steps_left]) if steps_left > 0 else 0.0

                f_new = -(prof + h)
                g_new = -prof

                heapq.heappush(open_list, (f_new, g_new, new_seq, new_eff))

        return best_seq, best_eff, best_cost, best_profit
