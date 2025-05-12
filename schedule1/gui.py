import threading
import time
from tkinter import StringVar, Listbox, Text, LEFT, RIGHT, BOTH, X, Y, WORD, END
import ttkbootstrap as tb
import logging
from schedule1.calculator    import Calculator
from schedule1.search_engine import SearchEngine
from schedule1.timer         import CountdownTimer
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

        # Countdown starten
        def tick(rem):
            self.timer.configure(amountused=rem)
        def done():
            self.logger.info("Timer fertig.")
        self.countdown = CountdownTimer(self.root, timeout, tick, done)
        self.countdown.start()

        # Suche im Thread
        threading.Thread(target=self._search_task,
                         args=(min_s, max_s, allowed, base, timeout),
                         daemon=True).start()

    def on_cancel(self):
        self.abort_flag = True
        self.cancel_btn.configure(state='disabled')
        self.countdown.stop()
        self.find_btn.configure(state='normal')
        self.logger.info("Abgebrochen.")

    def _search_task(self, min_s, max_s, allowed, base, timeout):
        start = time.time()
        best_seq, best_eff = [], []
        best_cost, best_profit = float("inf"), float("-inf")
        depths = max_s - min_s + 1

        for idx, depth in enumerate(range(min_s, max_s+1), start=1):
            # Abort/Timeout prüfen
            if self.abort_flag:
                self.logger.info("Abbruch durch Benutzer")
                break
            elapsed = time.time() - start
            if elapsed >= timeout:
                self.logger.info("Timeout erreicht, breche ab.")
                break
            remaining = timeout - elapsed

            # Meter updaten
            self.root.after(0, lambda v=idx:       self.progress.configure(amountused=v))
            self.root.after(0, lambda r=remaining:self.timer   .configure(amountused=r))

            # Suche
            seq, eff, cost, profit = self.search.find_sequence(
                desired_effects=[],
                optimize_for=self.opt_var.get(),
                base=base,
                min_steps=depth,
                max_steps=depth,
                allowed_ingredients=allowed,
                timeout=remaining,
                abort_callback=lambda: self.abort_flag
            )
            self.logger.info(f"Tiefe {depth}: profit={profit:.2f}, seq={seq}")
            if seq and profit > best_profit:
                best_profit, best_cost = profit, cost
                best_seq, best_eff     = seq, eff

        # Am Ende: Buttons zurücksetzen und Ergebnis anzeigen
        def _finish():
            self.countdown.stop()
            self.find_btn.configure(state='normal')
            self.cancel_btn.configure(state='disabled')
            if best_seq:
                sale = round(self.calc.calculate_sale_price(best_eff, base))
                prof = sale - best_cost
                self.result_txt.delete("1.0", END)
                self.result_txt.insert(END,
                    f"Sequenz:       {best_seq}\n"
                    f"Effekte:       {best_eff}\n"
                    f"Kosten:        ${best_cost:.2f}\n"
                    f"Verkaufspreis: ${sale}\n"
                    f"Profit:        ${prof}\n"
                )
        self.root.after(0, _finish)