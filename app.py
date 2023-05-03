from flask import Flask, render_template, request, redirect, url_for
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    test = 1;
    return render_template('index.html')


@app.route('/import')
def import_statement_page():
    return render_template('import.html')


@app.route('/deposit')
def deposit():
    return render_template('deposit.html')


@app.route('/monthly')
def monthly_breakdown():
    return render_template('monthly.html')


@app.route('/import_file', methods=['POST'])
def import_statement():
    file = request.files['statement']
    if file.filename != '':
        file_path = r'statements\\' + file.filename
        new_file = open(file_path, 'x')

        for line in file:
            sanitized_line = str(line)
            # remove b'
            sanitized_line = sanitized_line[2:]
            # remove ,\n'
            sanitized_line = sanitized_line[:-4]

            new_file.write(sanitized_line)
            new_file.write('\n')

        new_file.close()

    return redirect(url_for('index'))
