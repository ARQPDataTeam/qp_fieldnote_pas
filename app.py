from dash import Dash, html, dcc 
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from sqlalchemy import create_engine,text
from credentials import sql_engine_string_generator
from flask import request
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
from dotenv import load_dotenv 
import logging

# Version number to display
version = "1.3"

# Setup logger
if not os.path.exists('logs'):
    os.mkdir('logs')
    
logging.basicConfig(
    format = '%(message)s',
    filename='logs/log.log', 
    filemode='w+',
    level = 20)

logging.getLogger("azure").setLevel(logging.ERROR)

#initialize the dash app as 'app'
app = Dash(__name__,
            external_stylesheets=[dbc.themes.SLATE],
            requests_pathname_prefix="/app/AQPD/",
            routes_pathname_prefix="/app/AQPD/")
# app = Dash(__name__,
#             external_stylesheets=[dbc.themes.SLATE])

# Global variable to store headers
request_headers = {}

# # Get connection string
# sql_engine_string=sql_engine_string_generator('DATAHUB_PSQL_SERVER','DATAHUB_SWAPIT_DBNAME','DATAHUB_PSQL_EDITUSER','DATAHUB_PSQL_EDITPASSWORD')
# swapit_sql_engine=create_engine(sql_engine_string)

sql_engine_string=sql_engine_string_generator('DATAHUB_PSQL_SERVER','dcp','DATAHUB_PSQL_EDITUSER','DATAHUB_PSQL_EDITPASSWORD')
dcp_sql_engine=create_engine(sql_engine_string)


# Setup the app layout
## MOBILE
def serve_layout():
    
    global users
    global sites
    global instruments
    global projects
    global flag_table
    # pull required data from tables
    databases = pd.read_sql_table("databases",dcp_sql_engine)
    users = pd.read_sql_table("users", dcp_sql_engine)
    sites = pd.read_sql_query(
        "select * from stations", 
        dcp_sql_engine)
    instruments = pd.read_sql_query(
        "select * from instrument_history where active = 'True'", 
        dcp_sql_engine)
    projects = np.sort(instruments['projectid'].dropna().unique())
    flag_table = pd.read_sql_query(
        "select * from flags", 
        dcp_sql_engine)
    
    dcp_sql_engine.dispose()
    
    
    return(
        html.Div(
            children=[
                
                #title + instructions
                html.H1('QP Field Log'),
                html.Div([
                    html.Span('Required fields indicated by '),
                    html.Span('*',style={"color": "red","font-weight": "bold"})
                ]),
                html.Span('v. '+version),
                html.Br(),
                
                # User
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2([
                            "User",
                            html.Span('*',style={"color": "red","font-weight": "bold"})
                        ])),
                        html.Br(),
                        dcc.Input(
                            style={'textAlign': 'center'},
                            id = "user",
                            placeholder="...",
                        ),
                        html.Br()],
                        width = 8
                    )],
                    id = "user_row",
                    justify = "center"
                ),
                
                # Project
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2([
                            "Project",
                            html.Span('*',style={"color": "red","font-weight": "bold"})
                        ])),
                        dcc.Dropdown(
                            projects.tolist(),
                            id = "project",
                            placeholder="..."
                        ),
                        html.Br()],
                        width = 8
                    )],
                    id = "project_row",
                    justify = "center"
                ),
                
                # Site
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2([
                            "Site",
                            html.Span('*',style={"color": "red","font-weight": "bold"})
                        ])),
                        dcc.Dropdown(
                            id = "site",
                            placeholder="...",
                            optionHeight=50
                        ),
                        html.Br()],
                        width = 8
                    )],
                    id = "site_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                
                # Instrument
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2([
                            "Instrument",
                            html.Span('*',style={"color": "red","font-weight": "bold"})
                        ])),
                        dcc.Dropdown(
                            id = "instrument",
                            placeholder="...",
                            optionHeight=50
                        ),
                        html.Br()],
                        width = 8
                    )],
                    id = "instrument_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                
                # Flag Category
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2("Flag Category")),
                        dcc.Dropdown(
                            options=list(set(flag_table['category'].tolist())),
                            id = "flag_cat",
                            placeholder="...",
                            optionHeight=50
                        ),
                        html.Br()],
                        width = 8
                    )],
                    id = "flagcat_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                
                # Flag
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2("Flag")),
                        dcc.Dropdown(
                            id = "flag",
                            placeholder="...",
                            optionHeight=50
                        ),
                        html.Br()],
                        width = 8
                    )],
                    id = "flag_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                
                # Note
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2("Note")),
                        dbc.Input(
                            placeholder="...", 
                            id = "note",
                            type="text"),
                        html.Br()],
                        width = 8
                    )],
                    id = "note_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                
                # Date and time
                dbc.Row([
                    dbc.Col(
                        [dbc.Label(html.H2([
                            "Datetime",
                            html.Span('*',style={"color": "red","font-weight": "bold"})
                        ])),
                        dbc.Input(
                            value = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            placeholder="...",
                            id = "startdt",
                            type="datetime-local",
                            step="1"
                        )],
                        width = 8
                    )],
                    id = "date_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(
                            options = ["UTC","EST","EDT"],
                            value = "EST",
                            id = "timezone",
                            placeholder="Timezone",
                            optionHeight=50
                        ),
                        html.Br()],
                        width = 4
                    )],
                    id = "tz_row",
                    justify = "center",
                    style={'display':'none'}
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "Submit",
                            id = "submit_button",
                            color="info", 
                            disabled=True),
                        html.Br()],
                        width = 4
                    )],
                    id = "buttons_row",
                    justify = "center",
                    className="d-grid gap-2"
                ),
                dbc.Row([
                    dbc.Col([
                        html.Br(),
                        dcc.Loading(
                            id="loading",
                            type="default",
                            children=html.Div(id="submit_button_loading")
                        )],
                        width = 8
                    )],
                    id = "loading_row",
                    justify = "center"
                ),
                dbc.Tooltip(
                    "Required input missing",
                    id="submit_tooltip",
                    target="buttons_row",
                    placement="bottom"
                ),
                html.Div(id='logs'),
                dcc.Interval(id='log_updater',interval = 2000)
            
            ],
            style={'textAlign': 'center'}
        )
    )

#%% Select project callback
@app.callback(
    Output('site_row', 'style'),
    Output('site','options'),
    Input('project','value'))
def project_update(project):
    
    # sites for selected project
    sites_filtered = np.sort(sites.loc[sites["projectid"]==project]['short_description']).tolist()
    
    # show row and update
    if project == "" or project is None:
        return [{'display':'none'},sites_filtered]
    else:
        return [{'display':'flex'},sites_filtered]


#%% Site selection callback
@app.callback(
    Output('instrument_row', 'style'),
    Output('flagcat_row', 'style'),
    Output('flag_row', 'style'),
    Output('note_row', 'style'),
    Output('date_row', 'style'),
    Output('tz_row', 'style'),
    Output('instrument','options'),
    Input('site','value'),
    State('project','value'))
def site_update(site,project):
    
    # show all remaining rows
    if site == "" or site is None:
        d = {'display':'none'}
        return_list = [d]*6
        return_list.append([''])
    else:
        d ={'display':'flex'}
        return_list = [d]*6
        
        # instruments for selected site
        siteid = sites[(sites['short_description']==site) &
                               (sites['projectid']==project)]['siteid'].tolist()[0]
        
        instruments_filtered = np.sort(instruments.loc[
                (instruments["projectid"]==project) &
                (instruments["currentlocation"] == siteid)]['instrumentnamelabel']).tolist()
        
        return_list.append(instruments_filtered)
        
    return return_list
        

#%% Flag category selection callback 
@app.callback(
    Output('flag','options'),
    Input('flag_cat','value'))
def flag_update(flag_cat):
    
    # flags for selected category
    if flag_cat == "" or flag_cat is None:
        flags = [""]
    else:
        flags = np.sort(flag_table.loc[flag_table["category"]==flag_cat]['description']).tolist()
    return flags



#%% Show submit button when all required inputs are put in
@app.callback(
    Output('submit_button','disabled'),
    Output('submit_tooltip','children'),
    Input('user','value'),
    Input('project','value'),
    Input('site','value'),
    Input('instrument','value'),
    Input('startdt','value'),
    Input('timezone','value'),
    Input('flag_cat','value'),
    Input('flag','value'),
    Input('note','value'))
    
def button_update(user,project,site,instrument,startdt,timezone,flag_cat,flag,note):
    
    if any([user is None, 
            project is None,
            site is None,
            instrument is None,
            startdt is None,
            timezone is None]):
        return [True,"Required input missing"]
    else:
        return [False,"Ready to submit"]


#%% Submit to database
@app.callback(
    Output('submit_button_loading','children'),
    Output('submit_button_loading','style'),
    Output('submit_button','disabled',allow_duplicate=True),
    Output('submit_tooltip','children',allow_duplicate=True),
    Input('submit_button', 'n_clicks'),
    State('site','value'),
    State('instrument','value'),
    State('project','value'),
    State('startdt','value'),
    State('timezone','value'),
    State('user','value'),
    State('note','value'),
    State('flag','value'),
    prevent_initial_call=True
)

def upload_log(n,site,instrument,project,startdt,timezone,useremail,note,flag):
    
    
    
    
    sql_engine_string=sql_engine_string_generator('DATAHUB_PSQL_SERVER','borden','DATAHUB_PSQL_EDITUSER','DATAHUB_PSQL_EDITPASSWORD')
    sql_engine=create_engine(sql_engine_string)
    
    # create db connection
    with sql_engine.connect() as conn:
    
        # parse all variables going to db
        siteid = sites[(sites['short_description']==site) &
                       (sites['projectid']==project)]['siteid'].tolist()[0]
        submitdt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        startdt = startdt.replace("T", " ")
        if isinstance(note,list):
            note = ','.join(note)
            
        try:
            user = users['fullname'].loc[users['piemail'].str.lower()==useremail.lower()].values[0]
        except:
            user = useremail
                    
        try:
            # queries
            tz_set_query = text("""SET TIME ZONE 'EST5EDT';""")
           
            InsertLog = text('''
            INSERT INTO logs (station,datetime,loguser,logtype,startdt,enddt,field_comment,site_location,instrument,field_flag)
            VALUES ('{0}', '{1}', '{2}','{3}',NULLIF('{4}','')::timestamp,NULLIF('{5}','')::timestamp,'{6}',NULLIF('{7}',''),NULLIF('{8}',''),NULLIF('{9}',''))
            ON CONFLICT DO NOTHING;
            '''.format(siteid,submitdt,
            user,'FIELD', 
            startdt,'', 
            note.replace("'","''"),'', 
            instrument,flag))
            
            conn.execute(tz_set_query)
            conn.execute(InsertLog)
            conn.commit()
            
            return ["Upload to database successful!",
                    {"color": "green","font-weight": "bold","font-size": "large"},
                    True,
                    "Submission complete!"]
        except Exception as e:
            
            logging.exception(e)
            
            return ["Upload to database not successful!",
                    {"color": "red","font-weight": "bold","font-size": "large"},
                    False,
                    "Ready to submit"]
        
    
#%% Callback to update user field based on page headers
@app.callback(
    Output('user', 'value'),
    Output('user', 'disabled'),
    Output('user_row','style'),
    Input('user', 'id')  # This triggers the callback on page load
)
def display_headers(_):
    if request_headers.get('Dh-User'):
        return [request_headers.get('Dh-User'),True,{'display':'none'}]
    else:
        return [None,False,{'display':'flex'}]



#%% Server route to automatically capture headers when the page is first loaded
@app.server.before_request
def before_request():
    global request_headers
    request_headers = dict(request.headers)  # Capture headers before processing any request

#%% Log print statements
@app.callback(
    Output('logs', 'children'),
    Input('log_updater', 'n_intervals')  # This triggers the callback on page load
)
def update_log(n):
    with open("logs/log.log","r") as log:
        return log.read()

app.layout = serve_layout

server = app.server 
# if __name__=='__main__':
#     app.run_server(debug=True,port=8080)
