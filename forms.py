from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DecimalField, FileField
from wtforms.validators import Optional

class ExpenseForm(FlaskForm):
    sheet_type = SelectField('Sheet Type', choices=[('LLC', 'Code & Palette (LLC)'), ('Personal', 'Bryan (Personal)')], validators=[Optional()])
    date = StringField('Date', validators=[Optional()])
    description = StringField('Description', validators=[Optional()])
    category = StringField('Category', validators=[Optional()])
    income = DecimalField('Income', places=2, validators=[Optional()])
    expense = DecimalField('Expense', places=2, validators=[Optional()])
    payment_method = StringField('Payment Method', validators=[Optional()])
    notes = StringField('Notes', validators=[Optional()])
    member_name = StringField('Member Name', validators=[Optional()])
    csv_file = FileField('Upload CSV', validators=[Optional()])
    submit = SubmitField('Submit')
