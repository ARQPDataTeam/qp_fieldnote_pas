# %% Import + setup
import dash
from dash import html, Input, Output, State, ctx, dcc, Dash
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from credentials import sql_engine_string_generator
from flask import request
from datetime import datetime
import os
import logging
from dash_breakpoints import WindowBreakpoints
import socket

# Local dev boolean
computer = socket.gethostname()
if computer == 'WONTN774787':
    local = True
else:
    local = False

# Version number to display
version = "1.1"

# Setup logger
if not os.path.exists('logs'):
    os.mkdir('logs')

logging.basicConfig(
    format='%(message)s',
    filename='logs/log.log',
    filemode='w+',
    level=20
)

logging.getLogger("azure").setLevel(logging.ERROR)

# Initialize the dash app as 'app'
if not local:
    app = Dash(__name__,
               external_stylesheets=[dbc.themes.SLATE],
               requests_pathname_prefix="/app/AQPD/",
               routes_pathname_prefix="/app/AQPD/",
               suppress_callback_exceptions=True)
else:
    app = Dash(__name__,
               external_stylesheets=[dbc.themes.SLATE],
               suppress_callback_exceptions=True)

# Global variable to store headers
request_headers = {}

# Get connection string
sql_engine_string = sql_engine_string_generator('DATAHUB_PSQL_SERVER', 'dcp', 'DATAHUB_PSQL_EDITUSER', 'DATAHUB_PSQL_EDITPASSWORD', local)
dcp_sql_engine = create_engine(sql_engine_string)


# %% Layout function, useful for having two UI options (e.g., mobile vs desktop)
def serve_layout():
    global databases
    global users
    global sites
    global instruments
    global projects
    global flag_table

    # Pull required data from tables
    databases = pd.read_sql_table("databases", dcp_sql_engine)
    users = pd.read_sql_table("users", dcp_sql_engine)
    sites = pd.read_sql_query("select * from stations", dcp_sql_engine)
    instruments = pd.read_sql_query("select * from instrument_history where active = 'True'", dcp_sql_engine)
    projects = databases['label'].loc[databases['active'] == True].values
    flag_table = pd.read_sql_query("select * from flags", dcp_sql_engine)

    dcp_sql_engine.dispose()

    return html.Div([
        html.Div(id="display", style={'textAlign': 'center'}),
        WindowBreakpoints(
            id="breakpoints",
            widthBreakpointThresholdsPx=[768],
            widthBreakpointNames=["sm", "lg"]
        )
    ])


# %% Function to create textbox rows
def create_text_row(index: int, value="", editable=True, selection=None):
    return html.Div(
        id=f"entry_row_{index}",
        children=[
            dbc.Input(
                id={'type': 'entry-input', 'index': index},
                type="text",
                value=value,
                disabled=not editable,
                debounce=False,
                className="mb-2 me-2"
            ),
            dcc.RadioItems(
                id={'type': 'entry-radio', 'index': index},
                options=[
                    {'label': 'Sample', 'value': 'Sample'},
                    {'label': 'Blank', 'value': 'Blank'}
                ],
                value='Sample',
                labelStyle={'display': 'inline-block', 'marginRight': '10px'},
                inputStyle={"marginRight": "5px"},
                style={'marginBottom': '10px', 'color': 'white'}
            )
        ],
        className="d-flex align-items-center",
        style={'gap': '20px'}
    )

# %% Desktop layout
@app.callback(
    Output("display", "children"),
    Input("breakpoints", "widthBreakpoint"),
    State("breakpoints", "width"),
)
def change_layout(breakpoint_name: str, window_width: int):
    return [
        dbc.Row([
            html.H1('QP FieldNote - Passive Mercury'),
            html.Div([
                html.Span('Required fields indicated by '),
                html.Span('*', style={"color": "red", "font-weight": "bold"})
            ]),
            html.Span('v. ' + version),
            html.Br(),
        ]),
        dbc.Row([
            dbc.Col(
                dbc.Row(
                    dbc.Col([
                        dbc.Label(html.H2([
                            "User",
                            html.Span('*', style={"color": "red", "font-weight": "bold"})
                        ])),
                        html.Br(),
                        dcc.Input(
                            style={'textAlign': 'center'},
                            id="user",
                            placeholder="..."
                        )
                    ]),
                    justify="center"
                ),
                id="user_div",
                width=3,
                align="center",
            )
        ], justify="center"),
        html.Br(),
        dbc.Row(
            dbc.Col(
                html.Div([
                    dbc.ButtonGroup([
                        dbc.Button("New", id="btn-new", color="primary"),
                        dbc.Button("Update", id="btn-update", color="secondary")
                    ], size="md"),
                    dbc.Tooltip("Create new sample entry", target="btn-new", placement="top"),
                    dbc.Tooltip("Update existing sample entry", target="btn-update", placement="top"),
                ]),
                width="auto",
            ),
            justify="center",
            className="buttons_div"
        ),
        dbc.Modal(
            id="new-entry-modal",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader("Enter New Entries"),
                dbc.ModalBody([
                    html.Div(id="entry-container", children=[]),
                    html.Div([
                        dbc.Spinner(color="primary", type="grow"),
                        html.Span(" Waiting for user input...", className="ms-2")
                    ], className="text-center text-muted my-3")
                ]),
                dbc.ModalFooter(
                    dbc.Button("Done", id="done-button", color="success")
                )
            ]
        ),
        dcc.Store(id="entry-store", data=[]),  # Keep track of all entries
        dcc.Store(id="editing", data=False),   # Whether we are editing or not
        dcc.Store(id="entry-counter", data=1),
        html.Div(id='logs'),
        dcc.Interval(id='log_updater', interval=5000)
    ]


# %% Modal for "new" button click
@app.callback(
    Output("new-entry-modal", "is_open"),
    Output("entry-container", "children", allow_duplicate=True),
    Output("entry-store", "data", allow_duplicate=True),
    Output("editing", "data", allow_duplicate=True),
    Output("entry-counter", "data"),
    Input("btn-new", "n_clicks"),
    Input("done-button", "n_clicks"),
    State("new-entry-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_modal(new_clicks, done_clicks, is_open):
    triggered_id = ctx.triggered_id
    if triggered_id == "btn-new":
        return True, [create_text_row(1)], [{"index": 1, "value": "", "editable": True, "radio": None}], False, 2
    elif triggered_id == "done-button":
        return False, [], [], False, 1
    return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update


# %% Create text boxes dynamically in "New" modal
@app.callback(
    Output("entry-container", "children", allow_duplicate=True),
    Output("entry-store", "data", allow_duplicate=True),
    Output("entry-counter", "data", allow_duplicate=True),
    Input({'type': 'entry-input', 'index': dash.ALL}, 'value'),
    State({'type': 'entry-input', 'index': dash.ALL}, 'id'),
    State("entry-store", "data"),
    State("entry-counter", "data"),
    prevent_initial_call=True
)
def handle_input_length(values, ids, entry_data, counter):
    new_components = []
    new_data = []

    for i, (val, id_obj) in enumerate(zip(values, ids)):
        idx = id_obj['index']
        radio_val = entry_data[i].get("radio", None)
        new_data.append({"index": idx, "value": val, "editable": True, "radio": radio_val})
        new_components.append(create_text_row(idx, value=val, editable=True, selection=radio_val))

    if len(values) > 0 and len(values[-1]) == 8 and entry_data[-1]['value'] != values[-1]:
        new_data.append({"index": counter, "value": "", "editable": True, "radio": None})
        new_components.append(create_text_row(counter, editable=True))
        counter += 1

    return new_components, new_data, counter

# %% Store radio button input values in entry-store
@app.callback(
    Output("entry-store", "data"),
    Input({'type': 'entry-radio', 'index': dash.ALL}, 'value'),
    State({'type': 'entry-radio', 'index': dash.ALL}, 'id'),
    State("entry-store", "data"),
    prevent_initial_call=True
)
def update_radio_values(values, ids, entry_data):
    for i, val in enumerate(values):
        entry_data[i]['radio'] = val
    return entry_data


# %% Grab user email from headers
@app.callback(
    Output('user', 'value'),
    Output('user', 'disabled'),
    Output('user_div', 'style'),
    Input('user', 'id')  
)
def display_headers(_):
    if request_headers.get('Dh-User'):
        return [request_headers.get('Dh-User'), True, {'display': 'none'}]
    else:
        return [None, False, {'display': 'block'}]

@app.server.before_request
def before_request():
    global request_headers
    request_headers = dict(request.headers)  # Capture headers before processing any request


# %% Update log
@app.callback(
    Output('logs', 'children'),
    Input('log_updater', 'n_intervals')
)
def update_log(n):
    with open("logs/log.log", "r") as log:
        return log.read()

# %% javascript used to autofocus newly created textboxes in "New" modal
app.clientside_callback(
    """
    function(children) {
        window.requestAnimationFrame(() => {
            setTimeout(() => {
                const container = document.getElementById('entry-container');
                if (container) {
                    const inputs = container.querySelectorAll('input[type="text"]');
                    if (inputs.length > 0) {
                        inputs[inputs.length - 1].focus();
                    }
                }
            }, 100);
        });
        return children;
    }
    """,
    Output("entry-container", "children"),
    Input("entry-container", "children")
)

# %% Run app
app.layout = serve_layout

if not local:
    server = app.server
else:
    if __name__ == '__main__':
        app.run(debug=True, port=8080)

