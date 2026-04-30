import argparse
import threading
import tkinter as tk
from tkinter import font as tkfont

from yoctopuce.yocto_rangefinder import *


class Parameters:
    def __init__(self, travel, max_val, gui,):
        self.travel = int(travel)
        self.max_val = int(max_val)
        self.sag = 0
        self.mm_sag = 0
        self.gui = gui  # reference to the GUI for live updates

    def update(self, new_val):
        # Update max value in case the app was started with the suspension compressed
        if new_val > self.max_val:
            self.max_val = new_val

        mm_sag = self.max_val - new_val
        sag = mm_sag * 100 // self.travel

        if sag != self.sag or mm_sag != self.mm_sag:
            self.sag = sag
            self.mm_sag = mm_sag
            if self.gui is None:

                print("SAG = %d%% (%dmm)" % (self.sag, mm_sag))
                print("  %dmm = %d - %d" % (mm_sag, self.max_val, new_val))
            else:
                self.gui.update_display(sag, mm_sag, self.max_val, new_val)


def valueCallback(rf, value):
    """Called by Yoctopuce SDK each time a new range measurement arrives."""
    p = rf.get_userData()
    p.update(int(value))


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class SagWindow:
    """Main application window showing the suspension SAG meter."""

    # Thresholds for colour feedback (percent)
    SAG_GOOD_MIN = 25
    SAG_GOOD_MAX = 35

    # Color palette
    BG = "#0d0d0d"
    FG_TITLE = "#ffffff"
    FG_LABEL = "#888888"
    FG_GOOD = "#00e676"  # green  – SAG in target range
    FG_WARN = "#ff9800"  # orange – SAG slightly off
    FG_BAD = "#f44336"  # red    – SAG very wrong

    def __init__(self, root, travel, verbose):
        self.root = root
        self.travel = travel
        self.verbose = verbose

        root.title("Suspension SAG Meter")
        root.configure(bg=self.BG)
        root.geometry("420x320")
        root.resizable(False, False)

        self._build_ui()

    def _build_ui(self):
        """Create all widgets."""
        pad = dict(padx=20, pady=6)

        # ── Title ──────────────────────────────────────────────────────────
        title_font = tkfont.Font(family="Courier New", size=16, weight="bold")
        tk.Label(
            self.root, text="SUSPENSION SAG METER",
            font=title_font, bg=self.BG, fg=self.FG_TITLE
        ).pack(pady=(24, 0))

        # Divider line
        tk.Frame(self.root, bg="#333333", height=1).pack(fill="x", padx=20, pady=10)

        # ── Travel info ────────────────────────────────────────────────────
        info_font = tkfont.Font(family="Courier New", size=11)
        tk.Label(
            self.root,
            text=f"Travel: {self.travel} mm   |   Target SAG: {self.SAG_GOOD_MIN}–{self.SAG_GOOD_MAX}%",
            font=info_font, bg=self.BG, fg=self.FG_LABEL
        ).pack()

        # ── SAG percentage (big number) ────────────────────────────────────
        big_font = tkfont.Font(family="Courier New", size=64, weight="bold")
        self.lbl_sag = tk.Label(
            self.root, text="--", font=big_font,
            bg=self.BG, fg=self.FG_LABEL
        )
        self.lbl_sag.pack(pady=(12, 0))

        # ── mm label below the big number ─────────────────────────────────
        mm_font = tkfont.Font(family="Courier New", size=14)
        self.lbl_mm = tk.Label(
            self.root, text="waiting for sensor…",
            font=mm_font, bg=self.BG, fg=self.FG_LABEL
        )
        self.lbl_mm.pack()

        if self.verbose:
            mm_font = tkfont.Font(family="Courier New", size=14)
            self.lbl_verbose = tk.Label(
                self.root, text="…",
                font=mm_font, bg=self.BG, fg=self.FG_LABEL
            )
            self.lbl_verbose.pack()

        # ── Status bar at the bottom ───────────────────────────────────────
        self.lbl_status = tk.Label(
            self.root, text="● connected",
            font=tkfont.Font(family="Courier New", size=10),
            bg=self.BG, fg="#00e676", anchor="w"
        )
        self.lbl_status.pack(fill="x", padx=20, pady=(10, 0))

    def _sag_color(self, sag):
        """Return a colour depending on how close the SAG is to the target range."""
        if self.SAG_GOOD_MIN <= sag <= self.SAG_GOOD_MAX:
            return self.FG_GOOD
        return self.FG_BAD

    def update_display(self, sag, mm_sag, max, current):
        """
        Schedule a UI refresh on the main thread.
        Must be called from the sensor thread via root.after() to stay thread-safe.
        """
        self.root.after(0, self._refresh, sag, mm_sag, max, current)

    def _refresh(self, sag, mm_sag, max, current):
        """Actually update the labels — runs on the Tk main thread."""
        color = self._sag_color(sag)
        self.lbl_sag.config(text=f"{sag}%", fg=color)
        self.lbl_mm.config(text=f"{mm_sag} mm of sag", fg=color)
        if self.verbose:
            self.lbl_verbose.config(text=f"{mm_sag}mm = {max} - {current}")

    def set_status(self, msg, error=True):
        """Display an offline warning when the sensor disconnects."""
        self.root.after(0, self._update_status, msg, error)

    def _update_status(self, msg, error):
        color = self.FG_BAD if error else self.FG_GOOD
        self.lbl_status.config(text=f"{msg}", fg=color)
        self.lbl_status.config(text=msg, fg=color)
        self.lbl_sag.config(fg=color)


# ---------------------------------------------------------------------------
# Sensor logic (runs in a background thread so it never blocks the GUI)
# ---------------------------------------------------------------------------

def display_msg(msg, iserror, gui):
    if gui is None:
        print(msg)
    else:
        gui.set_status(msg, iserror)


def sensor_thread(url, target, travel, gui):
    """
    Connect to the Yocto-RangeFinder and poll continuously.
    Runs in a daemon thread so it exits automatically when the window closes.
    """
    errmsg = YRefParam()
    display_msg("connecting to %s" % url, False, gui)
    if YAPI.RegisterHub(url, errmsg) != YAPI.SUCCESS:
        display_msg("USB error: " + errmsg.value, True, gui)
        return
    display_msg("connected", False, gui)

    if target == "first":
        rf = YRangeFinder.FirstRangeFinder()
        if rf is None:
            display_msg("No Yocto-RangeFinder found", True, gui)
            return
    else:
        rf = YRangeFinder.FindRangeFinder(target + ".rangeFinder1")
        if not rf.isOnline():
            display_msg(f"{target} not connected", True, gui)
            return
    display_msg("use sensor %s" % rf.get_serialNumber(), False, gui)
    # Use high-accuracy mode for better precision
    rf.set_rangeFinderMode(YRangeFinder.RANGEFINDERMODE_HIGH_ACCURACY)

    # Build the parameter object, passing the GUI reference so callbacks can update it
    parameters = Parameters(travel, rf.get_currentValue(), gui)
    rf.set_userData(parameters)
    rf.registerValueCallback(valueCallback)
    while rf.isOnline():
        YAPI.Sleep(1000)
    display_msg("Yocto-Rangefinder %s is offline" % rf.get_serialNumber(), False, gui)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Compute suspension sag from Yocto-RangeFinder', )
    parser.add_argument('-g', '--gui', dest='gui', action='store_true', default=False, help='show GUI')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    parser.add_argument('-r', '--remote', dest='url', action='store', default='usb',
                        help='Remote YoctoHub or VirtualHub')
    parser.add_argument('-s', '--serial', dest='target', action='store',
                        help='serial number (or logical name) of the Yocto-Range finder to use', default="first")
    parser.add_argument('travel', help='suspension travel in mm')
    args = parser.parse_args()
    if args.gui:
        # ── Build the Tkinter window ───────────────────────────────────────────
        root = tk.Tk()
        gui = SagWindow(root, int(args.travel), args.verbose)

        # ── Start the sensor in a background daemon thread ─────────────────────
        t = threading.Thread(
            target=sensor_thread,
            args=(args.url, args.target, args.travel, gui),
            daemon=True  # thread dies automatically when the window closes
        )
        t.start()

        # ── Hand control to Tkinter's event loop ──────────────────────────────
        root.mainloop()
    else:
        sensor_thread(args.url, args.target, args.travel, None)


if __name__ == "__main__":
    main()
