import matplotlib.pyplot as plt

# ============================================================
# Mass grid definition
# ============================================================

mass_points = {
    300: [90, 95, 100, 125, 150, 170],
    320: [90, 95, 100, 125, 150, 170],
    350: [90, 95, 100, 125, 150, 170, 200],
    400: [90, 95, 100, 125, 150, 170, 200, 250],
    450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
    500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    600: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450],
    650: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500],
    700: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550],
    750: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600],
    800: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650],
    850: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    900: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700],
    950: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
    1000: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800],
}

# ============================================================
# Color palette
# ============================================================

dark_colors = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
    '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
    '#bcbd22', '#17becf', '#393b79', '#637939',
    '#8c6d31', '#843c39', '#7b4173', '#3182bd'
]

unique_y_values = sorted({y for ys in mass_points.values() for y in ys})
y_color_map = {y: dark_colors[i % len(dark_colors)]
               for i, y in enumerate(unique_y_values)}

# ============================================================
# Plot
# ============================================================

plt.figure(figsize=(10, 7))

# Plot sorted for visual consistency
for mX in sorted(mass_points.keys()):
    for mY in sorted(mass_points[mX]):
        plt.scatter(
            mX,
            mY,
            color=y_color_map[mY],
            s=70,
            edgecolor='black',
            linewidth=0.6,
            alpha=0.9
        )

# Axis labels
plt.xlabel(r'$m_X$ (Spin-0) [GeV]', fontsize=15, loc='right')
plt.ylabel(r'$m_Y$ [GeV]', fontsize=15, loc='top')



# Limits
plt.xlim(250, 1050)
plt.ylim(80, 850)

# Grid
# plt.grid(True, linestyle='--', alpha=0.4)
plt.grid(False)

# Legend
handles = [
    plt.Line2D(
        [0], [0],
        marker='o',
        color='w',
        markerfacecolor=y_color_map[y],
        markeredgecolor='black',
        markersize=8,
        label=str(y)
    )
    for y in unique_y_values
]

plt.legend(
    handles=handles,
    title=r'$m_Y$ [GeV]',
    title_fontsize=12,
    fontsize=10,
    markerscale=1.3,
    handlelength=1.5,
    labelspacing=0.5,
    bbox_to_anchor=(1.02, 1),
    loc='upper left',
    frameon=True
)

plt.tight_layout()

# Save high-resolution
output_path = "/afs/cern.ch/user/s/sraj/sraj/www/CUA/HH-bbgg/all_plots/grid_point_mx_1000_dark"
plt.savefig(output_path + ".png", dpi=300)
plt.savefig(output_path + ".pdf")

# plt.show()
print(f"Plot saved to: {output_path}.png and {output_path}.pdf")
print("Plotting complete.")