"""
Linux Package Optimizer — Main Window (tkinter, no third-party deps)
Dark industrial theme.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.package_detector import detect
from core.package_scanner import scan, ScanResult, Package
from core import operations

# ─── Palette ─────────────────────────────────────────────────────────────────

C = {
    "bg":        "#0d0f12",
    "panel":     "#141720",
    "card":      "#1a1e2a",
    "hover":     "#1f2435",
    "border":    "#252a38",
    "fg":        "#e8eaf0",
    "fg2":       "#7a8099",
    "fg3":       "#4a5168",
    "blue":      "#4a9eff",
    "green":     "#3ecf8e",
    "red":       "#ff5a5a",
    "amber":     "#ffb547",
    "purple":    "#a78bfa",
    "sel":       "#1e3a5f",
    "sel_fg":    "#e8eaf0",
}

FONT_MONO  = ("Monospace", 11)
FONT_SMALL = ("Monospace", 10)
FONT_TITLE = ("Monospace", 13, "bold")
FONT_STAT  = ("Monospace", 22, "bold")
FONT_LABEL = ("Monospace", 9)


# ─── Helper widgets ───────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    def __init__(self, parent, label: str, color: str = C["blue"]):
        super().__init__(parent, bg=C["card"],
                         highlightbackground=C["border"], highlightthickness=1)
        self._color = color
        self.value_var = tk.StringVar(value="—")

        tk.Label(self, textvariable=self.value_var,
                 font=FONT_STAT, fg=color, bg=C["card"],
                 anchor="w").pack(padx=18, pady=(14, 2), anchor="w")
        tk.Label(self, text=label.upper(),
                 font=FONT_LABEL, fg=C["fg2"], bg=C["card"],
                 anchor="w").pack(padx=18, pady=(0, 12), anchor="w")

    def set(self, value: str):
        self.value_var.set(value)


class SectionHeader(tk.Frame):
    def __init__(self, parent, text: str):
        super().__init__(parent, bg=C["card"],
                         highlightbackground=C["border"], highlightthickness=1)
        tk.Label(self, text=text, font=FONT_MONO,
                 fg=C["fg2"], bg=C["card"],
                 anchor="w").pack(padx=12, pady=6, anchor="w")


def _styled_button(parent, text: str, command, style: str = "normal",
                   width: int = 20) -> tk.Button:
    colors = {
        "normal":  (C["card"],  C["fg"],   C["blue"]),
        "primary": (C["blue"],  "#ffffff", "#5aafff"),
        "danger":  (C["card"],  C["red"],  C["red"]),
        "success": (C["card"],  C["green"], C["green"]),
    }
    bg, fg, active_fg = colors.get(style, colors["normal"])
    btn = tk.Button(
        parent, text=text, command=command,
        font=FONT_SMALL, fg=fg, bg=bg,
        activeforeground=active_fg, activebackground=C["hover"],
        relief="flat", bd=0, padx=14, pady=8,
        width=width, cursor="hand2",
        highlightbackground=C["border"], highlightthickness=1,
    )
    return btn


# ─── Sortable Treeview ────────────────────────────────────────────────────────

class SortableTree(ttk.Treeview):
    """Treeview with click-to-sort on column headers."""

    def __init__(self, parent, columns, headings, widths, **kw):
        super().__init__(parent, columns=columns, show="headings", **kw)
        self._sort_col = None
        self._sort_rev = False

        for col, heading, width in zip(columns, headings, widths):
            self.heading(col, text=heading,
                         command=lambda c=col: self._sort_by(c))
            self.column(col, width=width, anchor="w", minwidth=40)

    def _sort_by(self, col: str):
        rows = [(self.set(k, col), k) for k in self.get_children("")]
        reverse = (self._sort_col == col and not self._sort_rev)
        self._sort_col = col
        self._sort_rev = reverse

        def _key(item):
            v = item[0]
            # Try numeric sort for size column
            try:
                num = float(v.replace(" MB", "").replace(" KB", "").replace(",", "."))
                mult = 1 if "KB" in v else 1024
                return num * mult
            except ValueError:
                return v.lower()

        rows.sort(key=_key, reverse=reverse)
        for i, (_, k) in enumerate(rows):
            self.move(k, "", i)
        arrow = " ▼" if reverse else " ▲"
        for c in self["columns"]:
            h = self.heading(c)["text"].rstrip(" ▼▲")
            self.heading(c, text=h + (arrow if c == col else ""))


# ─── Main Window ─────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Linux Package Optimizer")
        self.geometry("1200x780")
        self.minsize(900, 600)
        self.configure(bg=C["bg"])

        self._manager = detect()
        self._result: ScanResult | None = None
        self._check_vars: dict[str, tk.BooleanVar] = {}  # name → BooleanVar

        self._apply_ttk_style()
        self._build()

        if not self._manager:
            messagebox.showerror(
                "Unsupported System",
                "No supported package manager found.\n\n"
                "Supported: pacman, apt, dnf, zypper"
            )

    # ─── Styles ──────────────────────────────────────────────────────────────

    def _apply_ttk_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Treeview",
                        background=C["panel"], foreground=C["fg"],
                        fieldbackground=C["panel"], rowheight=32,
                        borderwidth=0, font=FONT_SMALL)
        style.configure("Treeview.Heading",
                        background=C["card"], foreground=C["fg2"],
                        relief="flat", font=FONT_LABEL,
                        borderwidth=0)
        style.map("Treeview",
                  background=[("selected", C["sel"])],
                  foreground=[("selected", C["sel_fg"])])
        style.map("Treeview.Heading",
                  background=[("active", C["hover"])])

        style.configure("Vertical.TScrollbar",
                        background=C["border"], troughcolor=C["panel"],
                        arrowcolor=C["fg3"], borderwidth=0, relief="flat")
        style.configure("TNotebook",
                        background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=C["bg"], foreground=C["fg2"],
                        padding=[20, 8], font=FONT_LABEL,
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", C["panel"])],
                  foreground=[("selected", C["blue"])])

        style.configure("TProgressbar",
                        background=C["blue"], troughcolor=C["card"],
                        borderwidth=0, thickness=4)

    # ─── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()
        self._build_stats()
        self._build_progress()
        self._build_notebook()
        self._build_actions()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=C["card"],
                       highlightbackground=C["border"], highlightthickness=1)
        hdr.pack(fill="x", side="top")

        left = tk.Frame(hdr, bg=C["card"])
        left.pack(side="left", padx=20, pady=14)

        tk.Label(left, text="⬡", font=("Monospace", 18),
                 fg=C["blue"], bg=C["card"]).pack(side="left", padx=(0, 10))
        tk.Label(left, text="Linux Package Optimizer",
                 font=FONT_TITLE, fg=C["fg"], bg=C["card"]).pack(side="left")

        pm = self._manager.upper() if self._manager else "UNSUPPORTED"
        tk.Label(left, text=f"  {pm}  ",
                 font=FONT_LABEL, fg=C["purple"],
                 bg=C["card"],
                 relief="solid", bd=1,
                 padx=6, pady=2).pack(side="left", padx=14)

        right = tk.Frame(hdr, bg=C["card"])
        right.pack(side="right", padx=20)
        self._scan_btn = _styled_button(right, "⟳  Scan System",
                                        self._on_scan, "primary", width=16)
        self._scan_btn.pack(pady=12)
        if not self._manager:
            self._scan_btn.config(state="disabled")

    def _build_stats(self):
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x", padx=20, pady=(16, 0))
        for i in range(4):
            row.columnconfigure(i, weight=1, uniform="stat")

        self._stat_installed  = StatCard(row, "Installed Packages", C["blue"])
        self._stat_removable  = StatCard(row, "Removable Packages",  C["amber"])
        self._stat_reclaimable= StatCard(row, "Reclaimable Space",   C["green"])
        self._stat_cache      = StatCard(row, "Cache Size",          C["purple"])

        for i, card in enumerate([self._stat_installed, self._stat_removable,
                                   self._stat_reclaimable, self._stat_cache]):
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 10 if i < 3 else 0))

    def _build_progress(self):
        self._progress_frame = tk.Frame(self, bg=C["bg"])
        self._progress_frame.pack(fill="x", padx=20, pady=8)
        self._progress = ttk.Progressbar(self._progress_frame,
                                         mode="indeterminate",
                                         style="TProgressbar")
        # hidden by default — only pack when needed

    def _build_notebook(self):
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=20, pady=8)

        self._tab_removable = self._make_tab("  Removable Packages  ")
        self._tab_largest   = self._make_tab("  Largest Packages  ")
        self._tab_all       = self._make_tab("  All Packages  ")

        self._build_removable_tab(self._tab_removable)
        self._build_largest_tab(self._tab_largest)
        self._build_all_tab(self._tab_all)

    def _make_tab(self, title: str) -> tk.Frame:
        f = tk.Frame(self._nb, bg=C["panel"])
        self._nb.add(f, text=title)
        return f

    # ── Removable tab ─────────────────────────────────────────────────────────

    def _build_removable_tab(self, parent: tk.Frame):
        info = tk.Label(parent,
                        text="Orphaned dependencies and unused packages safe to remove.",
                        font=FONT_LABEL, fg=C["fg2"], bg=C["panel"])
        info.pack(anchor="w", padx=14, pady=(10, 4))

        # Scrollable checkbox list
        cols_frame = tk.Frame(parent, bg=C["panel"])
        cols_frame.pack(fill="x", padx=14, pady=(0, 4))
        for text, width in [("  ✓", 3), ("Package", 25), ("Size", 12), ("Description", 60)]:
            tk.Label(cols_frame, text=text, font=FONT_LABEL,
                     fg=C["fg3"], bg=C["panel"],
                     width=width, anchor="w").pack(side="left")

        sep = tk.Frame(parent, bg=C["border"], height=1)
        sep.pack(fill="x", padx=14)

        # Scrollable area
        container = tk.Frame(parent, bg=C["panel"])
        container.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        canvas = tk.Canvas(container, bg=C["panel"],
                           highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(container, orient="vertical",
                             command=canvas.yview,
                             style="Vertical.TScrollbar")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._removable_inner = tk.Frame(canvas, bg=C["panel"])
        self._removable_canvas_id = canvas.create_window(
            (0, 0), window=self._removable_inner, anchor="nw"
        )

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self._removable_inner.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(e):
            canvas.itemconfig(self._removable_canvas_id, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll( 1, "units"))

        self._removable_canvas = canvas

        # Controls row
        ctrl = tk.Frame(parent, bg=C["panel"])
        ctrl.pack(fill="x", padx=14, pady=(4, 8))

        self._select_all_var = tk.BooleanVar()
        tk.Checkbutton(ctrl, text="Select All",
                       variable=self._select_all_var,
                       command=self._on_select_all,
                       font=FONT_SMALL, fg=C["fg2"], bg=C["panel"],
                       selectcolor=C["card"],
                       activebackground=C["panel"],
                       activeforeground=C["blue"],
                       bd=0).pack(side="left")

        self._removable_count_lbl = tk.Label(ctrl, text="0 packages",
                                             font=FONT_LABEL, fg=C["fg3"],
                                             bg=C["panel"])
        self._removable_count_lbl.pack(side="right")

    def _build_largest_tab(self, parent: tk.Frame):
        info = tk.Label(parent,
                        text="Top 20 packages by installed size. Click a column header to sort.",
                        font=FONT_LABEL, fg=C["fg2"], bg=C["panel"])
        info.pack(anchor="w", padx=14, pady=(10, 6))

        frame = tk.Frame(parent, bg=C["panel"])
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self._largest_tree = SortableTree(
            frame,
            columns=("rank", "name", "size", "desc"),
            headings=["#", "Package", "Size", "Description"],
            widths=[50, 220, 100, 500],
        )
        vsb = ttk.Scrollbar(frame, orient="vertical",
                            command=self._largest_tree.yview,
                            style="Vertical.TScrollbar")
        self._largest_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._largest_tree.pack(fill="both", expand=True)

        self._largest_tree.tag_configure("odd", background=C["card"])
        self._largest_tree.tag_configure("even", background=C["panel"])

    def _build_all_tab(self, parent: tk.Frame):
        info = tk.Label(parent,
                        text="All installed packages. Click a column header to sort.",
                        font=FONT_LABEL, fg=C["fg2"], bg=C["panel"])
        info.pack(anchor="w", padx=14, pady=(10, 6))

        frame = tk.Frame(parent, bg=C["panel"])
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self._all_tree = SortableTree(
            frame,
            columns=("name", "size", "version", "desc"),
            headings=["Package", "Size", "Version", "Description"],
            widths=[220, 100, 130, 500],
        )
        vsb = ttk.Scrollbar(frame, orient="vertical",
                            command=self._all_tree.yview,
                            style="Vertical.TScrollbar")
        self._all_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._all_tree.pack(fill="both", expand=True)

        self._all_tree.tag_configure("removable", foreground=C["amber"])
        self._all_tree.tag_configure("odd",  background=C["card"])
        self._all_tree.tag_configure("even", background=C["panel"])

    def _build_actions(self):
        row = tk.Frame(self, bg=C["bg"])
        row.pack(fill="x", padx=20, pady=(0, 12))

        self._remove_btn = _styled_button(
            row, "✕  Remove Selected", self._on_remove, "danger", width=20)
        self._remove_btn.pack(side="left", padx=(0, 10))
        self._remove_btn.config(state="disabled")

        self._clean_btn = _styled_button(
            row, "⊘  Clean Package Cache", self._on_clean, "success", width=22)
        self._clean_btn.pack(side="left")
        self._clean_btn.config(state="disabled")

        tk.Label(row,
                 text="⚠  Removal requires administrator privileges",
                 font=FONT_LABEL, fg=C["fg3"], bg=C["bg"]).pack(side="right")

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=C["card"],
                       highlightbackground=C["border"], highlightthickness=1)
        bar.pack(fill="x", side="bottom")
        self._status_var = tk.StringVar(value="  Ready. Click 'Scan System' to begin.")
        tk.Label(bar, textvariable=self._status_var,
                 font=FONT_LABEL, fg=C["fg2"], bg=C["card"],
                 anchor="w").pack(fill="x", padx=8, pady=5)

    # ─── Scan ─────────────────────────────────────────────────────────────────

    def _on_scan(self):
        if not self._manager:
            return
        self._set_busy(True, "Scanning system packages…")
        self._scan_btn.config(text="  Scanning…  ", state="disabled")
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        result = scan(self._manager)
        self.after(0, self._on_scan_done, result)

    def _on_scan_done(self, result: ScanResult):
        self._result = result
        self._set_busy(False)
        self._scan_btn.config(text="⟳  Scan System", state="normal")

        self._stat_installed.set(str(result.total))
        self._stat_removable.set(str(result.removable_count))
        self._stat_reclaimable.set(f"{result.reclaimable_mb} MB")
        self._stat_cache.set(
            f"{result.cache_size_mb:.1f} MB" if result.cache_size_mb else "—"
        )

        self._populate_removable(result.orphans)
        self._populate_largest(result.largest)
        self._populate_all(
            sorted(result.packages, key=lambda p: p.size_kb, reverse=True)
        )

        self._clean_btn.config(state="normal")
        self._status(
            f"Scan complete — {result.total} packages, "
            f"{result.removable_count} removable, "
            f"{result.reclaimable_mb} MB reclaimable."
        )

        if result.errors:
            self._status(f"Scan complete with warnings: {result.errors[0]}")

    # ─── Populate tables ──────────────────────────────────────────────────────

    def _populate_removable(self, packages: list[Package]):
        for w in self._removable_inner.winfo_children():
            w.destroy()
        self._check_vars.clear()
        self._select_all_var.set(False)

        for pkg in packages:
            var = tk.BooleanVar()
            self._check_vars[pkg.name] = var

            row = tk.Frame(self._removable_inner, bg=C["panel"])
            row.pack(fill="x")

            # Hover highlight
            def _enter(e, r=row): r.config(bg=C["hover"])
            def _leave(e, r=row): r.config(bg=C["panel"])
            row.bind("<Enter>", _enter)
            row.bind("<Leave>", _leave)

            cb = tk.Checkbutton(row, variable=var,
                                command=self._update_remove_btn,
                                bg=C["panel"], selectcolor=C["card"],
                                activebackground=C["panel"],
                                bd=0, width=2)
            cb.pack(side="left", padx=(4, 2))

            tk.Label(row, text=pkg.name, font=FONT_SMALL,
                     fg=C["fg"], bg=C["panel"],
                     width=26, anchor="w").pack(side="left")
            tk.Label(row, text=pkg.size_display, font=FONT_SMALL,
                     fg=C["amber"], bg=C["panel"],
                     width=10, anchor="e").pack(side="left", padx=(0, 16))
            tk.Label(row, text=pkg.description or "—", font=FONT_LABEL,
                     fg=C["fg2"], bg=C["panel"],
                     anchor="w").pack(side="left", fill="x")

            sep = tk.Frame(self._removable_inner, bg=C["border"], height=1)
            sep.pack(fill="x")

        self._removable_count_lbl.config(
            text=f"{len(packages)} package{'s' if len(packages) != 1 else ''}"
        )
        self._update_remove_btn()

        # Reset scroll
        self._removable_canvas.yview_moveto(0)

    def _populate_largest(self, packages: list[Package]):
        self._largest_tree.delete(*self._largest_tree.get_children())
        for i, pkg in enumerate(packages):
            tag = "odd" if i % 2 else "even"
            self._largest_tree.insert("", "end",
                values=(f"#{i+1}", pkg.name, pkg.size_display, pkg.description or "—"),
                tags=(tag,))

    def _populate_all(self, packages: list[Package]):
        self._all_tree.delete(*self._all_tree.get_children())
        for i, pkg in enumerate(packages):
            tags = []
            tags.append("odd" if i % 2 else "even")
            if pkg.removable:
                tags.append("removable")
            self._all_tree.insert("", "end",
                values=(pkg.name, pkg.size_display, pkg.version, pkg.description or "—"),
                tags=tuple(tags))

    # ─── Actions ─────────────────────────────────────────────────────────────

    def _on_select_all(self):
        state = self._select_all_var.get()
        for var in self._check_vars.values():
            var.set(state)
        self._update_remove_btn()

    def _update_remove_btn(self):
        selected = self._get_selected()
        if selected:
            self._remove_btn.config(state="normal",
                                    text=f"✕  Remove Selected ({len(selected)})")
        else:
            self._remove_btn.config(state="disabled",
                                    text="✕  Remove Selected")

    def _get_selected(self) -> list[str]:
        return [name for name, var in self._check_vars.items() if var.get()]

    def _on_remove(self):
        selected = self._get_selected()
        if not selected:
            return
        pkg_list = "\n  • ".join(selected[:15])
        extra = f"\n  … and {len(selected)-15} more" if len(selected) > 15 else ""
        confirmed = messagebox.askyesno(
            "Confirm Package Removal",
            f"Remove {len(selected)} package(s)?\n\n"
            f"  • {pkg_list}{extra}\n\n"
            "Administrator privileges will be requested."
        )
        if not confirmed:
            return
        self._set_busy(True, f"Removing {len(selected)} package(s)…")
        threading.Thread(
            target=self._remove_thread, args=(selected,), daemon=True
        ).start()

    def _remove_thread(self, names: list[str]):
        result = operations.remove_packages(self._manager, names)
        self.after(0, self._on_remove_done, result)

    def _on_remove_done(self, result):
        self._set_busy(False)
        if result.success:
            messagebox.showinfo("Success", "Packages removed successfully.")
            self._on_scan()
        else:
            messagebox.showerror("Removal Failed",
                                 f"Package removal failed:\n\n{result.stderr}")
            self._status(f"Removal failed: {result.stderr[:100]}")

    def _on_clean(self):
        from utils.command_runner import run as _run
        cache_cmd = {"pacman": "du -sm /var/cache/pacman/pkg/",
                     "apt":    "du -sm /var/cache/apt/archives/",
                     "dnf":    "du -sm /var/cache/dnf/",
                     "zypper": "du -sm /var/cache/zypp/"}.get(self._manager, "")
        cache_size = "unknown"
        if cache_cmd:
            r = _run(cache_cmd)
            if r.success:
                try:
                    cache_size = f"{float(r.stdout.split()[0]):.1f} MB"
                except (ValueError, IndexError):
                    pass

        confirmed = messagebox.askyesno(
            "Clean Package Cache",
            f"Clean package cache ({cache_size})?\n\n"
            "This removes cached package files.\n"
            "Administrator privileges will be requested."
        )
        if not confirmed:
            return
        self._set_busy(True, "Cleaning package cache…")
        threading.Thread(target=self._clean_thread, daemon=True).start()

    def _clean_thread(self):
        result = operations.clean_cache(self._manager)
        self.after(0, self._on_clean_done, result)

    def _on_clean_done(self, result):
        self._set_busy(False)
        if result.success:
            messagebox.showinfo("Success", "Package cache cleaned successfully.")
            self._on_scan()
        else:
            messagebox.showerror("Cache Clean Failed",
                                 f"Cache cleaning failed:\n\n{result.stderr}")
            self._status(f"Cache clean failed: {result.stderr[:100]}")

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _set_busy(self, busy: bool, msg: str = ""):
        if busy:
            self._progress.pack(fill="x")
            self._progress.start(12)
        else:
            self._progress.stop()
            self._progress.pack_forget()
        if msg:
            self._status(msg)

    def _status(self, msg: str):
        self._status_var.set(f"  {msg}")
