import geopandas as gpd
import dash_leaflet as dl
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_daq as daq
import plotly.express as px
import pandas as pd
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash.exceptions import PreventUpdate
import os
import dash_bootstrap_components as dbc
from datetime import datetime
import numpy as np
from dash import callback_context

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://fonts.googleapis.com/css?family=Roboto:900&display=swap'])

# Load and preprocess the updated data
file_path = './src/data/updated_mobility_data.csv'
combined_data = pd.read_csv(file_path)

# Convert 'Day' and 'Hours' to datetime and create a new column for filtering
combined_data['DateTime'] = pd.to_datetime(combined_data['Day'] + ' ' + combined_data['Hours'], format='%B %d, %Y %H:%M')

# Format the slider labels
def format_datetime_label(dt):
    if f"{dt.strftime('%H:%M')}" == "00:00":
        return f"{dt.strftime('%d %b')} (1)"
    elif f"{dt.strftime('%H:%M')}" == "08:00":
        return f"{dt.strftime('%d %b')} (2)"
    else:
        return f"{dt.strftime('%d %b')} (3)"

# Ensure the slider marks are ordered by date
sorted_datetimes = combined_data['DateTime'].sort_values().unique()
slider_marks = {i: {'label': format_datetime_label(date), 'style': {'font-size': '10px', 'max-width': '45px', 'text-align': 'center', 'white-space': 'nowrap'}} for i, date in enumerate(sorted_datetimes)}

# Learn More content
content = html.Div([
    html.H5("What is the purpose of this dashboard?", style={'color': '#00008B'}),
    html.P("This dashboard aims to visualize mobility data over time, showing the count of people moving from various source to destination categories."),
    html.H5("How to use the dashboard?", style={'color': '#00008B'}),
    html.P("Use the filters to select different source and destination categories. The map will update to show the routes and points accordingly."),
    html.H5("Have any questions?", style={'color': '#00008B'}),
    html.P([
        "Feel free to reach out to  Zainab Akhtar, at ",
        html.A("zakhtar@alumni.cmu.edu", href="mailto:zakhtar@alumni.cmu.edu")
    ])
])

# Create layout
app.layout = html.Div(
    className="pretty_container",
    children=[
        # Header and Hidden Content
        html.Div(
            id="header",
            children=[
                html.Div(
                    [html.H1(children="COVID-19 Point Mobility Data Visualization", style={"fontFamily": "'Roboto', sans-serif", "fontWeight": "900", "fontSize": "39px"})],
                    style={"display": "inline-block", "width": "70%", "margin-left": "10px"}              
                ),
                dbc.Collapse(
                    content,
                    style={'padding-left': '15px','padding-right': '50px'},
                    id="collapse",
                ),
                # Learn More Button
                html.Div(
                    [
                        dbc.Button(
                            "Learn more",
                            id="collapse-button", # Refer to callback function
                            className="mb-3",
                            style={"background-color": "white", "color": "steelblue",  "margin-left": "10px"},
                        )
                    ],
                    style={"display": "inline-block", "width": "100%", "textAlign": "left", "margin-bottom": "15px"}
                ),
            ],
        ),
        html.Div([
            html.Div([
                html.Label('Source Category'),
                dcc.Dropdown(
                    id='source-category-dropdown',
                    options=[{'label': cat, 'value': cat} for cat in combined_data['Source Category'].unique()],
                    value=combined_data['Source Category'].unique()[0]
                )
            ], style={'width': '48%', 'display': 'inline-block'}),
            html.Div([
                html.Label('Destination Category'),
                dcc.Dropdown(
                    id='destination-category-dropdown',
                    options=[{'label': cat, 'value': cat} for cat in combined_data['Destination Category'].unique()],
                    value=combined_data['Destination Category'].unique()[0]
                )
            ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
        ]),
        html.Div([
            html.Div(
                children=[
                    html.Span(
                        "Map Information",
                        style={"font-size": "12px", "vertical-align": "middle"}
                    ),
                    html.Span(
                        "?",
                        id="map-info-tooltip",
                        style={"display": "inline-block", "text-align": "center", "color": "white", "backgroundColor": "black", "borderRadius": "50%", "width": "18px", "height": "18px", "line-height": "18px", "marginLeft": "10px", "cursor": "pointer"},
                    ),
                    dbc.Tooltip(
                        "Use the filters to select different source and destination categories as well as the relevant date/time from the slider. For the slider (1) represents the first 8 hours of the day, (2) is for the second part and (3) is for the last part of the day.",
                        target="map-info-tooltip",
                    ),
                ],
                style={"textAlign": "right", "padding": "10px"}
            ),
        ]),
        dl.Map([
            dl.TileLayer(),
            dl.LayerGroup(id="route-layer")
        ], style={'width': '100%', 'height': '700px'}, center=[20.5937, 78.9629], zoom=8),
        html.Div(style={'margin-top': '20px'}),  # Add space between the map and slider
        dcc.Slider(
            id='datetime-slider',
            min=0,
            max=len(sorted_datetimes)-1,
            value=0,
            marks=slider_marks,
            step=None
        )
    ]
)

# Update map layers based on datetime, source, and destination categories
@app.callback(
    Output("route-layer", "children"),
    [
        Input("datetime-slider", "value"),
        Input("source-category-dropdown", "value"),
        Input("destination-category-dropdown", "value")
    ]
)
def update_map(datetime_index, source_category, destination_category):
    selected_datetime = sorted_datetimes[datetime_index]
    filtered_data = combined_data[(combined_data['DateTime'] == selected_datetime) & 
                                  (combined_data['Source Category'] == source_category) &
                                  (combined_data['Destination Category'] == destination_category)]

    routes = []
    for _, row in filtered_data.iterrows():
        origin = [row['y0_shifted'], row['x0_shifted']]
        destination = [row['y1_shifted'], row['x1_shifted']]
        tooltip_origin = f"Baseline: {row['Daily Baseline: People Moving']}"
        tooltip_destination = f"Crisis: {row['Crisis: People Moving']}"

        # Create markers with custom icons
        origin_marker = dl.Marker(position=origin, icon=dict(iconUrl='https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png', iconSize=[8, 14]), children=dl.Tooltip(tooltip_origin))
        destination_marker = dl.Marker(position=destination, icon=dict(iconUrl='https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png', iconSize=[8, 14]), children=dl.Tooltip(tooltip_destination))

        # Create a polyline for the route
        route_line = dl.Polyline(positions=[origin, destination], color='blue', weight=1)

        routes.extend([origin_marker, destination_marker, route_line])

    return routes

# Control the visibility of the "Learn More" button
@app.callback(
    Output("collapse", "is_open"),
    [Input("collapse-button", "n_clicks")], #listens for clicks on a button (collapse-button) 
    [State("collapse", "is_open")],
)
def toggle_collapse(n, is_open): 
    if n:
        return not is_open
    return is_open

if __name__ == '__main__':
    app.run_server(debug=True)
