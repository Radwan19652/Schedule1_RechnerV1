
import time
import cProfile
import pstats
import io
from tkinter import StringVar, Listbox, Text, BooleanVar, Checkbutton, LEFT, RIGHT, BOTH, X, Y, WORD, END
import ttkbootstrap as tb
import logging
from schedule1.calculator    import Calculator
from schedule1.search_engine import SearchEngine
from multiprocessing import Process, Queue
from typing import Dict
def run_search_process(
    search_engine,
    desired_effects,
    optimize_for,
    base,
    min_steps,
    max_steps,
    allowed_ingredients,
    timeout,
    enable_profiling,
    result_queue,
    progress_queue
):
    """
    Führt für jede Tiefe eine einzelne A*-Suche durch,
    pusht Zwischenergebnisse in progress_queue und
    liefert am Ende das beste Ergebnis + Profiling in result_queue.
    """
    start = time.time()
    best_profit = float("-inf")
    best_seq: list = []
    best_eff: list = []
    best_cost = 0.0
    # Dict zum Speichern der Laufzeiten pro Tiefe
    times: Dict[int, float] = {}
    # Profiler nur bei Bedarf anlegen
    if enable_profiling:
        profiler = cProfile.Profile()
        profiler.enable()
    else:
        profiler = None

    # Loop über alle Tiefen
    for depth in range(min_steps, max_steps + 1):
        elapsed = time.time() - start
        if elapsed >= timeout:
            break
        remaining = timeout - elapsed
        # Zeitmessung für diese Tiefe starten
        deph_start = time.time()

        # Eine Tiefe durchsuchen
        seq, eff, cost, profit = search_engine.find_sequence(
            desired_effects=desired_effects,
            optimize_for=optimize_for,
            base=base,
            min_steps=depth,
            max_steps=depth,
            allowed_ingredients=allowed_ingredients,
            timeout=remaining,
            abort_callback=lambda: False
        )

        # Zwischenergebnis + Rest-Timeout melden
        progress_queue.put((depth, profit, seq, remaining))
        # Laufzeit dieser Tiefe messen und melden
        depth_time = time.time() - deph_start
        times[depth] = depth_time
        progress_queue.put(depth_time)

        # Bestes Ergebnis merken
        if seq and profit > best_profit:
            best_profit, best_cost = profit, cost
            best_seq, best_eff = seq, eff

    # Profiling beenden und Output puffern
    if profiler:
        profiler.disable()
        buf = io.StringIO()
        stats = pstats.Stats(profiler, stream=buf).sort_stats("cumtime")
        stats.print_stats(10)
        profiling_output = buf.getvalue()
    else:
        profiling_output = ""

    # 1) Endergebnis
    result_queue.put((best_seq, best_eff, best_cost, best_profit))
    # 2) Profiling-Output (leer, wenn Profiling deaktiviert)
    result_queue.put(profiling_output)
    # 3) Zeiten pro Tiefe (immer)
    result_queue.put(times)
    # 4) Zeit-Verhältnisse nur bei Profiling
    if enable_profiling:
        ratios = {
            d: times[d] / times[d-1]
            for d in times
            if (d-1) in times
        }
    else:
        ratios = {}
    result_queue.put(ratios)

# GUI-Klasse für Schedule1
class Schedule1App:
    def __init__(self):
        # Logger initialisieren
        self.logger = logging.getLogger("schedule1")
        self.logger.setLevel(logging.INFO)
        # Calculator & SearchEngine
        self.calc = Calculator()
        self.search = SearchEngine(self.calc)
        self.abort_flag = False

        # GUI
        style = tb.Style(theme="darkly")
        self.root = style.master
        self.root.title("Schedule1 OOP")
        self.root.geometry("900x600")

        # Sidebar
        sidebar = tb.Frame(self.root, padding=10)
        sidebar.pack(side=LEFT, fill=Y)

        # Desired Effects
        tb.Label(sidebar, text="Desired Effects").pack(anchor="w")
        self.effects_lb = Listbox(sidebar, selectmode="multiple", height=8)
        for e in sorted(self.calc.items_data.keys()):
            self.effects_lb.insert(END, e)
        self.effects_lb.pack(fill=X)

        # Optimize for
        self.opt_var = StringVar(value="profit")
        tb.Radiobutton(sidebar, text="Cost", variable=self.opt_var, value="cost").pack(anchor="w")
        tb.Radiobutton(sidebar, text="Profit", variable=self.opt_var, value="profit").pack(anchor="w")

        # Mix Steps
        tb.Label(sidebar, text="Steps Min/Max").pack(anchor="w", pady=(10,0))
        frame = tb.Frame(sidebar); frame.pack(fill=X)
        self.min_sb = tb.Spinbox(frame, from_=1, to=15, width=5); self.min_sb.set(1); self.min_sb.pack(side=LEFT)
        self.max_sb = tb.Spinbox(frame, from_=1, to=15, width=5); self.max_sb.set(5); self.max_sb.pack(side=LEFT)

        # Timeout
        tb.Label(sidebar, text="Timeout (s)").pack(anchor="w", pady=(10,0))
        self.timeout_sb = tb.Spinbox(sidebar, from_=1, to=600, width=6)
        self.timeout_sb.set(30)
        self.timeout_sb.pack(fill=X)

        # Buttons
        self.find_btn = tb.Button(sidebar, text="Find", bootstyle="success", command=self.on_find)
        self.find_btn.pack(fill=X, pady=(10,0))
        self.cancel_btn = tb.Button(sidebar, text="Cancel", bootstyle="danger",
                                    command=self.on_cancel, state="disabled")
        self.cancel_btn.pack(fill=X, pady=(5,0))

        # Meters
        self.progress = tb.Meter(sidebar, amounttotal=1, amountused=0, subtext="Steps")
        self.progress.pack(fill=X, pady=5)
        self.timer    = tb.Meter(sidebar, amounttotal=1, amountused=0, subtext="Time (s)")
        self.timer.pack(fill=X)

        # Log-Panel (oben rechts) und Result-Panel (unten rechts)
        self.log_txt = Text(self.root, height=10, wrap=WORD)
        self.log_txt.pack(side=RIGHT, fill=X, pady=(10,0), padx=10)
        self.result_txt = Text(self.root, height=8, wrap=WORD)
        self.result_txt.pack(side=RIGHT, fill=BOTH, expand=1, padx=10)

        # Frame für Buttons & Checkbox
        self.control_frame = tb.Frame(self.root)
        self.control_frame.pack(fill=X, padx=10, pady=5)

        # Profiling–Toggle
        self.profile_var = BooleanVar(value=False)
        self.profile_chk = Checkbutton(
            self.control_frame,
            text="Profiling aktiv",
            variable=self.profile_var
        )
        self.profile_chk.pack(side=LEFT, padx=5)

        # Einziger Text-Handler fürs Logging in log_txt
        class TextHandler(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget
            def emit(self, record):
                msg = self.format(record)
                self.widget.after(0, lambda: (
                    self.widget.insert(END, msg+"\n"),
                    self.widget.see(END)
                ))
        th = TextHandler(self.log_txt)
        th.setFormatter(logging.Formatter("%(asctime)s — %(message)s"))
        self.logger.addHandler(th)

    def on_find(self):
        # Log-Panel leeren
        self.log_txt.delete("1.0", END)
        # Disable/Enable Buttons
        self.abort_flag = False
        self.find_btn.configure(state='disabled')
        self.cancel_btn.configure(state='normal')

        # Inputs
        min_s = int(self.min_sb.get())
        max_s = int(self.max_sb.get())
        timeout = float(self.timeout_sb.get())
        allowed = None  # oder aus einer Listbox auslesen
        base = "Meth"   # falls GUI dazu

        # Meters
        depths = max_s - min_s + 1
        self.progress.configure(amounttotal=depths, amountused=0)
        self.timer.configure(amounttotal=timeout, amountused=timeout)

        # Suche per eigenem Prozess starten
        self.search_start = time.time()
        self.find_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")

        # Ergebnis-Queue und Prozess aufsetzen
        self.result_queue = Queue()
        self.progress_queue = Queue()
        self.search_process = Process(
            target=run_search_process,
            args=(
                self.search,
                [],                 # desired_effects
                self.opt_var.get(), # optimize_for
                base,
                min_s,
                max_s,
                allowed,
                timeout,
                self.profile_var.get(), # enable_profiling
                self.result_queue,
                self.progress_queue
            ),
            daemon=True
        )
        self.search_process.start()

        # Meter-Updates alle 100 ms planen
        self.root.after(100, self._update_meter)

    def on_cancel(self):
        # Wenn ein Such-Prozess läuft, beende ihn
        if hasattr(self, "search_process") and self.search_process.is_alive():
            self.search_process.terminate()
            self.logger.info("Suche abgebrochen.")
        # Buttons zurücksetzen
        self.cancel_btn.configure(state="disabled")
        self.find_btn.configure(state="normal")
        
    def _update_meter(self):
        """
        Aktualisiert das Meter-Widget unabhängig vom Such-Loop,
        zeigt live die Tiefe-Updates im Log und am Ende das Profiling.
        """
        # 0) Alle Zwischenergebnisse aus progress_queue lesen und ins Log schreiben
        while not self.progress_queue.empty():
            # zuerst das Ergebnis, dann die Laufzeit
            depth, profit, seq, remaining = self.progress_queue.get()
            depth_time = self.progress_queue.get()
            # Meter aktualisieren
            self.progress.configure(amountused=depth)
            self.log_txt.insert(
                END,
                f"Tiefe {depth}: profit={profit:.2f}, seq={seq}, "
                f"remaining={remaining:.2f}s, time={depth_time:.3f}s\n"
            )
            self.log_txt.see(END)

        # 1) Verbleibende Zeit berechnen und Meter aktualisieren
        elapsed = time.time() - self.search_start
        remaining = max(0.0, float(self.timeout_sb.get()) - elapsed)
        self.timer.configure(amountused=remaining)

        # 2) Solange der Prozess noch läuft und Zeit übrig ist, erneut planen
        if self.search_process.is_alive() and remaining > 0:
            self.root.after(100, self._update_meter)
            return

        # 3) Jetzt ist Suche fertig oder Timeout:
        if self.search_process.is_alive():
            # Timeout: Prozess abbrechen
            self.search_process.terminate()
            self.logger.info("Timeout – Suche abgebrochen.")
        else:
            # Suche abgeschlossen: Endergebnis + Profiling aus result_queue lesen
            best_seq, best_eff, best_cost, best_profit = self.result_queue.get()
            profiling_output = self.result_queue.get()
            times            = self.result_queue.get()
            ratios           = self.result_queue.get()

            # Ergebnis auch im Haupt-Panel anzeigen
            self.result_txt.delete("1.0", END)
            self.result_txt.insert(
                END,
                f"Sequenz:       {best_seq}\n"
                f"Effekte:       {best_eff}\n"
                f"Kosten:        ${best_cost:.2f}\n"
                f"Profit:        ${best_profit:.2f}\n"
            )

            # Profiling nur anzeigen, wenn aktiviert
            if profiling_output:
                self.log_txt.insert(END, "\n--- Profiling (Top 10) ---\n" + profiling_output)
                self.log_txt.see(END)

            # Laufzeiten pro Tiefe ausgeben
            self.log_txt.insert(END, "\n--- Laufzeiten pro Tiefe (s) ---\n")
            for d in sorted(times):
                self.log_txt.insert(END, f"Tiefe {d}: {times[d]:.3f} s\n")

            # Zeit-Verhältnisse nur, wenn Profiling aktiviert
            if profiling_output:
                self.log_txt.insert(END, "\n--- Zeit-Verhältnisse (d/d-1) ---\n")
                for d in sorted(ratios):
                    self.log_txt.insert(END, f"{d}/{d-1}: {ratios[d]:.2f}\n")

            # Endergebnis ausgeben
            self.log_txt.insert(END, f"\n=== Fertig: profit={best_profit:.2f}, seq={best_seq}\n")
            self.log_txt.see(END)

        # 4) Buttons zurücksetzen
        self.find_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
