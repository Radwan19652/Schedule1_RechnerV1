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
        if allowed_ingredients and len(allowed_ingredients) > 0:
            # Nur erlaubte Zutaten verwenden, die auch im Calculator existieren
            ingredients = [ing for ing in allowed_ingredients 
                        if ing in self.calc.INGREDIENT_PRICES]
        else:
            # Wenn keine Zutaten gewählt wurden, alle verfügbaren verwenden
            ingredients = list(self.calc.INGREDIENT_PRICES.keys())

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
                
                # Prüfe, ob diese Lösung besser ist als die bisherige
                is_better = False
                if optimize_for == "cost":
                    is_better = (best_seq == [] or total_cost < best_cost)
                else:  # "profit"
                    is_better = (best_seq == [] or total_profit > best_profit)
                    
                if is_better:
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
                
                # Bonus für gewünschte Effekte
                effect_bonus = 0.0
                if desired_effects:
                    # Zähle, wie viele der gewünschten Effekte enthalten sind
                    matched_effects = sum(1 for e in desired_effects if e in new_eff)
                    effect_bonus = matched_effects * 10.0  # Bonus pro gefundenem Effekt
                
                if optimize_for == "cost":
                    # Bei "cost" optimieren wir auf minimale Kosten
                    h = 0.0  # Keine Heuristik für Kosten
                    f_new = cost - effect_bonus  # Je kleiner, desto besser, mit Bonus für Effekte
                    g_new = cost
                else:  # "profit" (default)
                    # Bei "profit" optimieren wir auf maximalen Profit 
                    h = sum(yields_only[:steps_left]) if steps_left > 0 else 0.0
                    f_new = -(prof + h + effect_bonus)  # Mit Bonus für Effekte
                    g_new = -(prof + effect_bonus)
                
                heapq.heappush(open_list, (f_new, g_new, new_seq, new_eff))

        return best_seq, best_eff, best_cost, best_profit
    
    def find_best_sequence(
        self,
        desired_effects: List[str],
        optimize_for: str,
        base: str,
        min_steps: int,
        max_steps: int,
        allowed_ingredients: Optional[List[str]],
        timeout: float,
        abort_callback: Optional[Callable[[], bool]] = None
    ) -> Tuple[List[str], List[str], float, float]:
        """
        Führt find_sequence für jede Tiefe von min_steps bis max_steps aus
        und liefert das profitabelste Ergebnis.
        """
        start = time.time()
        abort = abort_callback or (lambda: False)

        best_profit = float("-inf")
        best_seq: List[str] = []
        best_eff: List[str] = []
        best_cost = 0.0

        for depth in range(min_steps, max_steps + 1):
            if abort():
                break
            elapsed = time.time() - start
            if elapsed >= timeout:
                break
            remaining = timeout - elapsed

            seq, eff, cost, profit = self.find_sequence(
                desired_effects=desired_effects,
                optimize_for=optimize_for,
                base=base,
                min_steps=depth,
                max_steps=depth,
                allowed_ingredients=allowed_ingredients,
                timeout=remaining,
                abort_callback=abort
            )

            if seq:
                if optimize_for == "cost" and (best_seq == [] or cost < best_cost):
                    best_profit, best_cost = profit, cost
                    best_seq, best_eff = seq, eff
                elif optimize_for == "profit" and (best_seq == [] or profit > best_profit):
                    best_profit, best_cost = profit, cost
                    best_seq, best_eff = seq, eff

        return best_seq, best_eff, best_cost, best_profit