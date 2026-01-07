# spatial-temporal-puzzle-maps
Automatic generation of puzzle tile maps for spatial-temporal data visualization. Python implementation of Lin et al. (2019) methodology for visualizing geographic time-series data.

# Puzzle Tile Maps for Spatial-Temporal Data Visualization

## Project Overview

This project implements an automatic generation system for puzzle tile maps to visualize spatial-temporal data, based on the methodology described by Lin et al. (2019). The system creates interactive visualizations that display geographic data changing over time in a single, readable 2D view without losing important temporal details.

**Dataset**: USA Cancer Mortality Dataset (CDC WONDER Database)
- Source: https://wonder.cdc.gov/cancermort-v2021.html
- Description: Age-adjusted death rates for cancer across U.S. states from 2004-2021

## Demo & Resources

- **Live Demo**: https://xflower.eu.pythonanywhere.com/(https://xflower.eu.pythonanywhere.com/) <!-- Add your deployment URL here -->
- **Reference Paper**: Lin et al. (2019) - "Automatic generation of puzzle tile maps for spatial-temporal data visualization"

## Features

- **Automatic Tile Map Generation**: Converts geographic maps into grid-based tile layouts
- **Puzzle Piece Visualization**: Represents time-series data as connected puzzle pieces
- **Interactive Dashboard**: Built with Dash/Plotly for exploring state-level cancer mortality trends
- **Temporal Trend Encoding**: Connection points between puzzle pieces indicate data trends (increasing/decreasing)
- **Color-Coded Data**: Sequential color scheme represents death rate magnitudes
- **Non-Contiguous Region Support**: Handles Alaska and Hawaii separately from mainland states

## System Architecture

The pipeline consists of four main stages:

### 1. Data Preprocessing (`preprocess_dataset.py`, `preprocess_geodata.py`)
- Loads cancer mortality and population data
- Calculates death rates per 100,000 population
- Processes GeoJSON data for US state boundaries
- Creates adjacency matrix for state connectivity
- Identifies connected regions (mainland, Alaska, Hawaii)

### 2. Tile Map Generation (`tile_generation.py`)
- Converts geographic map to binary image
- Applies mosaic filtering to generate initial tile positions
- Corrects tile positions using first-order neighborhood algorithm
- Optimizes district-to-tile mapping using Hungarian algorithm
- Handles non-contiguous regions

### 3. Puzzle Generation (`puzzle_generation.py`)
- Creates puzzle pieces for each state tile (16 pieces per tile)
- Applies color encoding based on death rates
- Calculates connection points between pieces showing temporal trends
- Generates statistics for each state

### 4. Interactive Visualization (`visualization.py`)
- Creates overview map with all state tiles
- Implements click-to-detail functionality
- Shows temporal progression within each tile
- Displays connection point markers indicating trend changes

## Installation & Setup

### Prerequisites
```bash
Python 3.8+
pip (Python package manager)
```

### Required Libraries
```bash
pip install requirements.txt
```

### Running the Complete Pipeline

```bash
python main.py
```