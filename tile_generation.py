import geopandas as gpd
import numpy as np
import json
from PIL import Image, ImageDraw
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point
import matplotlib.pyplot as plt
from collections import deque
import warnings

warnings.filterwarnings('ignore', category=UserWarning)


def identify_connected_regions(geojson_path, adjacency_matrix_path):
    states = gpd.read_file(geojson_path)
    adjacency_matrix = np.load(adjacency_matrix_path)

    us_states = states[states['admin'] == 'United States of America'].copy()
    state_names = us_states['name'].tolist()

    regions = {
        'mainland': [s for s in state_names if s not in ['Alaska', 'Hawaii']],
        'alaska': ['Alaska'] if 'Alaska' in state_names else [],
        'hawaii': ['Hawaii'] if 'Hawaii' in state_names else []
    }

    return regions


def deform_map(geojson_path, connected_regions, adjacency_matrix_path, iterations=0):
    states = gpd.read_file(geojson_path)
    adjacency_matrix = np.load(adjacency_matrix_path)

    deformed_states = states.copy()

    for region_name, state_list in connected_regions.items():
        if len(state_list) == 0:
            continue

        region_states = states[states['name'].isin(state_list)].copy()
        n_states = len(region_states)

        if n_states <= 1:
            continue

        state_names = region_states['name'].tolist()
        centroids = {}
        for idx, row in region_states.iterrows():
            centroids[row['name']] = np.array([row.geometry.centroid.x, row.geometry.centroid.y])

        all_us_states = states[states['admin'] == 'United States of America']['name'].tolist()

        neighbors = {}
        for state in state_names:
            if state not in all_us_states:
                continue
            state_idx = all_us_states.index(state)
            if state_idx >= len(adjacency_matrix):
                continue

            state_neighbors = []
            for other_state in state_names:
                if other_state == state or other_state not in all_us_states:
                    continue
                other_idx = all_us_states.index(other_state)
                if other_idx >= len(adjacency_matrix):
                    continue

                if adjacency_matrix[state_idx, other_idx] != -1 and adjacency_matrix[state_idx, other_idx] != 4:
                    state_neighbors.append(other_state)

            neighbors[state] = state_neighbors

        bounds = region_states.total_bounds
        area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
        s = np.sqrt(area / n_states)

        for iteration in range(iterations):
            new_centroids = {}

            for state in state_names:
                if state not in neighbors or len(neighbors[state]) == 0:
                    new_centroids[state] = centroids[state]
                    continue

                neighbor_centroids = [centroids[n] for n in neighbors[state]]
                g = np.mean(neighbor_centroids, axis=0)

                direction = g - centroids[state]
                if np.linalg.norm(direction) > 0:
                    direction = direction / np.linalg.norm(direction)

                new_centroid = (1.0 / len(neighbors[state])) * sum(
                    centroids[n] + s * direction for n in neighbors[state]
                )

                new_centroids[state] = new_centroid

            centroids = new_centroids

        from shapely.affinity import translate
        for idx, row in region_states.iterrows():
            state_name = row['name']
            old_centroid = np.array([row.geometry.centroid.x, row.geometry.centroid.y])
            new_centroid = centroids[state_name]

            shift = new_centroid - old_centroid
            shifted_geom = translate(row.geometry, xoff=shift[0], yoff=shift[1])

            deformed_states.loc[deformed_states['name'] == state_name, 'geometry'] = shifted_geom

    return deformed_states


def map_to_binary(geojson_path, connected_regions, adjacency_matrix_path, output_dir, resolution=4000):
    deformed_states = deform_map(geojson_path, connected_regions, adjacency_matrix_path)

    binary_images = {}

    for region_name, state_list in connected_regions.items():
        region_states = deformed_states[deformed_states['name'].isin(state_list)]

        if len(region_states) == 0:
            continue

        merged_geometry = region_states.geometry.union_all()

        bounds = merged_geometry.bounds
        minx, miny, maxx, maxy = bounds

        width = resolution
        height = int(resolution * (maxy - miny) / (maxx - minx))

        img = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(img)

        if merged_geometry.geom_type == 'Polygon':
            polygons = [merged_geometry]
        elif merged_geometry.geom_type == 'MultiPolygon':
            polygons = list(merged_geometry.geoms)
        else:
            continue

        for poly in polygons:
            coords = [(int((x - minx) / (maxx - minx) * width),
                       int((maxy - y) / (maxy - miny) * height))
                      for x, y in poly.exterior.coords]
            draw.polygon(coords, fill=255)

        binary_array = np.array(img) > 128
        binary_images[region_name] = {
            'array': binary_array.astype(int),
            'bounds': bounds,
            'states': state_list
        }

        plt.imsave(f'{output_dir}/binary_{region_name}.png', binary_array, cmap='gray')

    return binary_images


def mosaic_filter(binary_images, output_dir):
    initial_tiles = {}

    for region_name, region_data in binary_images.items():
        binary_array = region_data['array']
        n_states = len(region_data['states'])

        if n_states == 0:
            initial_tiles[region_name] = {'tiles': [], 'grid_size': 1, 'states': []}
            continue

        total_pixels = binary_array.size
        land_pixels = np.sum(binary_array)

        if land_pixels == 0:
            initial_tiles[region_name] = {'tiles': [(0, 0)] * n_states, 'grid_size': 1, 'states': region_data['states']}
            continue

        target_grid_size = int(np.sqrt(total_pixels / n_states))

        grid_size = max(1, target_grid_size)
        best_tiles = []
        best_diff = float('inf')

        for iteration in range(500):
            tiles = []
            height, width = binary_array.shape

            if grid_size <= 0:
                grid_size = 1

            n_rows = max(1, height // grid_size)
            n_cols = max(1, width // grid_size)

            for i in range(n_rows):
                for j in range(n_cols):
                    y_start = i * grid_size
                    y_end = min((i + 1) * grid_size, height)
                    x_start = j * grid_size
                    x_end = min((j + 1) * grid_size, width)

                    cell = binary_array[y_start:y_end, x_start:x_end]

                    black_pixels = np.sum(cell)
                    total_cell_pixels = cell.size

                    if black_pixels > total_cell_pixels / 2:
                        tiles.append((i, j))

            diff = abs(len(tiles) - n_states)

            if diff < best_diff:
                best_diff = diff
                best_tiles = tiles.copy()

            if len(tiles) == n_states:
                break

            if len(tiles) > n_states:
                grid_size += 1
            else:
                grid_size -= 1

            if grid_size <= 0:
                grid_size = 1

        while len(best_tiles) < n_states:
            y_coords, x_coords = np.where(binary_array > 0)
            if len(y_coords) > 0:
                cy = int(np.mean(y_coords)) // grid_size
                cx = int(np.mean(x_coords)) // grid_size
                if (cy, cx) not in best_tiles:
                    best_tiles.append((cy, cx))
                else:
                    best_tiles.append((cy + len(best_tiles), cx))
            else:
                best_tiles.append((len(best_tiles), 0))

        while len(best_tiles) > n_states:
            best_tiles.pop()

        initial_tiles[region_name] = {
            'tiles': best_tiles,
            'grid_size': grid_size,
            'states': region_data['states']
        }

    with open(f'{output_dir}/initial_tiles.json', 'w') as f:
        json.dump({k: {'tiles': v['tiles'], 'grid_size': v['grid_size'], 'states': v['states']}
                   for k, v in initial_tiles.items()}, f, indent=2)

    return initial_tiles


def correct_tile_positions(initial_tiles, geojson_path, output_dir):
    states = gpd.read_file(geojson_path)

    main_region_name = max(initial_tiles.keys(), key=lambda k: len(initial_tiles[k]['states']))

    corrected_tiles = {}

    for region_name, region_data in initial_tiles.items():
        tiles = region_data['tiles'].copy()

        if len(tiles) == 0:
            corrected_tiles[region_name] = region_data.copy()
            continue

        tiles_set = set()
        unique_tiles = []
        for tile in tiles:
            if tile not in tiles_set:
                tiles_set.add(tile)
                unique_tiles.append(tile)
            else:
                offset = 0
                while (tile[0] + offset, tile[1]) in tiles_set:
                    offset += 1
                new_tile = (tile[0] + offset, tile[1])
                tiles_set.add(new_tile)
                unique_tiles.append(new_tile)

        tiles = unique_tiles

        connected = set()
        if tiles:
            queue = deque([tiles[0]])
            connected.add(tiles[0])

            while queue:
                current = queue.popleft()
                i, j = current

                neighbors = [(i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)]

                for neighbor in neighbors:
                    if neighbor in tiles and neighbor not in connected:
                        connected.add(neighbor)
                        queue.append(neighbor)

        disconnected = [t for t in tiles if t not in connected]

        for tile in disconnected:
            min_dist = float('inf')
            best_pos = None

            for conn_tile in list(connected):
                ci, cj = conn_tile
                ti, tj = tile

                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_pos = (ci + di, cj + dj)
                    if new_pos not in tiles:
                        dist = abs(new_pos[0] - ti) + abs(new_pos[1] - tj)
                        if dist < min_dist:
                            min_dist = dist
                            best_pos = new_pos

            if best_pos:
                tiles = [t for t in tiles if t != tile]
                tiles.append(best_pos)
                connected.add(best_pos)

        corrected_tiles[region_name] = {
            'tiles': tiles,
            'grid_size': region_data['grid_size'],
            'states': region_data['states']
        }

    if len(corrected_tiles) > 1:
        main_tiles_array = np.array(corrected_tiles[main_region_name]['tiles'])
        min_row = main_tiles_array[:, 0].min()
        max_row = main_tiles_array[:, 0].max()
        max_col = main_tiles_array[:, 1].max()

        offset_row = max_row - min_row + 3
        offset_col = max_col + 3

        region_order = ['alaska', 'hawaii']
        current_offset = 0

        for region_name in region_order:
            if region_name not in corrected_tiles:
                continue

            if region_name == main_region_name:
                continue

            if len(corrected_tiles[region_name]['tiles']) == 0:
                continue

            region_tiles = np.array(corrected_tiles[region_name]['tiles'])

            if region_name == 'alaska':
                shift = np.array([offset_row, -(offset_col // 2)])
            else:
                shift = np.array([offset_row + 2, offset_col])

            shifted_tiles = (region_tiles + shift).astype(int).tolist()
            corrected_tiles[region_name]['tiles'] = shifted_tiles

    with open(f'{output_dir}/corrected_tiles.json', 'w') as f:
        json.dump({k: {'tiles': v['tiles'], 'grid_size': v['grid_size'], 'states': v['states']}
                   for k, v in corrected_tiles.items()}, f, indent=2)

    return corrected_tiles


def optimize_mapping(corrected_tiles, geojson_path, adjacency_matrix_path, output_dir, alpha=0.1):
    states = gpd.read_file(geojson_path)
    adjacency_matrix = np.load(adjacency_matrix_path)

    final_mapping = {}

    for region_name, region_data in corrected_tiles.items():
        region_states = region_data['states']
        region_tiles = region_data['tiles']

        if len(region_states) == 0 or len(region_tiles) == 0:
            continue

        n = len(region_states)

        state_centroids = {}
        for state_name in region_states:
            state_geom = states[states['name'] == state_name].geometry.iloc[0]
            state_centroids[state_name] = np.array([state_geom.centroid.x, state_geom.centroid.y])

        cost_matrix = np.zeros((n, n))

        directions = {
            0: (-1, -1), 1: (0, -1), 2: (1, -1),
            3: (-1, 0), 4: (0, 0), 5: (1, 0),
            6: (-1, 1), 7: (0, 1), 8: (1, 1)
        }

        all_us_states = states[states['admin'] == 'United States of America']['name'].tolist()

        for i in range(n):
            state_i = region_states[i]
            centroid_i = state_centroids[state_i]

            for j in range(n):
                tile_j = np.array(region_tiles[j])

                distance = np.linalg.norm(centroid_i - tile_j)

                orientation_cost = 0
                count = 0

                for k in range(n):
                    if i == k:
                        continue

                    state_k = region_states[k]

                    if state_i not in all_us_states or state_k not in all_us_states:
                        continue

                    i_global = all_us_states.index(state_i)
                    k_global = all_us_states.index(state_k)

                    if i_global >= len(adjacency_matrix) or k_global >= len(adjacency_matrix):
                        continue

                    adj_value = adjacency_matrix[i_global, k_global]

                    if adj_value == 4 or adj_value == -1 or adj_value < 0 or adj_value > 8:
                        continue

                    expected_dir = np.array(directions[int(adj_value)])

                    tile_k = np.array(region_tiles[k])
                    actual_dir = tile_k - tile_j

                    if np.linalg.norm(actual_dir) > 0:
                        actual_dir_norm = actual_dir / np.linalg.norm(actual_dir)
                    else:
                        actual_dir_norm = np.array([0, 0])

                    if np.linalg.norm(expected_dir) > 0:
                        expected_dir_norm = expected_dir / np.linalg.norm(expected_dir)
                    else:
                        expected_dir_norm = np.array([0, 0])

                    orientation_cost += np.linalg.norm(expected_dir_norm - actual_dir_norm)
                    count += 1

                if count > 0:
                    orientation_cost /= count

                cost_matrix[i, j] = alpha * distance + (1 - alpha) * orientation_cost

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        for i, j in zip(row_ind, col_ind):
            final_mapping[region_states[i]] = tuple(region_tiles[j])

    with open(f'{output_dir}/final_tilemap.json', 'w') as f:
        json.dump(final_mapping, f, indent=2)

    return final_mapping


def generate_tilemap(geojson_path='geoData/ne_110m_admin_1_states_provinces.json',
                     adjacency_matrix_path='geoData/adjacency_matrix.npy',
                     output_dir='outputs'):
    import os
    os.makedirs(output_dir, exist_ok=True)

    print("Step 0: Identifying connected regions...")
    connected_regions = identify_connected_regions(geojson_path, adjacency_matrix_path)

    print("Step 1: Converting map to binary images...")
    binary_images = map_to_binary(geojson_path, connected_regions, adjacency_matrix_path, output_dir)

    print("Step 2: Applying mosaic filter...")
    initial_tiles = mosaic_filter(binary_images, output_dir)

    print("Step 3: Correcting tile positions...")
    corrected_tiles = correct_tile_positions(initial_tiles, geojson_path, output_dir)

    print("Step 4: Optimizing district-to-tile mapping...")
    final_mapping = optimize_mapping(corrected_tiles, geojson_path, adjacency_matrix_path, output_dir)

    print("Tile map generation complete!")
    return final_mapping


if __name__ == "__main__":
    final_mapping = generate_tilemap()