from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from forms import ExpenseForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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

def add_data_to_sheet(sheet, data_list):
    # Write data in batches to avoid exceeding quota
    BATCH_SIZE = 100  # Adjust the batch size as needed
    for i in range(0, len(data_list), BATCH_SIZE):
        batch = data_list[i:i+BATCH_SIZE]
        sheet.append_rows(batch)
        time.sleep(1)  # Add a delay between batches

def get_data_from_sheet(sheet):
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # Ensure Member Name column exists
    if 'Member Name' not in df.columns:
        df['Member Name'] = pd.NA
    return df

def extract_data_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    required_columns = ['Date', 'Description', 'Category', 'Income', 'Expense', 'Payment Method', 'Notes', 'Member Name']
    
    # Log the columns to check if Member Name exists
    print("CSV Columns:", df.columns.tolist())

    # Map 'Debit' column to 'Expense' if 'Debit' column exists
    if 'Debit' in df.columns:
        df['Expense'] = df['Debit']
    
    # Map 'Credit' column to 'Income' if 'Credit' column exists
    if 'Credit' in df.columns:
        df['Income'] = df['Credit']
    
    # Ensure all required columns are present
    for column in required_columns:
        if column not in df.columns:
            df[column] = pd.NA
    
    # Filter rows where Member Name is 'BRYAN BALLI' or 'Bryan Balli'
    df = df[df['Member Name'].str.strip().str.lower().isin(['bryan balli'])]
    
    # Convert pd.NA to empty string for JSON serialization and ensure numeric columns are numeric
    df = df.fillna('')
    df['Income'] = pd.to_numeric(df['Income'], errors='coerce').fillna(0)
    df['Expense'] = pd.to_numeric(df['Expense'], errors='coerce').fillna(0)
    
    # Log the data to ensure it is correctly formatted
    print("Extracted Data:", df.head())
    
    return df[required_columns]

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ExpenseForm()
    if form.validate_on_submit():
        if form.csv_file.data:
            filename = secure_filename(form.csv_file.data.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.csv_file.data.save(file_path)
            extracted_data = extract_data_from_csv(file_path)
            data_list = []
            for _, row in extracted_data.iterrows():
                sheet_type = form.sheet_type.data or 'LLC'  # Default to 'LLC' if not selected
                data = [
                    row['Date'], row['Description'], row['Category'],
                    row['Income'], row['Expense'], row['Payment Method'], row['Notes'], row['Member Name']
                ]
                data_list.append(data)
                if len(data_list) >= 100:
                    if sheet_type == 'LLC':
                        add_data_to_sheet(llc_sheet, data_list)
                    elif sheet_type == 'Personal':
                        add_data_to_sheet(personal_sheet, data_list)
                    data_list = []
            if data_list:
                if sheet_type == 'LLC':
                    add_data_to_sheet(llc_sheet, data_list)
                elif sheet_type == 'Personal':
                    add_data_to_sheet(personal_sheet, data_list)
            flash('Data from CSV file has been successfully added.')
        else:
            sheet_type = form.sheet_type.data or 'LLC'  # Default to 'LLC' if not selected
            date = form.date.data or ''
            description = form.description.data or ''
            category = form.category.data or ''
            income = float(form.income.data) if form.income.data else 0
            expense = float(form.expense.data) if form.expense.data else 0
            payment_method = form.payment_method.data or ''
            notes = form.notes.data or ''
            member_name = form.member_name.data or 'Bryan Balli'  # Default member name

            data = [date, description, category, income, expense, payment_method, notes, member_name]

            if sheet_type == 'LLC':
                add_data_to_sheet(llc_sheet, [data])
            elif sheet_type == 'Personal':
                add_data_to_sheet(personal_sheet, [data])

            flash('Data has been successfully added.')

        return redirect(url_for('summary'))
    return render_template('index.html', form=form)

@app.route('/summary')
def summary():
    llc_data = get_data_from_sheet(llc_sheet)
    personal_data = get_data_from_sheet(personal_sheet)

    llc_data['Income'] = pd.to_numeric(llc_data['Income'], errors='coerce').fillna(0)
    llc_data['Expense'] = pd.to_numeric(llc_data['Expense'], errors='coerce').fillna(0)
    personal_data['Income'] = pd.to_numeric(personal_data['Income'], errors='coerce').fillna(0)
    personal_data['Expense'] = pd.to_numeric(personal_data['Expense'], errors='coerce').fillna(0)

    # Log the data before filtering to ensure it contains the expected columns and data
    print("LLC Data Before Filtering:")
    print(llc_data.head())
    print("Personal Data Before Filtering:")
    print(personal_data.head())

    # Filter data for member name "Bryan Balli" (case insensitive)
    llc_data_filtered = llc_data[llc_data['Member Name'].str.strip().str.lower() == 'bryan balli']
    personal_data_filtered = personal_data[personal_data['Member Name'].str.strip().str.lower() == 'bryan balli']

    # Log the filtered data to check if the filtering worked correctly
    print("LLC Data After Filtering:")
    print(llc_data_filtered.head())
    print("Personal Data After Filtering:")
    print(personal_data_filtered.head())

    total_llc_income = llc_data_filtered['Income'].sum()
    total_llc_expenses = llc_data_filtered['Expense'].sum()
    total_personal_income = personal_data_filtered['Income'].sum()
    total_personal_expenses = personal_data_filtered['Expense'].sum()

    return render_template('summary.html', 
                           llc_data=llc_data_filtered, 
                           personal_data=personal_data_filtered, 
                           total_llc_income=total_llc_income, 
                           total_llc_expenses=total_llc_expenses, 
                           total_personal_income=total_personal_income, 
                           total_personal_expenses=total_personal_expenses)

if __name__ == '__main__':
    app.run(debug=True, port=5009)
