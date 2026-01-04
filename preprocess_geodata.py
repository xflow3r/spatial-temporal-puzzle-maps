import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point
import json

states = gpd.read_file('geoData/ne_110m_admin_1_states_provinces.json')
states = states.sort_values('name').reset_index(drop=True)  # Add this line

n_states = len(states)
adjacency = np.full((n_states, n_states), -1, dtype=int)

# First pass: mark adjacencies (symmetric)
for i in range(n_states):
    for j in range(i + 1, n_states):
        if states.iloc[i].geometry.touches(states.iloc[j].geometry) or states.iloc[i].geometry.intersects(
                states.iloc[j].geometry):
            adjacency[i, j] = 1
            adjacency[j, i] = 1

# After the first pass (line after adjacency[j, i] = 1)
tx_idx = states[states['name'] == 'Texas'].index[0]
nm_idx = states[states['name'] == 'New Mexico'].index[0]
print(f"After first pass - Texas-NM: {adjacency[tx_idx, nm_idx]}, NM-Texas: {adjacency[nm_idx, tx_idx]}")


# Second pass: add directions (don't overwrite, skip if already has neighbor)
states_projected = states.to_crs('EPSG:5070')
centroids = states_projected.geometry.centroid

for i in range(n_states):
    for j in range(n_states):
        if adjacency[i, j] == 1:  # Only process neighbors
            dx = centroids.iloc[j].x - centroids.iloc[i].x
            dy = centroids.iloc[j].y - centroids.iloc[i].y

            angle = np.arctan2(dy, dx)
            angle_deg = np.degrees(angle)
            if angle_deg < 0:
                angle_deg += 360

            if angle_deg < 22.5 or angle_deg >= 337.5:
                direction = 5
            elif angle_deg < 67.5:
                direction = 2
            elif angle_deg < 112.5:
                direction = 1
            elif angle_deg < 157.5:
                direction = 0
            elif angle_deg < 202.5:
                direction = 3
            elif angle_deg < 247.5:
                direction = 6
            elif angle_deg < 292.5:
                direction = 7
            else:
                direction = 8

            adjacency[i, j] = direction

# After the second pass (at the very end before np.save)
print(f"After second pass - Texas-NM: {adjacency[tx_idx, nm_idx]}, NM-Texas: {adjacency[nm_idx, tx_idx]}")


np.save('geoData/adjacency_matrix.npy', adjacency)