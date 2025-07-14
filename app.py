# %% Import + setup
import dash
from dash import html, Input, Output, State, ctx, dcc, Dash,dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, MetaData
from credentials import sql_engine_string_generator
from flask import request
from datetime import datetime
import os
import logging
from dash_breakpoints import WindowBreakpoints
import socket
import dash.exceptions
import dash_ag_grid as dag
import re

# Local dev boolean
computer = socket.gethostname()
if computer == 'WONTN774787':
    local = True
else:
    local = False

# Version number to display
version = "2.0"

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
               external_stylesheets=[dbc.themes.SLATE], # REMOVED PLACEHOLDER_CSS from here
               requests_pathname_prefix="/app/AQPD/",
               routes_pathname_prefix="/app/AQPD/",
               suppress_callback_exceptions=True)
else:
    app = Dash(__name__,
               external_stylesheets=[dbc.themes.SLATE], # REMOVED PLACEHOLDER_CSS from here
               suppress_callback_exceptions=True)

# Global variable to store headers
request_headers = {}

# Get connection string
dcp_sql_engine_string = sql_engine_string_generator('DATAHUB_PSQL_SERVER', 'dcp', 'DATAHUB_PSQL_USER', 'DATAHUB_PSQL_PASSWORD', local)
dcp_sql_engine = create_engine(dcp_sql_engine_string)

mercury_sql_engine_string = sql_engine_string_generator('DATAHUB_PSQL_SERVER', 'mercury_passive', 'DATAHUB_PSQL_USER', 'DATAHUB_PSQL_PASSWORD', local)
mercury_sql_engine = create_engine(mercury_sql_engine_string)


# Global storage for the new dataframe
database_df = pd.DataFrame(columns=[
    'sample_start', 'sample_end', 'sampleid', 'kitid', 'samplerid',
    'siteid', 'shipped_location', 'shipped_date', 'return_date',
    'sample_type', 'note'
])

# Define the placeholder for date/time columns
DATE_TIME_PLACEHOLDER = "YYYY-MM-DD HH:MM:SS"

# Table div
global tablehtml
tablehtml = html.Div(
    dag.AgGrid(
        id="database-table",
        columnDefs=[
            {"field": "sample_start", "headerName": "Sample Start", "editable": True,
             "valueFormatter": {"function": f"params.value === '' || params.value === null ? '{DATE_TIME_PLACEHOLDER}' : params.value"},
             "cellClassRules": {
                 "ag-placeholder-text": "params.value === '' || params.value === null"
             }},
            {"field": "sample_end", "headerName": "Sample End", "editable": True,
             "valueFormatter": {"function": f"params.value === '' || params.value === null ? '{DATE_TIME_PLACEHOLDER}' : params.value"},
             "cellClassRules": {
                 "ag-placeholder-text": "params.value === '' || params.value === null"
             }},
            {"field": "sampleid", "headerName": "Sample ID", "editable": False},
            {"field": "kitid", "headerName": "Kit ID", "editable": True},
            {"field": "samplerid", "headerName": "Sampler ID", "editable": True},
            {"field": "siteid", "headerName": "Site ID", "editable": True},
            {"field": "shipped_location", "headerName": "Shipped Location", "editable": True},
            {"field": "shipped_date", "headerName": "Shipped Date", "editable": True, "cellEditor": "agDateStringCellEditor"},
            {"field": "return_date", "headerName": "Return Date", "editable": True, "cellEditor": "agDateStringCellEditor"},
            {"field": "sample_type", "headerName": "Sample Type", "editable": True, "cellEditor": "agSelectCellEditor", "cellEditorParams": {"values": ["Sample", "Blank"]}},
            {"field": "note", "headerName": "Note", "editable": True}
        ],
        defaultColDef={"resizable": True, "sortable": True},
        columnSize="sizeToFit",
        dashGridOptions={"rowSelection":"single",
                         "animateRows": True,
                         "editable": True,
                         "components": {}
        },
        className="ag-theme-alpine-dark",
        style={"height": "400px", "width": "100%"}
    ),
    style={"padding": "0 40px"}
)





# %% Layout function, useful for having two UI options (e.g., mobile vs desktop)
def serve_layout():
    global databases
    global users
    global sites

    # Pull required data from tables
    users = pd.read_sql_table("users", dcp_sql_engine)
    sites = pd.read_sql_query("select * from stations", dcp_sql_engine)

    dcp_sql_engine.dispose()
    mercury_sql_engine.dispose()

    return html.Div([
        html.Div(id="display", style={'textAlign': 'center'}),
        WindowBreakpoints(
            id="breakpoints",
            widthBreakpointThresholdsPx=[768],
            widthBreakpointNames=["sm", "lg"]
        )
    ])

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
            html.Span('v. ' + version),
            html.Br(),
            html.Br(),
            html.Div([
                html.H3('Choose Sample Type:'),
                #html.Span('*', style={"color": "red", "font-weight": "bold"})
            ])
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
        #html.Br(),
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
        html.Hr(),
        tablehtml,
        html.Div(id="edit-confirmation", style={"textAlign": "center", "color": "green", "marginTop": "10px"}),
        dbc.Modal(
            id="new-entry-modal",
            is_open=False,
            size="lg",
            children=[
                dbc.ModalHeader("Enter New Kit Information"),
                dbc.ModalBody([
                    # Sampler IDs header
                    html.H5("Sampler IDs", className="mb-3 text-center"),
                    html.Div(id="entry-container", children=[]),
                    # Kit ID section
                    dbc.Row(
                        dbc.Col([
                            html.H5("Kit ID", className="mb-2 text-center"),
                            dbc.Input(
                                id="static-kit-id-input",
                                type="text",
                                placeholder="EC-XXXX", # Placeholder added
                                className="text-center",
                                style={'width': '150px', 'margin': '0 auto'}
                            )
                        ],
                        className="d-flex flex-column align-items-center"),
                        justify="center",
                        className="mb-4 mt-4"
                    ),
                    # Loading animation below Kit ID
                    html.Div([
                        dbc.Spinner(color="primary", type="grow"),
                        html.Span(" Waiting for user input...", className="text-muted ms-2")
                    ], className="text-center my-3"),
                ]),
                dbc.ModalFooter(
                    [
                        dbc.Button("Done", id="new-done-button", color="success"),
                        html.Div(id="new-kitid-feedback", className="mt-3 text-center")
                    ],
                    className="w-100 d-flex flex-column align-items-center"
                )
            ]
        ),
        dbc.Modal(
            id="update-kitid-modal",
            is_open=False,
            size="md",
            children=[
                dbc.ModalHeader("Update Kit Entry"),
                dbc.ModalBody([
                    html.H5("Enter Kit ID", className="mb-2 text-center"),
                    dbc.Input(
                        id="update-kitid-input",
                        type="text",
                        placeholder="EC-XXXX",
                        className="text-center",
                        style={'width': '150px', 'margin': '0 auto'}
                    ),
                    html.Div(id="update-kitid-feedback", className="mt-3 text-center")
                ]),
                dbc.ModalFooter(
                    dbc.Button("Done", id="update-done-button", color="success"),
                    className="w-100 d-flex justify-content-center"
                )
            ]
        ),
        dcc.Store(id="entry-store", data=[]),
        dcc.Store(id="editing", data=False),
        dcc.Store(id="entry-counter", data=1),
        dcc.Store(id='database-store', data=[]),
        dcc.Store(id="kitid-filtered-data", data=None),
        dcc.Interval(id='log_updater', interval=5000),
        html.Div(
            dbc.Button(
                "Upload Data to Database",
                id="btn-upload-data",
                color="success",
                className="mt-4",
                style={'display': 'none'} 
            ),
            className="d-flex justify-content-center" 
        )
    ]

# %% Function to create textbox rows
def create_text_row(index: int, value="", editable=True, selection=None):
    return html.Div(
        id={'type': 'entry-row', 'index': index},
        children=[
            dbc.Input(
                id={'type': 'entry-input', 'index': index},
                type="text",
                value=value,
                placeholder="ECCCXXXX",
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
                value=selection,
                labelStyle={'display': 'inline-block', 'marginRight': '10px'},
                inputStyle={"marginRight": "5px"},
                style={'marginBottom': '10px', 'color': 'white'}
            ),
            dbc.Button("×", id={'type': 'delete-row', 'index': index}, color="danger", size="sm", className="ms-2")
        ],
        className="d-flex align-items-center",
        style={'gap': '20px', 'marginBottom': '10px'}
    )

# %% Modal for "new" button click
@app.callback(
    Output("new-entry-modal", "is_open"),
    Output("entry-container", "children", allow_duplicate=True),
    Output("entry-store", "data", allow_duplicate=True),
    Output("editing", "data", allow_duplicate=True),
    Output("entry-counter", "data"),
    Input("btn-new", "n_clicks"),
    Input("new-done-button", "n_clicks"),
    State("new-entry-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_modal(new_clicks, done_clicks, is_open):
    triggered_id = ctx.triggered_id
    if triggered_id == "btn-new":
        return True, [create_text_row(1)], [{"index": 1, "value": "", "editable": True, "radio": None}], False, 2
    elif triggered_id == "new-done-button":
        return False, [], [], False, 1
    return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update


# %% Create text boxes dynamically in "New" modal
@app.callback(
    Output("entry-container", "children", allow_duplicate=True),
    Output("entry-store", "data", allow_duplicate=True),
    Output("entry-counter", "data", allow_duplicate=True),
    Input({'type': 'entry-input', 'index': dash.ALL}, 'value'),
    Input({'type': 'entry-radio', 'index': dash.ALL}, 'value'),
    State({'type': 'entry-input', 'index': dash.ALL}, 'id'),
    State("entry-counter", "data"),
    prevent_initial_call=True
)
def update_entry_store_and_ui(values, radios, ids, counter):
    if not values or not ids:
        raise dash.exceptions.PreventUpdate

    new_data = []
    new_components = []
    seen_indices = set()

    for i, id_obj in enumerate(ids):
        idx = id_obj['index']
        seen_indices.add(idx)
        value = values[i] if i < len(values) else ""
        radio = radios[i] if i < len(radios) else None

        new_data.append({
            "index": idx,
            "value": value,
            "editable": True,
            "radio": radio
        })

        new_components.append(create_text_row(idx, value=value, editable=True, selection=radio))

    if isinstance(values[-1], str) and len(values[-1]) == 8 and counter not in seen_indices:
        new_data.append({
            "index": counter,
            "value": "",
            "editable": True,
            "radio": None
        })
        new_components.append(create_text_row(counter, value="", editable=True))
        counter += 1

    return new_components, new_data, counter


# %% Delete row callback
@app.callback(
    Output("entry-container", "children", allow_duplicate=True),
    Output("entry-store", "data", allow_duplicate=True),
    Input({'type': 'delete-row', 'index': dash.ALL}, 'n_clicks'),
    State("entry-store", "data"),
    prevent_initial_call=True
)
def delete_row(delete_clicks, entry_data):
    if not any(delete_clicks):
        raise dash.exceptions.PreventUpdate

    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate

    delete_index = triggered['index']
    new_data = [row for row in entry_data if row['index'] != delete_index]
    new_components = [
        create_text_row(row['index'], row['value'], editable=True, selection=row['radio'])
        for row in new_data
    ]
    return new_components, new_data


# %% "Done" button callback for new entries
@app.callback(
    Output("database-table", "rowData", allow_duplicate=True),
    Output("btn-upload-data", "style", allow_duplicate=True),
    Output("new-kitid-feedback", "children"),
    Output("new-kitid-feedback", "style"),
    Output("new-entry-modal", "is_open", allow_duplicate=True),
    Output("entry-container", "children", allow_duplicate=True),
    Output("entry-store", "data", allow_duplicate=True),
    Input("new-done-button", "n_clicks"),
    State("static-kit-id-input", "value"),
    State("entry-store", "data"),
    State("entry-container", "children"),
    prevent_initial_call=True
)
def validate_and_build_df(n_clicks, kit_id_value, entry_data, current_components):
    global database_df

    # Validate Kit ID
    if not kit_id_value or not re.fullmatch(r"EC-\d{4}", kit_id_value.strip()):
        return dash.no_update, dash.no_update, "Invalid Kit ID format. Expected EC-####.", {"color": "red"}, True, current_components, entry_data

    # Validate Sample IDs
    invalid_samples = [
        entry["value"] for entry in entry_data
        if entry.get("value") and not re.fullmatch(r"ECCC\d{4}", entry["value"].strip())
    ]
    if invalid_samples:
        return dash.no_update, dash.no_update, f"Invalid Sample ID(s): {', '.join(invalid_samples)}. Expected ECCC####.", {"color": "red"}, True, current_components, entry_data

    # Proceed with building the DataFrame
    valid_entries = [entry for entry in entry_data if entry.get("value", "").strip() != ""]
    records = []
    for entry in valid_entries:
        sampler_id = entry.get("value", "")
        generated_sampleid = f"{kit_id_value}_{sampler_id}" if kit_id_value and sampler_id else None
        records.append({
            'sample_start': None,
            'sample_end': None,
            'sampleid': generated_sampleid,
            'kitid': kit_id_value,
            'samplerid': sampler_id,
            'siteid': None,
            'shipped_location': None,
            'shipped_date': None,
            'return_date': None,
            'sample_type': entry.get("radio", ""),
            'note': None
        })

    database_df = pd.DataFrame(records)
    return database_df.to_dict("records"), {'display': 'block', 'margin-top': '20px'}, "", {"color": "green"}, False, current_components, entry_data


# %% Update df whenever user edits the datatable
@app.callback(
    Output("edit-confirmation", "children"),
    Output("database-table", "rowData"),
    Input("database-table", "cellValueChanged"),
    State("database-table", "rowData"),
    prevent_initial_call=True
)
def sync_table_edits(cellValueChanged, current_grid_data):
    global database_df
    if not cellValueChanged:
        raise dash.exceptions.PreventUpdate

    changed_col = cellValueChanged[0]['colId']
    changed_row_index = cellValueChanged[0]['rowIndex']+1
    new_value_raw = cellValueChanged[0]['value']
    old_value = cellValueChanged[0]['oldValue']

    updated_grid_data = list(current_grid_data)

    feedback_message = ""
    feedback_style = {"color": "green"}

    # Update the value in the grid data first
    if changed_col in ['sample_start', 'sample_end']:
        if new_value_raw:
            try:
                datetime.strptime(str(new_value_raw), "%Y-%m-%d %H:%M:%S")
                updated_grid_data[changed_row_index][changed_col] = new_value_raw
                feedback_message = f"Column '{changed_col}' at Row {changed_row_index}, changed from '{old_value}' to '{new_value_raw}'."
                feedback_style = {"color": "green"}
            except ValueError:
                updated_grid_data[changed_row_index][changed_col] = old_value if old_value is not None else ""
                feedback_message = f"Error: Invalid date/time format for '{changed_col}' at Row {changed_row_index}. Expected '{DATE_TIME_PLACEHOLDER}'. Value reverted to '{old_value if old_value is not None else ''}'."
                feedback_style = {"color": "red"}
        else:
            updated_grid_data[changed_row_index][changed_col] = "" # Keep as empty string if user clears it in UI
            feedback_message = f"Column '{changed_col}' at Row {changed_row_index}, value cleared."
            feedback_style = {"color": "green"}
    else:
        updated_grid_data[changed_row_index][changed_col] = new_value_raw
        feedback_message = f"Column '{changed_col}' at Row {changed_row_index}, changed from '{old_value}' to '{new_value_raw}'."
        feedback_style = {"color": "green"}

    # After updating the changed cell, check if sampleid needs to be updated
    if changed_col in ['kitid', 'samplerid']:
        row = updated_grid_data[changed_row_index]
        current_kitid = row.get('kitid') if row.get('kitid') is not None else ""
        current_samplerid = row.get('samplerid') if row.get('samplerid') is not None else ""
        
        # Construct the new sampleid
        new_sampleid = f"{current_kitid}_{current_samplerid}"
        
        # Only update if the sampleid actually changes to avoid unnecessary re-renders
        if row.get('sampleid') != new_sampleid:
            updated_grid_data[changed_row_index]['sampleid'] = new_sampleid
            # Also update feedback message to indicate sampleid was updated
            feedback_message += f" Sample ID updated to '{new_sampleid}'."


    database_df = pd.DataFrame(updated_grid_data)
    database_df.to_csv("debug_database_df.csv",index =False)

    return html.Div(feedback_message, style=feedback_style), updated_grid_data


# %% Grab user email from headers
@app.callback(
    Output('user', 'value'),
    Output('user', 'disabled'),
    Output('user_div', 'style'),
    Input('user', 'id')
)
def display_headers(_):
    if request_headers.get('Dh-User'):
        return [request.headers.get('Dh-User'), True, {'display': 'none'}]
    else:
        return [None, False, {'display': 'none'}]

@app.server.before_request
def before_request():
    global request_headers
    request_headers = dict(request.headers)  # Capture headers before processing any request


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
    Output("entry-container", "children", allow_duplicate=True),
    Input("entry-container", "children"),
    prevent_initial_call=True
)

# %% Callback for the Upload Data button with duplicates checking
@app.callback(
    Output("edit-confirmation", "children", allow_duplicate=True), # Using edit-confirmation for feedback
    Input("btn-upload-data", "n_clicks"),
    prevent_initial_call=True
)
def upload_data_to_database(n_clicks):
    global database_df 

    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    # Filter out empty rows from database_df before attempting to upload
    df_to_upload = database_df[database_df['samplerid'].astype(str).str.strip() != ''].copy()

    if df_to_upload.empty:
        return html.Div("No valid data to upload. All entries are empty or have empty Sampler IDs.", style={"color": "orange"})

    # Clean up date/time columns to ensure they are None (for NULL) if they are empty strings
    for col in ['sample_start', 'sample_end', 'shipped_date', 'return_date']:
        df_to_upload[col] = df_to_upload[col].replace('', np.nan) # np.nan will be translated to NULL by sqlalchemy

    feedback_messages = []
    try:
        # Get existing sampleids from the database (reverted to original logic)
        existing_sampleids_df = pd.read_sql_query("SELECT sampleid FROM pas_tracking", mercury_sql_engine)
        existing_sampleids = set(existing_sampleids_df['sampleid'].dropna().astype(str).tolist())
        
        # Identify duplicates in the current dataframe to upload
        df_to_upload_sampleids = df_to_upload['sampleid'].astype(str)
        internal_duplicates = df_to_upload_sampleids[df_to_upload_sampleids.duplicated(keep='first')]

        # Find entries that already exist in the database
        db_duplicates_mask = df_to_upload_sampleids.isin(existing_sampleids)
        db_duplicates = df_to_upload[db_duplicates_mask]
        
        # Combine all duplicates (ensuring unique sampleid messages)
        all_duplicate_sampleids = set(internal_duplicates.tolist() + db_duplicates['sampleid'].astype(str).tolist())

        if all_duplicate_sampleids:
            # Filter out duplicates from the DataFrame to be uploaded
            df_unique_to_upload = df_to_upload[~df_to_upload_sampleids.isin(all_duplicate_sampleids)].copy()
            
            # Prepare message for duplicates
            duplicate_message = f"Duplicate entries detected and skipped for Sample IDs: {', '.join(sorted(list(all_duplicate_sampleids)))}. "
            feedback_messages.append(html.Span(duplicate_message, style={"color": "orange"}))
        else:
            df_unique_to_upload = df_to_upload.copy()

        if df_unique_to_upload.empty:
            if not all_duplicate_sampleids: # Only show this if no duplicates were found at all
                feedback_messages.append(html.Div("No new unique data to upload.", style={"color": "orange", "marginTop": "10px"}))
            return html.Div(feedback_messages)

        # Proceed with upload for unique entries
        df_unique_to_upload.to_sql('pas_tracking', mercury_sql_engine, if_exists='append', index=False)
        
        success_message = f"Successfully uploaded {len(df_unique_to_upload)} new entries to 'pas_tracking' table!"
        feedback_messages.append(html.Div(success_message, style={"color": "green", "marginTop": "10px"}))

    except Exception as e:
        error_message = f"Error uploading data: {e}. Please check logs for details."
        feedback_messages.append(html.Div(error_message, style={"color": "red", "marginTop": "10px"}))
        logging.error(f"Database upload error: {e}")

    return html.Div(feedback_messages)


# %% Update button callback
@app.callback(
    Output("update-kitid-modal", "is_open",allow_duplicate=True),
    Output("database-store", "data"),
    Input("btn-update", "n_clicks"),
    Input("update-done-button", "n_clicks"),
    State("update-kitid-modal", "is_open"),
    State("database-store", "data"),
    prevent_initial_call=True
)
def toggle_update_modal(open_clicks, done_clicks, is_open,db_tracking_data):

    triggered = ctx.triggered_id
    if triggered == "btn-update":
        # Query the pas_tracking table and store in global variable
        try:
            db_tracking_data = pd.read_sql_query("SELECT * FROM pas_tracking", mercury_sql_engine)
        except Exception as e:
            logging.error(f"Error loading pas_tracking table: {e}")
            db_tracking_data = pd.DataFrame().to_dict("records")

        return True,db_tracking_data.to_dict("records")  # open modal
    elif triggered == "update-done-button":
        return False,db_tracking_data
        # close modal

    return is_open

# %% Update Done button callback
@app.callback(
    Output("update-kitid-feedback", "children"),
    Output("update-kitid-feedback", "style"),
    Output("update-kitid-modal", "is_open", allow_duplicate=True),
    Output("database-table", "rowData", allow_duplicate=True),
    Output("kitid-filtered-data", "data"),
    Output("btn-upload-data", "style", allow_duplicate=True),
    Input("update-done-button", "n_clicks"),
    State("update-kitid-input", "value"),
    State("database-store", "data"),
    prevent_initial_call=True
)
def validate_and_display_kitid(n_clicks, kit_id,db_tracking_data):
    
    
    if not kit_id:
        return "Invalid Kit ID", {"color": "red"}, True, dash.no_update, dash.no_update, dash.no_update

    if not re.fullmatch(r"EC-\d{4}", kit_id.strip()):
        return "Invalid Kit ID", {"color": "red"}, True, dash.no_update, dash.no_update, dash.no_update

    # Filter the loaded tracking data for the entered Kit ID
    db_tracking_data = pd.DataFrame(db_tracking_data)
    filtered_df = db_tracking_data[db_tracking_data['kitid'] == kit_id].copy()

    if filtered_df.empty:
        return "No entries found for this Kit ID.", {"color": "orange"}, True, dash.no_update, dash.no_update, dash.no_update
    
    # Update global dataframe
    global database_df
    database_df = filtered_df

    return "", {}, False, database_df.to_dict("records"), filtered_df.to_dict("records"),{"display": "block", "margin-top": "20px"}


# %% Run app
app.layout = serve_layout

if not local:
    server = app.server
else:
    if __name__ == '__main__':
        app.run(debug=True, port=8080)
