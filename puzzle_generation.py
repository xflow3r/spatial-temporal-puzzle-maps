import json
import numpy as np
from typing import Dict, List, Tuple, Any


def create_color_scheme(n_classes=7):
    colors = [
        "#f2f0f7",
        "#dadaeb",
        "#bcbddc",
        "#9e9ac8",
        "#807dba",
        "#6a51a3",
        "#4a1486"
    ]
    return colors[:n_classes]


def normalize_value_to_color(value, min_val, max_val, color_scheme):
    if max_val == min_val:
        return color_scheme[len(color_scheme) // 2]

    normalized = (value - min_val) / (max_val - min_val)
    color_index = int(normalized * (len(color_scheme) - 1))
    color_index = max(0, min(len(color_scheme) - 1, color_index))

    return color_scheme[color_index]


def get_perimeter_positions(grid_size=5):
    positions = []
    positions.append((grid_size - 1, 0))

    for row in range(grid_size - 2, 0, -1):
        positions.append((row, grid_size - 1))

    positions.append((0, grid_size - 1))

    for col in range(grid_size - 2, 0, -1):
        positions.append((0, col))

    positions.append((0, 0))

    for row in range(1, grid_size - 1):
        positions.append((row, 0))

    for col in range(1, grid_size - 1):
        positions.append((grid_size - 1, col))

    positions.append((grid_size - 1, grid_size - 1))

    return positions


def calculate_connection_point(current_value, prev_value):
    if prev_value is None:
        return "middle"

    change_rate = (current_value - prev_value) / prev_value

    if abs(change_rate) < 0.02:
        return "middle"
    elif change_rate > 0:
        return "inner"
    else:
        return "outer"


def select_years_for_pieces(years_data, n_pieces=16):
    sorted_years = sorted(years_data.items())

    if len(sorted_years) <= n_pieces:
        return sorted_years
    else:
        return sorted_years[:n_pieces]


def create_puzzle_for_state(state_data, tilemap_position,
                            global_min, global_max, color_scheme):
    state_name = state_data['State']
    deaths_by_year = state_data['deaths_by_year']

    selected_years = select_years_for_pieces(deaths_by_year, n_pieces=16)
    perimeter_positions = get_perimeter_positions(grid_size=5)

    pieces = []
    prev_value = None

    for i, (year, value) in enumerate(selected_years):
        grid_row, grid_col = perimeter_positions[i]
        color = normalize_value_to_color(value, global_min, global_max, color_scheme)
        connection_point = calculate_connection_point(value, prev_value)

        change_rate = None
        if prev_value is not None:
            change_rate = (value - prev_value) / prev_value

        piece = {
            "year": int(year),
            "value": int(value),
            "color": color,
            "grid_position": [grid_row, grid_col],
            "connection_point": connection_point,
            "change_rate": round(change_rate, 4) if change_rate is not None else None
        }

        pieces.append(piece)
        prev_value = value

    values = [p["value"] for p in pieces]
    stats = {
        "min": int(min(values)),
        "max": int(max(values)),
        "mean": round(np.mean(values), 2),
        "trend": "increasing" if values[-1] > values[0] else "decreasing"
    }

    puzzle = {
        "tile_position": tilemap_position,
        "pieces": pieces,
        "stats": stats
    }

    return puzzle


def load_cancer_data(filepath="cancerData/cancer_data_2004_2020.csv"):
    from preprocess_dataset import load_dataset
    data = load_dataset(print_dataset=False, save_processed=False)
    return data


def generate_puzzle_tiles(cancer_data_path="cancerData/cancer_data_2004_2020.csv",
                          tilemap_path="outputs/final_tilemap.json",
                          output_path="outputs/puzzle_tiles.json"):
    cancer_data = load_cancer_data(cancer_data_path)

    with open(tilemap_path, 'r') as f:
        tilemap = json.load(f)

    all_values = []
    for state_data in cancer_data:
        all_values.extend(state_data['deaths_by_year'].values())

    global_min = min(all_values)
    global_max = max(all_values)

    color_scheme = create_color_scheme(n_classes=7)

    puzzle_tiles = {}

    for state_data in cancer_data:
        state_name = state_data['State']

        if state_name not in tilemap:
            continue

        tilemap_position = tilemap[state_name]

        puzzle = create_puzzle_for_state(
            state_data,
            tilemap_position,
            global_min,
            global_max,
            color_scheme
        )

        puzzle_tiles[state_name] = puzzle

    with open(output_path, 'w') as f:
        json.dump(puzzle_tiles, f, indent=2)

    return puzzle_tiles


if __name__ == "__main__":
    puzzle_tiles = generate_puzzle_tiles()