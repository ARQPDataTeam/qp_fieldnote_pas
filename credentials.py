from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
from dotenv import load_dotenv 

def sql_engine_string_generator(datahub_host, datahub_db, datahub_user, datahub_pwd,local): 

    # set a try except clause to grab the online credentials keys and if not, grab them locally as environment variables
    try:
        if local:
            raise Exception("Working locally, attempting to load credentials from file")
        
        # set the key vault path
        KEY_VAULT_URL = "https://fsdh-proj-aqpd-prd-kv.vault.azure.net/"
        error_occur = False

        # Retrieve the secrets containing DB connection details
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URL, 
                                     credential=credential)

        # Retrieve the secrets containing DB connection details
        DB_HOST = secret_client.get_secret(datahub_host).value
        DB_NAME = datahub_db
        DB_USER = secret_client.get_secret(datahub_user).value
        DB_PASS = secret_client.get_secret(datahub_pwd).value
        print ('Credentials loaded from FSDH')

    except Exception as e:
        # declare FSDH keys exception
        error_occur = True
        print(e)
        
        # load the .env file using the dotenv module remove this when running a powershell script to confirue system environment vars
        parent_dir=os.getcwd()
        load_dotenv(parent_dir+ '\\.env') # default is relative local directory 
        DB_HOST = os.getenv(datahub_host)
        DB_NAME = datahub_db
        DB_USER = os.getenv(datahub_user)
        DB_PASS = os.getenv(datahub_pwd)
        print('Credentials loaded')

    # set the sql engine string
    sql_engine_string=('postgresql://{}:{}@{}/{}?sslmode=require').format(DB_USER,DB_PASS,DB_HOST,DB_NAME)
    return sql_engine_string

