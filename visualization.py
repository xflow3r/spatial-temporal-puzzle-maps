import json
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import numpy as np

TILE_SIZE = 120
PIECE_SIZE = TILE_SIZE / 5
SPACING = 5

app = dash.Dash(__name__)


def load_data():
    with open('outputs/puzzle_tiles.json', 'r') as f:
        puzzle_tiles = json.load(f)
    return puzzle_tiles


def get_connection_point_offset(connection_type):
    if connection_type == "inner":
        return 0.3
    elif connection_type == "outer":
        return 0.7
    else:
        return 0.5


def create_puzzle_piece(piece, piece_size, offset_x, offset_y):
    row, col = piece['grid_position']
    x = offset_x + col * piece_size
    y = offset_y + row * piece_size

    rect = go.Scatter(
        x=[x, x + piece_size, x + piece_size, x, x],
        y=[y, y, y + piece_size, y + piece_size, y],
        fill='toself',
        fillcolor=piece['color'],
        line=dict(color='black', width=1),
        mode='lines',
        hoverinfo='text',
        hovertext=f"Year: {piece['year']}<br>Deaths: {piece['value']}<br>Change: {piece['change_rate'] * 100 if piece['change_rate'] else 0:.1f}%",
        showlegend=False
    )

    shapes = [rect]

    if piece['connection_point'] != 'middle':
        offset = get_connection_point_offset(piece['connection_point'])

        if col == 0:
            dot_x = x + piece_size * 0.1
            dot_y = y + piece_size * offset
        elif col == 4:
            dot_x = x + piece_size * 0.9
            dot_y = y + piece_size * offset
        elif row == 0:
            dot_x = x + piece_size * offset
            dot_y = y + piece_size * 0.1
        elif row == 4:
            dot_x = x + piece_size * offset
            dot_y = y + piece_size * 0.9
        else:
            dot_x = x + piece_size * offset
            dot_y = y + piece_size * offset

        dot = go.Scatter(
            x=[dot_x],
            y=[dot_y],
            mode='markers',
            marker=dict(size=4, color='white', line=dict(color='black', width=1)),
            hoverinfo='skip',
            showlegend=False
        )
        shapes.append(dot)

    return shapes


def create_tile(state_name, puzzle_data, tile_row, tile_col):
    offset_x = tile_col * (TILE_SIZE + SPACING)
    offset_y = tile_row * (TILE_SIZE + SPACING)

    shapes = []
    for piece in puzzle_data['pieces']:
        piece_shapes = create_puzzle_piece(piece, PIECE_SIZE, offset_x, offset_y)
        shapes.extend(piece_shapes)

    center_x = offset_x + TILE_SIZE / 2
    center_y = offset_y + TILE_SIZE / 2

    text = go.Scatter(
        x=[center_x],
        y=[center_y],
        mode='text',
        text=[state_name],
        textfont=dict(size=10, color='black', family='Arial Black'),
        hoverinfo='text',
        hovertext=f"{state_name}<br>Click for details",
        showlegend=False,
        customdata=[[state_name]]
    )
    shapes.append(text)

    invisible_rect = go.Scatter(
        x=[offset_x, offset_x + TILE_SIZE, offset_x + TILE_SIZE, offset_x, offset_x],
        y=[offset_y, offset_y, offset_y + TILE_SIZE, offset_y + TILE_SIZE, offset_y],
        fill='toself',
        fillcolor='rgba(0,0,0,0)',
        line=dict(color='rgba(0,0,0,0)', width=0),
        mode='lines',
        hoverinfo='text',
        hovertext=f"{state_name}<br>Click for details",
        showlegend=False,
        customdata=[[state_name]]
    )
    shapes.append(invisible_rect)

    return shapes


def create_overview_map(puzzle_tiles):
    all_shapes = []

    max_row = max([data['tile_position'][0] for data in puzzle_tiles.values()])
    max_col = max([data['tile_position'][1] for data in puzzle_tiles.values()])

    for state_name, puzzle_data in puzzle_tiles.items():
        tile_row, tile_col = puzzle_data['tile_position']
        tile_shapes = create_tile(state_name, puzzle_data, tile_row, tile_col)
        all_shapes.extend(tile_shapes)

    width = (max_col + 1) * (TILE_SIZE + SPACING) + 300
    height = (max_row + 1) * (TILE_SIZE + SPACING) + 100

    return all_shapes, width, height


def create_color_legend(puzzle_tiles):
    all_values = []
    for puzzle_data in puzzle_tiles.values():
        all_values.extend([p['value'] for p in puzzle_data['pieces']])

    min_val = min(all_values)
    max_val = max(all_values)

    from puzzle_generation import create_color_scheme
    color_scheme = create_color_scheme(n_classes=7)

    legend_items = []
    for i, color in enumerate(color_scheme):
        val_min = min_val + (max_val - min_val) * i / len(color_scheme)
        val_max = min_val + (max_val - min_val) * (i + 1) / len(color_scheme)

        legend_items.append(
            html.Div([
                html.Div(style={
                    'width': '50px',
                    'height': '30px',
                    'backgroundColor': color,
                    'border': '1px solid black',
                    'display': 'inline-block',
                    'marginRight': '15px'
                }),
                html.Span(f"{int(val_min)} - {int(val_max)}", style={'fontSize': '16px'})
            ], style={'marginBottom': '8px'})
        )

    return html.Div([
        html.H4("Deaths per Year", style={'fontSize': '18px', 'marginBottom': '15px'}),
        html.Div(legend_items)
    ], style={
        'position': 'absolute',
        'top': '20px',
        'right': '20px',
        'backgroundColor': 'white',
        'padding': '20px',
        'border': '2px solid black',
        'borderRadius': '5px',
        'zIndex': '1000'
    })


def create_detail_view(state_name, puzzle_data):
    if not puzzle_data:
        return None

    detail_shapes = []
    offset_x = 50
    offset_y = 50
    detail_piece_size = 60

    for piece in puzzle_data['pieces']:
        piece_shapes = create_puzzle_piece(piece, detail_piece_size, offset_x, offset_y)
        detail_shapes.extend(piece_shapes)

    fig = go.Figure(data=detail_shapes)

    fig.update_layout(
        title=f"{state_name} - Cancer Mortality (2005-2020)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 400]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 400]),
        plot_bgcolor='white',
        width=500,
        height=500,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    stats = puzzle_data['stats']
    stats_text = f"""
    **Statistics:**
    - Min: {stats['min']} deaths
    - Max: {stats['max']} deaths
    - Mean: {stats['mean']} deaths
    - Trend: {stats['trend']}
    """

    return html.Div([
        html.Div([
            html.H3(f"{state_name}", style={'marginBottom': '20px'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False}),
            dcc.Markdown(stats_text, style={'marginTop': '20px', 'fontSize': '14px'}),
            html.Button('Close', id={'type': 'close-button', 'index': state_name}, n_clicks=0, style={
                'marginTop': '20px',
                'padding': '10px 20px',
                'fontSize': '16px',
                'cursor': 'pointer',
                'backgroundColor': '#333',
                'color': 'white',
                'border': 'none',
                'borderRadius': '5px'
            })
        ], style={
            'position': 'relative',
            'backgroundColor': 'white',
            'padding': '30px',
            'borderRadius': '10px',
            'maxWidth': '600px',
            'margin': 'auto'
        })
    ], style={
        'position': 'fixed',
        'top': '0',
        'left': '0',
        'width': '100%',
        'height': '100%',
        'backgroundColor': 'rgba(0, 0, 0, 0.7)',
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'zIndex': '2000'
    })


puzzle_tiles = load_data()
overview_shapes, map_width, map_height = create_overview_map(puzzle_tiles)

app.layout = html.Div([
    html.H1("USA Cancer Mortality Puzzle Tile Map (2005-2020)",
            style={'textAlign': 'center', 'marginBottom': '30px'}),

    create_color_legend(puzzle_tiles),

    html.Div([
        dcc.Graph(
            id='tile-map',
            config={'displayModeBar': False},
            style={'width': f'{map_width}px', 'height': f'{map_height}px', 'margin': 'auto'}
        )
    ], style={'position': 'relative'}),

    html.Div(id='detail-modal', children=[])
])


@app.callback(
    Output('tile-map', 'figure'),
    Input('tile-map', 'id')
)
def update_map(_):
    fig = go.Figure(data=overview_shapes)

    all_rows = [data['tile_position'][0] for data in puzzle_tiles.values()]
    all_cols = [data['tile_position'][1] for data in puzzle_tiles.values()]

    min_row = min(all_rows)
    max_row = max(all_rows)
    min_col = min(all_cols)
    max_col = max(all_cols)

    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[min_col * (TILE_SIZE + SPACING) - SPACING, (max_col + 1) * (TILE_SIZE + SPACING)]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[(max_row + 1) * (TILE_SIZE + SPACING), min_row * (TILE_SIZE + SPACING) - SPACING],
            scaleanchor="x",
            scaleratio=1
        ),
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=5, b=5),
        hovermode='closest'
    )

    return fig


app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            return [];
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('detail-modal', 'children', allow_duplicate=True),
    Input({'type': 'close-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
    prevent_initial_call=True
)


@app.callback(
    Output('detail-modal', 'children'),
    Input('tile-map', 'clickData'),
    prevent_initial_call=True
)
def handle_click(clickData):
    if clickData and 'points' in clickData:
        point = clickData['points'][0]
        if 'customdata' in point and point['customdata']:
            state_name = point['customdata'][0]
            if isinstance(state_name, list):
                state_name = state_name[0]
            if state_name in puzzle_tiles:
                return create_detail_view(state_name, puzzle_tiles[state_name])

    return []


if __name__ == '__main__':
    app.run(debug=True, port=8050)