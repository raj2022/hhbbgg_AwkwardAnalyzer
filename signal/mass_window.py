import os
import pandas as pd
import matplotlib.pyplot as plt

m_H = 125  # Mass of Higgs

def mass_window(m_bb, m_gg, m_bbgg, m_y):
    m_x = m_bbgg - (m_gg - m_H) - (m_bb - m_y)
    return m_x



# Define X values with their corresponding Y values
x_values = {
    300: [90, 95, 100, 125, 150, 170],
    320: [90, 95, 100, 125, 150, 170],
    350: [90, 95, 100, 125, 150, 170, 200],
    400: [90, 95, 100, 125, 150, 170, 200],
    450: [90, 95, 100, 125, 150, 170, 200, 250, 300],
    500: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350],
    550: [90, 95, 100, 125, 150, 170, 200, 250, 300, 350, 400],
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

def find_lower_higher_x(mX, x_values):
    """Find the closest lower and higher X values for a given mX."""
    sorted_x = sorted(x_values.keys())  # Sort X values
    lower_x, higher_x = None, None

    for x in sorted_x:
        if x <= mX:
            lower_x = x
        if x >= mX and higher_x is None:
            higher_x = x
            break  # Stop once we find the first X greater than mX

    return lower_x, higher_x

def find_lower_higher_y_for_mX(mX, x_values):
    """Find the lowest and highest Y values for the lower and higher X surrounding mX."""
    # Step 1: Find lower and higher X values
    lower_x, higher_x = find_lower_higher_x(mX, x_values)

    # Step 2: Get the Y values for these X values
    y_values_lowX = x_values.get(lower_x, [])
    y_values_highX = x_values.get(higher_x, [])

    # Step 3: Find min and max Y in these sets
    min_y = min(y_values_lowX + y_values_highX) if y_values_lowX and y_values_highX else None
    max_y = max(y_values_lowX + y_values_highX) if y_values_lowX and y_values_highX else None

    return lower_x, higher_x, min_y, max_y

# Example Usage
mX = 750  # Given mX

# Find the bounding Y values
lower_x, higher_x, min_y, max_y = find_lower_higher_y_for_mX(mX, x_values)

print(f"For mX = {mX}:")
print(f" - Lower X: {lower_x}")
print(f" - Higher X: {higher_x}")
print(f" - Minimum Y in range: {min_y}")
print(f" - Maximum Y in range: {max_y}")



# Extract min and max Y values for each X
for x, y_values in x_values.items():
    min_y = min(y_values)
    max_y = max(y_values)
    print(f"X = {x}, Min Y = {min_y}, Max Y = {max_y}")

## import these variables m_bb, m_gg, m_bbgg from the parquet.