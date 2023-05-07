from flask import Flask, render_template, request, redirect, url_for
import datetime
import os
import psycopg2
from dotenv import load_dotenv

# -------- notes -------------------------------------------------------------

'''
    * statements are from the 14th to the 13th
'''

# -------- configuration -------------------------------------------------------------

app = Flask(__name__)

load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD')

conn = psycopg2.connect(
        host="localhost",
        database="budgeting",
        user='postgres',
        password=os.environ['DB_PASSWORD'])
conn.autocommit = True

# -------- endpoints -------------------------------------------------------------

@app.route('/')
def index():
    overview_data = get_overview_data();
    #total_spending_data = get_total_spending_data();
    #categorized_data = get_categorized_data();

    return render_template('index.html', overview_data=overview_data)


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

    to_be_reviewed = review_transactions(file_path)

    # TODO: delete saved file?

    return render_template("review_transactions.html", to_be_reviewed=to_be_reviewed)


@app.route('/last_month_comparison', methods=['GET'])
def get_last_month_comparison_data():
    cur = conn.cursor()

    try:
        sql = f"SELECT SUM(rent) as rent,  FROM transactions WHERE date >  "

        cur.execute(sql)
    except Exception as e:
        print("Error getting last month comparison: ", e)
        cur.close()
        return

    cur.close()
    return {}


@app.route('/recategorize_vendors', methods=['GET', 'POST'])
def review_transactions():
    print(request.form)
    return redirect(url_for('index'))

# -------- functions -------------------------------------------------------------


def add_transactions(filename):
    """
    :param filename:
    :return: None

    adds transactions into database
    """
    cur = conn.cursor()

    file = open(filename, 'r')
    header = False
    for line in file:

        # reads in the header
        if not header:
            header = True
            continue

        transaction_date, posted_date, description, category, trans_type, amount = line.split(',')
        description = description.replace("'","")

        try:
            sql = f"INSERT INTO transactions (transaction_date, post_date, description, category, " \
                  f"type, amount) VALUES " \
                  f"('{transaction_date}', '{posted_date}', '{description}', '{category}', '{trans_type}', " \
                  f"{amount})"

            cur.execute(sql)
        except Exception as e:
            print("Error inserting transaction: ", e)
            cur.close()
            return

    cur.close()


def get_overview_data():
    """
    :return: list
    query data of overall savings for each person
    """
    cur = conn.cursor()

    try:
        sql = f"SELECT * FROM balances ORDER BY name ASC"

        cur.execute(sql)
        res = cur.fetchall()

        res_dict = {
            'Ali': {},
            'Ian': {}
        }

        # format data to send to html
        for item in res:
            res_dict[item[0]] = {
                'rent': float(item[1]),
                'utilities': float(item[2]),
                'groceries': float(item[3]),
                'travel': float(item[4]),
                'food': float(item[5]),
                'ian_savings': float(item[6]),
                'misc': float(item[7])
            }

        res_dict['Total'] = {
            'rent': res_dict['Ali']['rent'] + res_dict['Ian']['rent'],
            'utilities': res_dict['Ali']['utilities'] + res_dict['Ian']['utilities'],
            'groceries': res_dict['Ali']['groceries'] + res_dict['Ian']['groceries'],
            'travel': res_dict['Ali']['travel'] + res_dict['Ian']['travel'],
            'food': res_dict['Ali']['food'] + res_dict['Ian']['food'],
            'ian_savings': res_dict['Ali']['ian_savings'] + res_dict['Ian']['ian_savings'],
            'misc': res_dict['Ali']['misc'] + res_dict['Ian']['misc']
        }

        return res_dict
    except Exception as e:
        print("Error when getting Overview Data: ", e)
        cur.close()
        return

    cur.close()


def review_transactions(file_path):
    cur = conn.cursor()
    to_be_categorized = {}

    # open file
    reviewed_file_path = 'reviewed-' + file_path

    file = open(file_path, 'r')
    reviewed_file = open(reviewed_file_path, 'x')

    # query for each category
    try:
        sql = f"SELECT *" \
              f"FROM categorized_vendors"

        cur.execute(sql)
        categorized_vendors = cur.fetchall()
    except Exception as e:
        print("Error when getting vendors: ", e)
        cur.close()

    index = 0
    header = False
    # go through each line and see if it has been categorized
    for line in file:
        if not header:
            header = True
            index += 1
            continue

        is_categorized = False
        transaction_date, posted_date, description, category, trans_type, amount = line.split(',')

        for vendor in categorized_vendors:
            vendor_category, vendor_name = vendor[0], vendor[1]

            if vendor_name in description:
                category = vendor_category

                # join and write to reviewed file
                data = ','.join([transaction_date, posted_date, description, category, trans_type, amount])
                reviewed_file.write(data)

                is_categorized = True
                break

        # if not, add to dictionary: key: description [dict used to remove repeats
        if not is_categorized:
            to_be_categorized[description] = ''

        index += 1

    # close file
    cur.close()
    file.close()
    reviewed_file.close()

    print(to_be_categorized)
    # return dictionary
    return to_be_categorized
