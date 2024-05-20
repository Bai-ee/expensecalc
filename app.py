from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import time
from forms import ExpenseForm
from google.cloud import language_v1

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'expenses-administration-fb7c867085c4.json'
NATURAL_LANGUAGE_KEY_FILE = 'expenses-administration-07026ddc784a.json'

# Define the scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Authenticate with the service account
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

# Open your Google Sheets
llc_sheet = client.open("LLC (Code & Palette) Sheet").sheet1
personal_sheet = client.open("Personal (Bryan) Sheet").sheet1

def clear_sheet(sheet):
    # Clear the sheet data
    sheet.clear()
    # Re-add the header row
    header = ['Date', 'Description', 'Category', 'Income', 'Expense', 'Payment Method', 'Notes', 'Member Name']
    sheet.append_row(header)

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

def categorize_expense(description, entities):
    # Specific categories for known entities
    known_entities = {
    "CARBON": "Fast Food",
    "ARDRIVE": "Subscriptions",
    "CAR WASH": "Car",
       "LEGALZOOM": "Legal",
       "LEGAL": "Legal",
    "MCDONALDS": "Fast Food",
     "SUSHI": "Fast Food",
      "MEDICINE": "Pharmacy",
    "METRA": "Metra",
    "CAR WASH": "Car",
    "H MART": "Groceries",
    "RAMEN": "Fast Food",
    "SMOKE": "Personal",
    "SLICE": "Fast Food",
    "RECORD": "Fast Food",
    "NOODLE": "Fast Food",
    "TACO": "Fast Food",
    "BBQ": "Fast Food",
    "AMZN": "Amazon",
    "CERMAK": "Groceries",
    "DUNKIN": "Fast Food",
    "STARBUCKS": "Fast Food",
    "MCDONALD'S": "Fast Food",
    "BURGER KING": "Fast Food",
    "TACO BELL": "Fast Food",
    "CHIPOTLE": "Fast Food",
    "SUBWAY": "Fast Food",
    "KFC": "Fast Food",
    "WENDY'S": "Fast Food",
    "WALGREENS": "Pharmacy",
    "CVS": "Pharmacy",
    "RITE AID": "Pharmacy",
    "COSTCO": "Groceries",
    "WALMART": "Retail",
    "TARGET": "Retail",
    "AMAZON": "Online Shopping",
    "EBAY": "Online Shopping",
    "PAYPAL": "Payment Service",
    "FIVERR": "Freelance Service",
    "UPWORK": "Freelance Service",
    "TRADER": "Groceries",
    "GRUBHUB": "Food Delivery",
    "UBER EATS": "Food Delivery",
    "LYFT": "Transportation",
    "UBER": "Transportation",
    "AIRBNB": "Travel",
    "EXPEDIA": "Travel",
    "DELTA": "Travel",
    "AMERICAN AIRLINES": "Travel",
    "UNITED AIRLINES": "Travel",
    "SOUTHWEST": "Travel",
    "SPOTIFY": "Subscription",
    "NETFLIX": "Subscription",
    "HULU": "Subscription",
    "DISNEY PLUS": "Subscription"
    }

    # Check if description matches any known entity
    for entity, category in known_entities.items():
        if entity.lower() in description.lower():
            return category

    # Specific categories for broader terms
    categories = {
        "Food": ["dinner", "lunch", "groceries", "restaurant", "cafe", "food"],
        "Business": ["office", "software", "subscription", "domain", "advertising"],
        "Personal": ["rent", "gym", "clothes", "entertainment"],
        "Family": ["school", "tuition", "family dinner", "daycare", "family"]
    }

    # Use entities to help categorize
    for entity in entities:
        for category, keywords in categories.items():
            if any(keyword in entity.name.lower() for keyword in keywords):
                return category

    # Fallback to description-based categorization
    for category, keywords in categories.items():
        if any(keyword in description.lower() for keyword in keywords):
            return category

    return "Uncategorized"

def entity_type_explanation(entity_type):
    explanations = {
        "PERSON": "Represents a person, including fictional characters.",
        "LOCATION": "Represents a geographical location, such as a city, country, or landmark.",
        "ORGANIZATION": "Represents an organization, such as a company, institution, or government.",
        "EVENT": "Represents an event, such as a conference, meeting, or concert.",
        "WORK_OF_ART": "Represents a work of art, such as a book, song, movie, or painting.",
        "CONSUMER_GOOD": "Represents a consumer product.",
        "OTHER": "Represents other entities that do not fall into the predefined categories.",
        "ADDRESS": "Represents a physical address.",
        "NUMBER": "Represents a numeric value.",
        "PRICE": "Represents the price of an item."
    }
    return explanations.get(entity_type, "Unknown entity type")

def analyze_expenses(data):
    client = language_v1.LanguageServiceClient.from_service_account_json(NATURAL_LANGUAGE_KEY_FILE)
    insights = []
    
    description_totals = data.groupby('Description')['Expense'].sum().reset_index()

    for description in description_totals['Description']:
        document = language_v1.Document(content=description, type_=language_v1.Document.Type.PLAIN_TEXT)
        response = client.analyze_entities(document=document)
        entities = response.entities
        
        for entity in entities:
            total_expense = description_totals[description_totals['Description'] == description]['Expense'].values[0]
            category = categorize_expense(description, entities)
            insights.append({
                'description': description,
                'name': entity.name,
                'type': language_v1.Entity.Type(entity.type_).name,
                'salience': entity.salience,
                'total_expense': total_expense,
                'category': category,
                'entity_explanation': entity_type_explanation(language_v1.Entity.Type(entity.type_).name)
            })
    return insights

def calculate_category_totals(insights):
    category_totals = {}
    category_descriptions = {}

    for insight in insights:
        category = insight['category']
        description = insight['description']
        total_expense = insight['total_expense']

        if category not in category_totals:
            category_totals[category] = 0
            category_descriptions[category] = set()

        if description not in category_descriptions[category]:
            category_totals[category] += total_expense
            category_descriptions[category].add(description)

    return category_totals

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ExpenseForm()
    if form.validate_on_submit():
        if form.csv_file.data:
            filename = secure_filename(form.csv_file.data.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.csv_file.data.save(file_path)
            extracted_data = extract_data_from_csv(file_path)
            sheet_type = form.sheet_type.data or 'LLC'  # Default to 'LLC' if not selected

            # Clear the sheet before adding new data
            if sheet_type == 'LLC':
                clear_sheet(llc_sheet)
            else:
                clear_sheet(personal_sheet)

            data_list = []
            for _, row in extracted_data.iterrows():
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
            session['selected_sheet'] = sheet_type  # Store the selected sheet type in the session
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

            # Clear the sheet before adding new data
            if sheet_type == 'LLC':
                clear_sheet(llc_sheet)
                add_data_to_sheet(llc_sheet, [data])
            elif sheet_type == 'Personal':
                clear_sheet(personal_sheet)
                add_data_to_sheet(personal_sheet, [data])

            flash('Data has been successfully added.')
            session['selected_sheet'] = sheet_type  # Store the selected sheet type in the session

        session['start_date'] = form.start_date.data
        session['end_date'] = form.end_date.data

        return redirect(url_for('summary'))
    return render_template('index.html', form=form)

@app.route('/summary')
def summary():
    selected_sheet = session.get('selected_sheet', 'LLC')  # Default to 'LLC' if not set
    start_date = session.get('start_date')
    end_date = session.get('end_date')

    if selected_sheet == 'LLC':
        data = get_data_from_sheet(llc_sheet)
    else:
        data = get_data_from_sheet(personal_sheet)

    data['Income'] = pd.to_numeric(data['Income'], errors='coerce').fillna(0)
    data['Expense'] = pd.to_numeric(data['Expense'], errors='coerce').fillna(0)
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')

    # Log the data before filtering to ensure it contains the expected columns and data
    print(f"{selected_sheet} Data Before Filtering:")
    print(data.head())

    # Filter data for member name "Bryan Balli" (case insensitive)
    data_filtered = data[data['Member Name'].str.strip().str.lower() == 'bryan balli']

    # Filter data by the selected date range
    if start_date:
        data_filtered = data_filtered[data_filtered['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        data_filtered = data_filtered[data_filtered['Date'] <= pd.to_datetime(end_date)]

    # Log the filtered data to check if the filtering worked correctly
    print(f"{selected_sheet} Data After Filtering:")
    print(data_filtered.head())

    total_income = data_filtered['Income'].sum()
    total_expenses = data_filtered['Expense'].sum()
    line_item_count = len(data_filtered)

    # Extract descriptions for analysis
    insights = analyze_expenses(data_filtered)

    # Calculate total expenses for each category from insights
    category_totals_from_insights = calculate_category_totals(insights)

    # Calculate total expenses for each category
    category_totals = data_filtered.groupby('Category')['Expense'].sum().reset_index()

    return render_template('summary.html', 
                           data=data_filtered, 
                           total_income=total_income, 
                           total_expenses=total_expenses, 
                           line_item_count=line_item_count, 
                           selected_sheet=selected_sheet, 
                           insights=insights,
                           category_totals=category_totals,
                           category_totals_from_insights=category_totals_from_insights)

if __name__ == '__main__':
    app.run(debug=True, port=5010)
