from flask import Flask
from flask.ext.admin import Admin
from settings_local import FLASK_SECRET_KEY

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
admin = Admin()