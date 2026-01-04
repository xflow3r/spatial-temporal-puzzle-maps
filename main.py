import os
import sys


def run_pipeline():
    print("Running pipeline...")

    try:
        from preprocess_dataset import load_dataset
        cancer_data = load_dataset(print_dataset=False, save_processed=True)
    except Exception as e:
        print(f"Error in preprocessing: {e}")
        return False

    try:
        from tile_generation import generate_tilemap
        final_mapping = generate_tilemap()
    except Exception as e:
        print(f"Error in tile generation: {e}")
        return False

    try:
        from puzzle_generation import generate_puzzle_tiles
        puzzle_tiles = generate_puzzle_tiles()
    except Exception as e:
        print(f"Error in puzzle generation: {e}")
        return False

    print("Pipeline complete. Starting server at http://localhost:8050")

    try:
        from visualization import app
        app.run(debug=False, port=8050)
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error in visualization: {e}")
        return False

    return True


if __name__ == "__main__":
    success = run_pipeline()
    if not success:
        sys.exit(1)