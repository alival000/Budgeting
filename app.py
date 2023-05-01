from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def index():
    test = 1;
    return render_template('index.html')

@app.route('/import')
def import_statement():
    return render_template('import.html')

