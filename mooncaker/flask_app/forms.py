from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Length

class AdminForm(FlaskForm):
	username = StringField('Username', validators=[InputRequired()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=5, max=32)])

class ConsoleForm(FlaskForm):
	command = StringField('Command', validators=[InputRequired()])