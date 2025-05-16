import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"

def generar_token():
    if os.path.exists(TOKEN_PATH):
        return {"message": "Token ya existe"}
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())
    return {"message": "Token generado exitosamente"}