import gspread
from google.oauth2.service_account import Credentials

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'expenses-administration-fb7c867085c4.json'

# Define the scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Authenticate with the service account
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

# Open your Google Sheets
llc_sheet = client.open("LLC (Code & Palette) Sheet").sheet1
personal_sheet = client.open("Personal (Bryan) Sheet").sheet1

# Example function to add data to a sheet
def add_data_to_sheet(sheet, data):
    sheet.append_row(data)

# Example data to be added
data = ["2024-05-19", "Example Description", "Example Category", 100.0, 50.0, "Credit Card", "Example Notes"]

# Add data to the LLC sheet
add_data_to_sheet(llc_sheet, data)
