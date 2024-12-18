import numpy as np
import matplotlib.pyplot as plt

import numpy as np
import scipy.stats as stats
import uproot
import matplotlib.pyplot as plt
from sklearn.neighbors import KernelDensity

# Load the ROOT file and the tree
file_path = "../../../../output_root/v1_v2_comparison/NMSSM_X300_Y60.root"
tree_name = "DiphotonTree/data_125_13TeV_NOTAG/"
with uproot.open(file_path) as file:
    tree = file[tree_name]
    data = tree["pt"].array(library="np")


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# Analytical KDE function
def kde_analytical(data, x_grid, bandwidth):
    n = len(data)
    density = np.zeros_like(x_grid)
    
    # Gaussian Kernel
    for x in x_grid:
        kernel_vals = np.exp(-0.5 * ((x - data) / bandwidth) ** 2)
        density[np.where(x_grid == x)] = np.sum(kernel_vals) / (n * bandwidth * np.sqrt(2 * np.pi))
    
    return density

# Generate the x-axis grid for KDE
x_grid = np.linspace(data.min() - 10, data.max() + 10, 1000)

# Initial bandwidth value
initial_bandwidth = 10

# Compute the initial KDE
density = kde_analytical(data, x_grid, initial_bandwidth)

# Create the figure and axis
fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.25)  # Leave space for the slider

# Plot the histogram and initial KDE
hist = ax.hist(data, bins=500, density=True, alpha=0.6, color="g", label="Data")
kde_line, = ax.plot(x_grid, density, color="red", label=f"KDE (bw={initial_bandwidth})")
ax.set_xlabel("pt")
ax.set_ylabel("Density")
ax.set_title("Interactive KDE with Bandwidth Slider")
ax.legend()

# Add a slider for bandwidth adjustment
ax_bandwidth = plt.axes([0.25, 0.1, 0.65, 0.03])  # [left, bottom, width, height]
slider_bandwidth = Slider(ax_bandwidth, 'Bandwidth', 0.1, 100, valinit=initial_bandwidth, valstep=0.1)

# Update function for the slider
def update(val):
    bandwidth = slider_bandwidth.val
    density = kde_analytical(data, x_grid, bandwidth)
    kde_line.set_ydata(density)  # Update the KDE line
    kde_line.set_label(f"KDE (bw={bandwidth:.1f})")
    ax.legend()  # Update the legend
    fig.canvas.draw_idle()  # Redraw the figure

# Connect the slider to the update function
slider_bandwidth.on_changed(update)

plt.show()

