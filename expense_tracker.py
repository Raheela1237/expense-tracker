#!/usr/bin/env python3
"""
Expense Tracker - GUI (Tkinter) - CodeNova Python Internship Task 2
Professional dark-slate UI with scrollable left panel.
"""

from __future__ import annotations

import csv
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass, asdict
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional, Dict

# ---------- CONSTANTS ----------
DATA_DIR = Path("data")
EXPORT_DIR = Path("exports")
DATA_FILE = DATA_DIR / "transactions.json"

CATEGORIES = ["Food", "Utilities", "Travel", "Shopping",
              "Health", "Entertainment", "Education",
              "Salary", "Other"]
TYPES = ["income", "expense"]

# ---------- PROFESSIONAL COLOR PALETTE ----------
COLOR_APP_BG      = "#0f172a"
COLOR_SURFACE     = "#1e293b"
COLOR_SURFACE_2   = "#273449"
COLOR_BORDER      = "#334155"
COLOR_TEXT        = "#e2e8f0"
COLOR_TEXT_MUTED  = "#94a3b8"
COLOR_ACCENT      = "#3b82f6"
COLOR_ACCENT_HOV  = "#2563eb"
COLOR_INCOME      = "#10b981"
COLOR_EXPENSE     = "#ef4444"
COLOR_NET         = "#60a5fa"
COLOR_HEADER      = "#111827"
COLOR_INPUT_BG    = "#0b1220"
COLOR_INPUT_FG    = "#e2e8f0"
COLOR_SELECT      = "#1d4ed8"


# ---------- MODEL ----------
@dataclass
class Transaction:
    id: int
    date: str
    type: str
    category: str
    amount: str
    description: str = ""

    @property
    def amount_decimal(self) -> Decimal:
        return Decimal(self.amount)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        return cls(
            id=int(d["id"]),
            date=d["date"],
            type=d["type"],
            category=d["category"],
            amount=str(d["amount"]),
            description=d.get("description", "")
        )


# ---------- VALIDATORS ----------
def validate_date(date_str: str) -> datetime:
    if not date_str:
        raise ValueError("Date cannot be empty.")
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")


def validate_amount(amount_str: str) -> Decimal:
    if not amount_str:
        raise ValueError("Amount cannot be empty.")
    try:
        amount = Decimal(amount_str)
    except InvalidOperation:
        raise ValueError("Invalid amount. Please enter a number.")
    if amount <= 0:
        raise ValueError("Amount must be positive.")
    return amount.quantize(Decimal("0.01"))


# ---------- STORAGE ----------
class ExpenseStore:
    def __init__(self, data_file: Path = DATA_FILE):
        self.data_file = data_file
        self.transactions: List[Transaction] = []
        self.next_id = 1
        self.load()

    def load(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.data_file.exists():
            self.transactions = []
            self.next_id = 1
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.transactions = [Transaction.from_dict(x) for x in raw]
            self.next_id = max([t.id for t in self.transactions], default=0) + 1
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            backup = self.data_file.with_suffix(".corrupted.bak")
            self.data_file.rename(backup)
            self.transactions = []
            self.next_id = 1
            self.save()

    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.transactions], f, indent=2)

    def add(self, date_str, type_, category, amount_str, description) -> Transaction:
        dt = validate_date(date_str)
        type_ = type_.lower().strip()
        if type_ not in TYPES:
            raise ValueError("Type must be income or expense.")
        amount = validate_amount(amount_str)
        category = category.strip().title()
        if not category:
            raise ValueError("Category cannot be empty.")
        t = Transaction(self.next_id, dt.strftime("%Y-%m-%d"),
                        type_, category, str(amount), description.strip())
        self.transactions.append(t)
        self.next_id += 1
        self.save()
        return t

    def delete(self, tid: int):
        self.transactions = [t for t in self.transactions if t.id != tid]
        self.save()

    def update(self, tid: int, **fields):
        for t in self.transactions:
            if t.id == tid:
                if "date" in fields:
                    t.date = validate_date(fields["date"]).strftime("%Y-%m-%d")
                if "type" in fields:
                    v = fields["type"].lower()
                    if v not in TYPES:
                        raise ValueError("Invalid type.")
                    t.type = v
                if "category" in fields:
                    if not fields["category"].strip():
                        raise ValueError("Category cannot be empty.")
                    t.category = fields["category"].strip().title()
                if "amount" in fields:
                    t.amount = str(validate_amount(fields["amount"]))
                if "description" in fields:
                    t.description = fields["description"].strip()
                self.save()
                return t
        raise ValueError(f"Transaction ID {tid} not found.")

    def summary(self) -> dict:
        inc = sum((t.amount_decimal for t in self.transactions if t.type == "income"),
                  Decimal("0"))
        exp = sum((t.amount_decimal for t in self.transactions if t.type == "expense"),
                  Decimal("0"))
        by_cat: Dict[str, Decimal] = {}
        for t in self.transactions:
            if t.type == "expense":
                by_cat[t.category] = by_cat.get(t.category, Decimal("0")) + t.amount_decimal
        return {"income": inc, "expense": exp, "net": inc - exp, "by_cat": by_cat}

    def filter(self, start: Optional[str] = None,
               end: Optional[str] = None,
               category: Optional[str] = None) -> List[Transaction]:
        s = validate_date(start).date() if start else None
        e = validate_date(end).date() if end else None
        if s and e and s > e:
            raise ValueError("Start date cannot be after end date.")
        cat = category.strip().lower() if category else None
        result = []
        for t in self.transactions:
            td = datetime.strptime(t.date, "%Y-%m-%d").date()
            if s and td < s: continue
            if e and td > e: continue
            if cat and t.category.lower() != cat: continue
            result.append(t)
        return sorted(result, key=lambda x: (x.date, x.id))

    def export_csv(self, txns: Optional[List[Transaction]] = None,
                   path: Optional[Path] = None) -> Path:
        if txns is None:
            txns = self.transactions
        if path is None:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = EXPORT_DIR / f"transactions_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ID", "Date", "Type", "Category", "Amount", "Description"])
            for t in txns:
                w.writerow([t.id, t.date, t.type, t.category, t.amount, t.description])
        return path


# ---------- SCROLLABLE FRAME ----------
class ScrollableFrame(ttk.Frame):
    """A frame with vertical scrollbar."""
    def __init__(self, parent, bg=COLOR_SURFACE, **kw):
        super().__init__(parent, style="Surface.TFrame", **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical",
                                 command=self.canvas.yview,
                                 style="Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas, style="Surface.TFrame")
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel support
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._win, width=event.width)

    def _on_mousewheel(self, event):
        # only scroll when mouse is over the canvas
        x, y = self.canvas.winfo_pointerxy()
        widget = self.canvas.winfo_containing(x, y)
        if widget is None:
            return
        # walk up parents to see if inside this canvas
        w = widget
        while w is not None:
            if w == self.canvas:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return
            w = w.master


# ---------- GUI APP ----------
class ExpenseTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Expense Tracker")
        self.geometry("1180x760")
        self.configure(bg=COLOR_APP_BG)
        self.minsize(1000, 600)

        self.store = ExpenseStore()
        self._editing_id: Optional[int] = None

        self._build_style()
        self._build_header()
        self._build_body()
        self.refresh_all()

    # -------- styles --------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=COLOR_APP_BG)
        style.configure("Surface.TFrame", background=COLOR_SURFACE)
        style.configure("Surface2.TFrame", background=COLOR_SURFACE_2)

        style.configure("App.TLabel", background=COLOR_APP_BG,
                        foreground=COLOR_TEXT, font=("Segoe UI", 10))
        style.configure("Surface.TLabel", background=COLOR_SURFACE,
                        foreground=COLOR_TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLOR_SURFACE,
                        foreground=COLOR_TEXT_MUTED, font=("Segoe UI", 9))
        style.configure("SectionTitle.TLabel", background=COLOR_SURFACE,
                        foreground=COLOR_TEXT, font=("Segoe UI Semibold", 11, "bold"))

        style.configure("Dark.TEntry",
                        fieldbackground=COLOR_INPUT_BG,
                        foreground=COLOR_INPUT_FG,
                        insertcolor=COLOR_INPUT_FG,
                        bordercolor=COLOR_BORDER,
                        lightcolor=COLOR_BORDER,
                        darkcolor=COLOR_BORDER,
                        padding=6)
        style.map("Dark.TEntry",
                  fieldbackground=[("focus", "#0a1020")],
                  bordercolor=[("focus", COLOR_ACCENT)])

        style.configure("Dark.TCombobox",
                        fieldbackground=COLOR_INPUT_BG,
                        background=COLOR_INPUT_BG,
                        foreground=COLOR_INPUT_FG,
                        arrowcolor=COLOR_TEXT_MUTED,
                        bordercolor=COLOR_BORDER,
                        lightcolor=COLOR_BORDER,
                        darkcolor=COLOR_BORDER,
                        padding=6)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", COLOR_INPUT_BG)],
                  foreground=[("readonly", COLOR_INPUT_FG)],
                  bordercolor=[("focus", COLOR_ACCENT)])

        style.configure("Dark.TRadiobutton",
                        background=COLOR_SURFACE,
                        foreground=COLOR_TEXT,
                        font=("Segoe UI", 10))
        style.map("Dark.TRadiobutton",
                  background=[("active", COLOR_SURFACE)],
                  foreground=[("active", COLOR_TEXT)])

        style.configure("Primary.TButton",
                        background=COLOR_ACCENT,
                        foreground="#ffffff",
                        borderwidth=0,
                        focusthickness=0,
                        font=("Segoe UI Semibold", 10, "bold"),
                        padding=(10, 8))
        style.map("Primary.TButton",
                  background=[("active", COLOR_ACCENT_HOV),
                              ("pressed", COLOR_ACCENT_HOV)])

        style.configure("Secondary.TButton",
                        background=COLOR_SURFACE_2,
                        foreground=COLOR_TEXT,
                        borderwidth=0,
                        focusthickness=0,
                        font=("Segoe UI", 10),
                        padding=(10, 8))
        style.map("Secondary.TButton",
                  background=[("active", "#334155"),
                              ("pressed", "#334155")])

        style.configure("Danger.TButton",
                        background="#3b1d1d",
                        foreground="#fecaca",
                        borderwidth=0,
                        focusthickness=0,
                        font=("Segoe UI", 10),
                        padding=(10, 8))
        style.map("Danger.TButton",
                  background=[("active", "#7f1d1d"),
                              ("pressed", "#7f1d1d")])

        style.configure("Custom.Treeview",
                        background=COLOR_SURFACE,
                        fieldbackground=COLOR_SURFACE,
                        foreground=COLOR_TEXT,
                        rowheight=30,
                        borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Custom.Treeview.Heading",
                        background=COLOR_SURFACE_2,
                        foreground=COLOR_TEXT_MUTED,
                        font=("Segoe UI Semibold", 10, "bold"),
                        borderwidth=0,
                        relief="flat",
                        padding=8)
        style.map("Custom.Treeview.Heading",
                  background=[("active", COLOR_SURFACE_2)])
        style.map("Custom.Treeview",
                  background=[("selected", COLOR_SELECT)],
                  foreground=[("selected", "#ffffff")])

        style.configure("Vertical.TScrollbar",
                        background=COLOR_SURFACE_2,
                        troughcolor=COLOR_SURFACE,
                        bordercolor=COLOR_SURFACE,
                        arrowcolor=COLOR_TEXT_MUTED,
                        borderwidth=0)

        style.configure("Dark.TSeparator", background=COLOR_BORDER)

    # -------- header --------
    def _build_header(self):
        h = tk.Frame(self, bg=COLOR_HEADER, height=72)
        h.pack(fill="x")
        h.pack_propagate(False)

        left = tk.Frame(h, bg=COLOR_HEADER)
        left.pack(side="left", padx=24)

        logo = tk.Canvas(left, width=36, height=36, bg=COLOR_HEADER,
                         highlightthickness=0)
        logo.pack(side="left", pady=18)
        logo.create_oval(2, 2, 34, 34, fill=COLOR_ACCENT, outline="")
        logo.create_text(18, 18, text="$", fill="#ffffff",
                         font=("Segoe UI", 16, "bold"))

        tk.Label(left, text="Expense Tracker", bg=COLOR_HEADER, fg="#ffffff",
                 font=("Segoe UI Semibold", 18, "bold")).pack(side="left", padx=12)

    # -------- body --------
    def _build_body(self):
        container = ttk.Frame(self, style="App.TFrame")
        container.pack(fill="both", expand=True, padx=18, pady=18)

        # LEFT: scrollable form panel
        left_wrap = tk.Frame(container, bg=COLOR_BORDER, width=360)
        left_wrap.pack(side="left", fill="y", padx=(0, 16))
        left_wrap.pack_propagate(False)

        self.left_scroll = ScrollableFrame(left_wrap, bg=COLOR_SURFACE)
        self.left_scroll.pack(fill="both", expand=True, padx=1, pady=1)
        self._build_form(self.left_scroll.inner)

        # RIGHT
        right = ttk.Frame(container, style="App.TFrame")
        right.pack(side="left", fill="both", expand=True)
        self._build_summary(right)
        self._build_filter_and_table(right)

    # -------- form panel --------
    def _build_form(self, parent):
        pad = {"padx": 20, "pady": (8, 3)}

        ttk.Label(parent, text="New Transaction",
                  style="SectionTitle.TLabel").pack(anchor="w", padx=20, pady=(18, 2))
        ttk.Label(parent, text="Fill in details and click save.",
                  style="Muted.TLabel").pack(anchor="w", padx=20, pady=(0, 8))

        ttk.Label(parent, text="Date (YYYY-MM-DD)",
                  style="Surface.TLabel").pack(anchor="w", **pad)
        self.var_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        ttk.Entry(parent, textvariable=self.var_date,
                  style="Dark.TEntry").pack(fill="x", padx=20)

        ttk.Label(parent, text="Type",
                  style="Surface.TLabel").pack(anchor="w", **pad)
        type_frame = ttk.Frame(parent, style="Surface.TFrame")
        type_frame.pack(fill="x", padx=20)
        self.var_type = tk.StringVar(value="expense")
        for val in TYPES:
            ttk.Radiobutton(type_frame, text=val.title(),
                            variable=self.var_type, value=val,
                            style="Dark.TRadiobutton").pack(side="left", padx=(0, 20))

        ttk.Label(parent, text="Category",
                  style="Surface.TLabel").pack(anchor="w", **pad)
        self.var_category = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(parent, textvariable=self.var_category,
                     values=CATEGORIES, state="normal",
                     style="Dark.TCombobox").pack(fill="x", padx=20)

        ttk.Label(parent, text="Amount",
                  style="Surface.TLabel").pack(anchor="w", **pad)
        self.var_amount = tk.StringVar()
        ttk.Entry(parent, textvariable=self.var_amount,
                  style="Dark.TEntry").pack(fill="x", padx=20)

        ttk.Label(parent, text="Description (optional)",
                  style="Surface.TLabel").pack(anchor="w", **pad)
        self.var_desc = tk.StringVar()
        ttk.Entry(parent, textvariable=self.var_desc,
                  style="Dark.TEntry").pack(fill="x", padx=20)

        self.btn_save = ttk.Button(parent, text="Add Transaction",
                                   style="Primary.TButton",
                                   command=self.on_save)
        self.btn_save.pack(fill="x", padx=20, pady=(14, 6))

        ttk.Button(parent, text="Clear Form",
                   style="Secondary.TButton",
                   command=self.clear_form).pack(fill="x", padx=20, pady=4)

        ttk.Separator(parent, style="Dark.TSeparator")\
            .pack(fill="x", padx=20, pady=14)

        # ---- Actions section ----
        ttk.Label(parent, text="Actions",
                  style="SectionTitle.TLabel").pack(anchor="w", padx=20, pady=(0, 6))

        ttk.Button(parent, text="Export CSV",
                   style="Secondary.TButton",
                   command=self.on_export).pack(fill="x", padx=20, pady=4)

        ttk.Button(parent, text="Edit Selected  (Load into form)",
                   style="Secondary.TButton",
                   command=self.on_load_selected).pack(fill="x", padx=20, pady=4)

        ttk.Button(parent, text="Delete Selected",
                   style="Danger.TButton",
                   command=self.on_delete).pack(fill="x", padx=20, pady=(4, 20))

    # -------- summary cards --------
    def _build_summary(self, parent):
        wrap = ttk.Frame(parent, style="App.TFrame")
        wrap.pack(fill="x")

        def card(title, color):
            f = tk.Frame(wrap, bg=COLOR_SURFACE, bd=0,
                         highlightthickness=1,
                         highlightbackground=COLOR_BORDER,
                         highlightcolor=COLOR_BORDER)
            f.pack(side="left", fill="both", expand=True, padx=6, ipady=4)
            tk.Label(f, text=title, bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
            val = tk.Label(f, text="0.00", bg=COLOR_SURFACE, fg=color,
                           font=("Segoe UI Semibold", 20, "bold"))
            val.pack(anchor="w", padx=16, pady=(0, 14))
            return val

        self.lbl_income = card("TOTAL INCOME", COLOR_INCOME)
        self.lbl_expense = card("TOTAL EXPENSE", COLOR_EXPENSE)
        self.lbl_net = card("NET BALANCE", COLOR_NET)
        self.lbl_count = card("TRANSACTIONS", COLOR_TEXT)

    # -------- filter + table --------
    def _build_filter_and_table(self, parent):
        filt = tk.Frame(parent, bg=COLOR_SURFACE, bd=0,
                        highlightthickness=1, highlightbackground=COLOR_BORDER)
        filt.pack(fill="x", pady=(14, 10))

        tk.Label(filt, text="FILTER", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0,
                                                    padx=(16, 12), pady=14, sticky="w")

        tk.Label(filt, text="Start", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=1, padx=(0, 4))
        self.var_start = tk.StringVar()
        ttk.Entry(filt, textvariable=self.var_start, width=12,
                  style="Dark.TEntry").grid(row=0, column=2, padx=(0, 12))

        tk.Label(filt, text="End", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=3, padx=(0, 4))
        self.var_end = tk.StringVar()
        ttk.Entry(filt, textvariable=self.var_end, width=12,
                  style="Dark.TEntry").grid(row=0, column=4, padx=(0, 12))

        tk.Label(filt, text="Category", bg=COLOR_SURFACE, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=5, padx=(0, 4))
        self.var_filter_cat = tk.StringVar(value="All")
        ttk.Combobox(filt, textvariable=self.var_filter_cat,
                     values=["All"] + CATEGORIES, state="readonly",
                     width=14, style="Dark.TCombobox").grid(row=0, column=6, padx=(0, 12))

        ttk.Button(filt, text="Apply", style="Primary.TButton",
                   command=self.refresh_table).grid(row=0, column=7, padx=4, pady=10)
        ttk.Button(filt, text="Reset", style="Secondary.TButton",
                   command=self.reset_filters).grid(row=0, column=8, padx=(4, 16), pady=10)

        tree_card = tk.Frame(parent, bg=COLOR_SURFACE, bd=0,
                             highlightthickness=1, highlightbackground=COLOR_BORDER)
        tree_card.pack(fill="both", expand=True)

        tree_wrap = tk.Frame(tree_card, bg=COLOR_SURFACE)
        tree_wrap.pack(fill="both", expand=True, padx=6, pady=6)

        cols = ("ID", "Date", "Type", "Category", "Amount", "Description")
        self.tree = ttk.Treeview(tree_wrap, columns=cols, show="headings",
                                 style="Custom.Treeview")
        widths = {"ID": 60, "Date": 110, "Type": 90, "Category": 130,
                  "Amount": 110, "Description": 320}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths[c],
                             anchor="e" if c == "Amount" else "w")

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical",
                            command=self.tree.yview,
                            style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("income", foreground=COLOR_INCOME)
        self.tree.tag_configure("expense", foreground=COLOR_EXPENSE)

        # Hint label under table
        tk.Label(parent, text="Tip: Select a row then click 'Edit Selected' or 'Delete Selected'.",
                 bg=COLOR_APP_BG, fg=COLOR_TEXT_MUTED,
                 font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(6, 0))

    # ---------- actions ----------
    def clear_form(self):
        self._editing_id = None
        self.var_date.set(date.today().strftime("%Y-%m-%d"))
        self.var_type.set("expense")
        self.var_category.set(CATEGORIES[0])
        self.var_amount.set("")
        self.var_desc.set("")
        self.btn_save.configure(text="Add Transaction")

    def on_save(self):
        try:
            if self._editing_id is None:
                self.store.add(self.var_date.get(), self.var_type.get(),
                               self.var_category.get(), self.var_amount.get(),
                               self.var_desc.get())
                messagebox.showinfo("Success", "Transaction added successfully.")
            else:
                self.store.update(
                    self._editing_id,
                    date=self.var_date.get(),
                    type=self.var_type.get(),
                    category=self.var_category.get(),
                    amount=self.var_amount.get(),
                    description=self.var_desc.get(),
                )
                messagebox.showinfo("Success", "Transaction updated.")
            self.clear_form()
            self.refresh_all()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))

    def on_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a row to delete.")
            return
        tid = int(self.tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete transaction ID {tid}?"):
            return
        self.store.delete(tid)
        self.refresh_all()
        messagebox.showinfo("Deleted", f"Transaction {tid} deleted.")

    def on_load_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select a row first, then click Edit Selected.")
            return
        values = self.tree.item(sel[0], "values")
        tid, dt, typ, cat, amt, desc = values
        self._editing_id = int(tid)
        self.var_date.set(dt)
        self.var_type.set(typ.lower())
        self.var_category.set(cat)
        self.var_amount.set(amt)
        self.var_desc.set(desc)
        self.btn_save.configure(text="Update Transaction")
        messagebox.showinfo("Edit Mode",
                            f"Transaction ID {tid} loaded.\n"
                            "Edit the fields and click 'Update Transaction'.")

    def on_export(self):
        try:
            txns = self._current_filtered()
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialdir=str(EXPORT_DIR if EXPORT_DIR.exists() else Path.cwd()),
                initialfile=f"transactions_{datetime.now():%Y%m%d_%H%M%S}.csv"
            )
            if not path:
                return
            self.store.export_csv(txns, Path(path))
            messagebox.showinfo("Exported", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def reset_filters(self):
        self.var_start.set("")
        self.var_end.set("")
        self.var_filter_cat.set("All")
        self.refresh_table()

    # ---------- refresh ----------
    def _current_filtered(self) -> List[Transaction]:
        start = self.var_start.get().strip() or None
        end = self.var_end.get().strip() or None
        cat = self.var_filter_cat.get()
        cat = None if cat == "All" else cat
        return self.store.filter(start, end, cat)

    def refresh_table(self):
        try:
            txns = self._current_filtered()
        except ValueError as e:
            messagebox.showerror("Filter Error", str(e))
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        for t in txns:
            self.tree.insert("", "end", values=(
                t.id, t.date, t.type.title(), t.category, t.amount, t.description
            ), tags=(t.type,))

    def refresh_summary(self):
        s = self.store.summary()
        self.lbl_income.configure(text=f"{s['income']:.2f}")
        self.lbl_expense.configure(text=f"{s['expense']:.2f}")
        self.lbl_net.configure(text=f"{s['net']:.2f}")
        self.lbl_count.configure(text=str(len(self.store.transactions)))

    def refresh_all(self):
        self.refresh_summary()
        self.refresh_table()


# ---------- MAIN ----------
def main():
    app = ExpenseTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()