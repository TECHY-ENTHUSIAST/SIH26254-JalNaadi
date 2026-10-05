"""Draws the explanatory diagrams used in the master document (matplotlib, no external assets)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Rectangle

OUT = os.path.join(os.path.dirname(__file__), "images")
BLUE, GREEN, ORANGE, NAVY, RED, GREY = "#0070C0", "#1E7B34", "#E8731A", "#1F4E79", "#C01F1F", "#55616B"


def box(ax, x, y, w, h, text, fc, tc="white", fs=9, ec=None, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec or fc, lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.15)


def arrow(ax, p, q, color=NAVY, ls="-", lw=1.8, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=12, color=color, lw=lw, ls=ls))


def canvas(w, h, xl, yl):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, xl); ax.set_ylim(0, yl); ax.axis("off"); return fig, ax


# 1 ---------------------------------------------------------------- system architecture
fig, ax = canvas(10, 4.6, 20, 9.2)
box(ax, 0.3, 5.6, 2.6, 1.6, "WATER TANK\n(SR / ESR)", "white", NAVY, 9, ec=BLUE)
ax.add_patch(Rectangle((2.9, 6.3), 16.8, 0.22, fc=BLUE, ec=BLUE))
box(ax, 3.4, 4.2, 2.6, 1.2, "NAADI-GATE\nflow + pressure", BLUE, fs=8)
box(ax, 8.4, 4.2, 2.0, 1.2, "EAR-A\n(slave)", GREEN, fs=8)
box(ax, 15.2, 4.2, 2.0, 1.2, "EAR-B\n(master)", GREEN, fs=8)
ax.add_patch(Circle((12.6, 6.41), 0.38, fc=RED, ec="white", lw=1.5)); ax.text(12.6, 7.1, "LEAK at x", color=RED, ha="center", fontsize=9, fontweight="bold")
ax.text(18.2, 6.9, "to homes →", color=GREY, fontsize=8)
for xx in (4.7, 9.4, 16.2): ax.plot([xx, xx], [5.4, 6.3], color="#999", lw=1.2)
arrow(ax, (10.4, 4.8), (15.2, 4.8), GREEN, "--", 2); ax.text(12.8, 5.0, "ESP-NOW: A sends its burst to B", ha="center", fontsize=7.5, color=GREEN)
box(ax, 7.6, 0.8, 4.6, 1.3, "GATEWAY  (SR / pump cabin)\nLoRa 865–867 MHz  →  MQTT-TLS", ORANGE, fs=8.5)
arrow(ax, (4.7, 4.2), (8.2, 2.1), ORANGE, "--", 1.8); arrow(ax, (16.2, 4.2), (11.6, 2.1), ORANGE, "--", 1.8)
arrow(ax, (12.2, 1.45), (14.6, 1.45), NAVY)
box(ax, 14.6, 0.5, 5.0, 1.9, "NAADI-DESK\nGIS map · SMS alert\nrepair-priority list", NAVY, fs=8.5)
arrow(ax, (9.4, 4.2), (9.4, 2.15), ORANGE, ":", 1.2)
ax.text(1.0, 2.6, "Gateway beacon (LoRa) = time reference\nfor both EAR nodes", color=ORANGE, fontsize=8, va="center")
arrow(ax, (3.2, 2.6), (7.5, 1.7), ORANGE, ":", 1.2)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_arch.png", dpi=170); plt.close(fig)

# 2 ---------------------------------------------------------------- TDOA geometry
fig, ax = canvas(9, 3.2, 18, 6.4)
ax.add_patch(Rectangle((1, 3.0), 16, 0.22, fc=BLUE, ec=BLUE))
for xx, lab in ((1.8, "A"), (16.2, "B")):
    box(ax, xx - 0.9, 3.7, 1.8, 0.9, f"EAR-{lab}", GREEN, fs=9); ax.plot([xx, xx], [3.22, 3.7], color="#999")
ax.add_patch(Circle((6.6, 3.11), 0.32, fc=RED, ec="white")); ax.text(6.6, 2.35, "leak", color=RED, ha="center", fontweight="bold")
arrow(ax, (6.3, 3.9), (2.5, 3.9), RED, "-", 1.6); arrow(ax, (6.9, 3.9), (15.5, 3.9), RED, "-", 1.6)
ax.text(4.4, 4.25, "d_A = x", color=RED, ha="center", fontsize=9); ax.text(11.2, 4.25, "d_B = L − x", color=RED, ha="center", fontsize=9)
ax.annotate("", (1.8, 1.6), (16.2, 1.6), arrowprops=dict(arrowstyle="<->", color=NAVY, lw=1.5)); ax.text(9, 1.2, "L  (known, measured on site)", ha="center", color=NAVY, fontsize=9)
ax.text(9, 5.6, "τ = t_B − t_A = (d_B − d_A) / v = (L − 2x) / v      ⇒      x = (L − v·τ) / 2", ha="center", fontsize=11, color=NAVY, fontweight="bold")
ax.text(9, 0.35, "Example: L = 20 m, v = 400 m/s, leak 6 m from A → t_A = 15 ms, t_B = 35 ms, τ = 20 ms → x = (20 − 8)/2 = 6 m", ha="center", fontsize=8.5, color=GREY)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_tdoa.png", dpi=170); plt.close(fig)

# 3 ---------------------------------------------------------------- a night in the life
fig, ax = canvas(10, 3.6, 20, 7.2)
ax.add_patch(Rectangle((1, 3.4), 18, 0.12, fc="#999", ec="#999"))
for t, lab in ((1, "00:00"), (7, "02:00"), (13, "04:00"), (19, "06:00")):
    ax.plot([t, t], [3.3, 3.6], color="#555"); ax.text(t, 3.0, lab, ha="center", fontsize=8)
ax.add_patch(Rectangle((7, 3.4), 6, 0.12, fc=GREEN, ec=GREEN)); ax.text(10, 3.85, "listen window 02:00–04:00", ha="center", color=GREEN, fontsize=8.5, fontweight="bold")
box(ax, 1.0, 5.1, 5.2, 1.5, "1  GATE: nightly mean flow\nvs learned baseline →\nCUSUM alarm: zone Z1", BLUE, fs=8)
box(ax, 6.7, 5.1, 3.6, 1.5, "2  Gateway beacon\nevery 5 min\n(sync + wake)", ORANGE, fs=8)
box(ax, 10.8, 5.1, 3.9, 1.5, "3  EAR pair: 15-s burst\nclassify → exchange →\nGCC-PHAT → x", GREEN, fs=8)
box(ax, 15.2, 5.1, 4.2, 1.5, "4  DESK: pin on map,\nSMS, repair rank\n(by 06:00)", NAVY, fs=8)
for x0, x1 in ((6.2, 6.7), (10.3, 10.8), (14.7, 15.2)): arrow(ax, (x0, 5.85), (x1, 5.85))
for k in range(24): ax.plot([7 + k * 0.25 + 0.12] * 2, [3.55, 3.75], color=ORANGE, lw=1)
ax.text(10, 1.5, "24 bursts per night (one every 5 min) · wake-checks every 15 min the rest of the day", ha="center", fontsize=8.5, color=GREY)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_night.png", dpi=170); plt.close(fig)

# 4 ---------------------------------------------------------------- node block diagram
fig, ax = canvas(9, 3.6, 18, 7.2)
box(ax, 6.2, 2.6, 5.6, 2.8, "ESP32-WROVER\n\nsample · classify · exchange\ncorrelate · schedule · sleep", NAVY, fs=9)
box(ax, 0.3, 4.6, 4.4, 1.4, "MEMS accelerometer\nADXL345 / ADXL355\n(clamped to the pipe)", GREEN, fs=8)
box(ax, 0.3, 2.0, 4.4, 1.4, "LoRa SX1276\n865–867 MHz", ORANGE, fs=8)
box(ax, 13.3, 4.6, 4.4, 1.4, "ESP-NOW\npair link (A ↔ B)", GREEN, fs=8)
box(ax, 13.3, 2.0, 4.4, 1.4, "Power: 18650 + 1 W solar\n+ low-Iq regulator", BLUE, fs=8)
box(ax, 6.2, 0.5, 5.6, 1.1, "IP67 case · tamper switch · INA219 (test)", GREY, fs=8)
arrow(ax, (4.7, 5.3), (6.2, 4.6), GREEN, "-", 1.6); arrow(ax, (4.7, 2.7), (6.2, 3.3), ORANGE, "-", 1.6)
arrow(ax, (11.8, 4.6), (13.3, 5.3), GREEN, "-", 1.6); arrow(ax, (13.3, 2.7), (11.8, 3.3), BLUE, "-", 1.6)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_node.png", dpi=170); plt.close(fig)

# 5 ---------------------------------------------------------------- lab rig
fig, ax = canvas(10, 3.4, 20, 6.8)
box(ax, 0.3, 3.4, 2.6, 1.6, "Water tank\n+ pump", "white", NAVY, 8.5, ec=BLUE)
ax.add_patch(Rectangle((2.9, 4.1), 14.0, 0.22, fc=BLUE, ec=BLUE))
box(ax, 3.3, 2.6, 2.4, 1.0, "GATE\nflow + P", BLUE, fs=8)
box(ax, 6.4, 2.6, 1.8, 1.0, "EAR-A", GREEN, fs=8); box(ax, 13.6, 2.6, 1.8, 1.0, "EAR-B", GREEN, fs=8)
ax.add_patch(Circle((10.4, 4.21), 0.32, fc=RED, ec="white")); ax.text(10.4, 5.0, "needle-valve leak\n(1.5 mm orifice, 2 bar ≈ 1.3 L/min)", ha="center", color=RED, fontsize=8)
ax.annotate("", (7.3, 1.9), (14.5, 1.9), arrowprops=dict(arrowstyle="<->", color=NAVY)); ax.text(10.9, 1.45, "8 m between nodes · 10 m of 25 mm HDPE/PVC", ha="center", fontsize=8.5, color=NAVY)
box(ax, 17.0, 3.0, 2.7, 1.6, "Laptop:\ngateway +\ndashboard", ORANGE, fs=8)
ax.text(10, 0.5, "Move the valve along the pipe → the pin on the dashboard map moves · close it → alert clears", ha="center", fontsize=8.5, color=GREY)
fig.tight_layout(); fig.savefig(f"{OUT}/fig_rig.png", dpi=170); plt.close(fig)
print("diagrams done")
