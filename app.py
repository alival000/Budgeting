import datetime

from flask import Flask, render_template, request, redirect, url_for
import ast
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


@app.route('/insert')
def insert():
    return render_template('insert.html')


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

            if 'AUTOMATIC PAYMENT' not in sanitized_line and 'Payment Thank You' not in sanitized_line:
                new_file.write(sanitized_line)
                new_file.write('\n')

        new_file.close()

    to_be_reviewed = review_transactions(file_path)

    # TODO: delete saved file?

    return render_template("review_transactions.html", to_be_reviewed=to_be_reviewed, file_path=file_path)


@app.route('/last_month_comparison', methods=['GET'])
def get_last_month_comparison_data():
    cur = conn.cursor()

    try:
        #sql = f"SELECT SUM(rent) as rent,  FROM transactions WHERE date >  "

       # cur.execute(sql)
        pass
    except Exception as e:
        print("Error getting last month comparison: ", e)
        cur.close()
        return

    cur.close()
    return {}


@app.route('/recategorize_vendors', methods=['GET', 'POST'])
def submit_transactions():
    # send updated version to db
    # send in reviewed and from form
    cur = conn.cursor()

    renames = {}
    categories = {}
    transactions = {}
    for result in request.form:
        if result == 'filepath':
            continue

        section = result.split('-')[0]
        name = result.split('-')[1]

        if section == 'rename':
            renames[name] = request.form[result]
        elif section == 'category':
            categories[name] = request.form[result]
        elif section == 'trans':
            transactions[name] = request.form[result]

    for name_key, new_name in renames.items():
        if name_key == 'filepath':
            continue

        old_name = name_key[7:]
        new_category = ''
        new_transactions = []

        for category_key, category in categories.items():
            if old_name in category_key:
                new_category = category
                break

        for trans_key, trans_lst in transactions.items():
            if old_name in trans_key:
                new_transactions = ast.literal_eval(trans_lst)
                break

        for transaction in new_transactions:
            try:
                sql = f"INSERT INTO transactions (transaction_date, post_date, description, category, " \
                  f"type, amount) VALUES " \
                      f"('{transaction[0]}', '{transaction[1]}', '{new_name}', '{new_category}', '{transaction[4]}', " \
                      f"{transaction[5]})"

                cur.execute(sql)
            except Exception as e:
                print("Error inserting updated transactions: ", e)
                continue

    file_path = 'reviewed-' + request.form['filepath']
    reviewed_file = open(file_path)
    for transaction in reviewed_file:
        transaction_lst = transaction.split(',')
        try:
            sql = f"INSERT INTO transactions (transaction_date, post_date, description, category, " \
                  f"type, amount) VALUES " \
                  f"('{transaction_lst[0]}', '{transaction_lst[1]}', '{transaction_lst[2]}', '{transaction_lst[3]}', " \
                  f"'{transaction_lst[4]}', {transaction_lst[5]})"

            cur.execute(sql)
        except Exception as e:
            print("Error inserting transactions: ", e)
            print(transaction_lst)
            continue


    # TODO: create balance triggers in db

    # get all transactions with ids
    try:
        today = datetime.date.today()

        sql = f"SELECT * FROM transactions WHERE created_on = date('{today}')"

        cur.execute(sql)
        all_transactions = cur.fetchall()
    except Exception as e:
        print("Error finding transactions: ", e)

    cur.close()
    return render_template("assign_cost.html", transactions=all_transactions)


@app.route('/submit_payments', methods=['GET', 'POST'])
def submit_payments():
    cur = conn.cursor()

    for breakdown, transaction in request.form.items():
        trans_id, cost, assignment = transaction.split('_')
        cost = float(cost)

        ali_cost = 0
        ian_cost = 0

        # determine cost
        if assignment == 'Ali':
            ali_cost = cost
        elif assignment == 'Ian':
            ian_cost = cost
        elif assignment == 'Both':
            ali_cost = cost // 2
            ian_cost = cost // 2
        else:
            ali_cost = cost * .75
            ian_cost = cost * .25

        # add each transaction split to cost breakdown table
        try:
            sql = f"INSERT INTO cost_breakdown VALUES " \
                  f"({trans_id}, {ali_cost}, {ian_cost})"

            cur.execute(sql)
        except Exception as e:
            print("Error adding payment", e)

    cur.close()
    return redirect(url_for('index'))


@app.route('/add_money', methods=['GET', 'POST'])
def add_money():
    cur = conn.cursor()
    results = {}

    name = request.form['name']
    results['Rent'] = float(request.form['Rent'])
    results['Utilities'] = float(request.form['Utilities'])
    results['Groceries'] = float(request.form['Groceries'])
    results['Travel'] = float(request.form['Travel'])
    results['Food'] = float(request.form['Food'])
    results['Ian-Savings'] = float(request.form['Ian-Savings'])
    results['Misc'] = float(request.form['Misc'])
    results['Vacation'] = float(request.form['Vacation'])

    today = datetime.date.today()
    description = name + '-deposit'

    for category in results:
        # make transaction
        try:
            sql = f"INSERT INTO transactions (transaction_date, post_date, description, category, " \
                  f"type, amount) VALUES " \
                  f"('{today}', '{today}', '{description}', '{category}', 'deposit', " \
                  f"{results[category]})"
            cur.execute(sql)
        except Exception as e:
            print("Error when making deposit transaction: ", e)

        # get id
        try:
            sql = f"SELECT id " \
                  f"FROM transactions " \
                  f"WHERE transaction_date = date('{today}') " \
                  f"AND description = '{description}' " \
                  f"AND category = '{category}'" \
                  f"AND amount = {results[category]}"
            cur.execute(sql)
            trans_id = cur.fetchone()[0]
        except Exception as e:
            print("Error getting id: ", e)

        # add cost breakdown
        try:
            if name == "Ali":
                sql = f"INSERT INTO cost_breakdown VALUES " \
                      f"({trans_id}, {results[category]}, 0)"
            else:
                sql = f"INSERT INTO cost_breakdown VALUES " \
                      f"({trans_id}, 0, {results[category]})"

            cur.execute(sql)
        except Exception as e:
            print("Error when adding to cost breakdown: ", e)

    cur.close()
    return redirect(url_for('index'))


@app.route('/insert_transaction', methods=['GET', 'POST'])
def insert_transaction():
    transaction_date = request.form['transaction-date']
    description = request.form['description']
    category = request.form['category']
    trans_type = request.form['type']
    amount = float(request.form['amount'])
    assignment = request.form['breakdown']

    cur = conn.cursor()
    trans_id = 0

    try:
        sql = f"INSERT INTO transactions (transaction_date, post_date, description, category, " \
              f"type, amount) VALUES " \
              f"('{transaction_date}', '{transaction_date}', '{description}', '{category}', '{trans_type}', " \
              f"{amount})"
        cur.execute(sql)
    except Exception as e:
        print('Error inserting transaction: ', e)

    # get id
    try:
        sql = f"SELECT id " \
              f"FROM transactions " \
              f"WHERE transaction_date = date('{transaction_date}') " \
              f"AND description = '{description}' " \
              f"AND category = '{category}'" \
              f"AND amount = {amount}"
        cur.execute(sql)
        trans_id = cur.fetchone()[0]
    except Exception as e:
        print("Error getting id: ", e)

    # add to cost breakdown
    try:
        ali_cost = 0
        ian_cost = 0

        # determine cost
        if assignment == 'Ali':
            ali_cost = amount
        elif assignment == 'Ian':
            ian_cost = amount
        elif assignment == 'Both':
            ali_cost = amount // 2
            ian_cost = amount // 2
        else:
            ali_cost = amount * .75
            ian_cost = amount * .25

        sql = f"INSERT INTO cost_breakdown VALUES " \
              f"({trans_id}, {ali_cost}, {ian_cost})"

        cur.execute(sql)
    except Exception as e:
        print('Error inserting cost breakdown: ', e)

    cur.close()
    return redirect(url_for('index'))


@app.route('/last_statement_data', methods=['GET', 'POST'])
def get_statement_data():
    cur = conn.cursor()
    today = datetime.date.today()
    month = today.month
    year = today.year

    results = {
        'Rent': 0,
        'Groceries': 0,
        'Utilities': 0,
        'Travel': 0,
        'Food': 0,
        'Ian-Savings': 0,
        'Misc': 0,
        'Vacation': 0
    }
    totals = {}

    # TODO: fix for january

    try:
        sql = f"SELECT category, (SUM(amount) * -1) as total " \
              f"FROM transactions " \
              f"WHERE transaction_date >= date('{str(year) + '-' +  str(month-1) + '-14' }') " \
              f"AND transaction_date <= date('{str(year) + '-' + str(month) + '-13'}') " \
              f"GROUP BY category"

        cur.execute(sql)
        totals = cur.fetchall()
    except Exception as e:
        print('Error getting statement data: ', e)

    for tup in totals:
        results[tup[0]] = float(tup[1])

    cur.close()
    return results


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
    """
    :param file_path:
    :return: to_be_categorized
    """
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
                # join and write to reviewed file
                data = ','.join([transaction_date, posted_date, vendor_name, vendor_category, trans_type, amount])
                reviewed_file.write(data)

                is_categorized = True
                break

        # if not, add to dictionary: key: description [dict used to remove repeats
        if not is_categorized:
            if description not in to_be_categorized:
                to_be_categorized[description] = []
            to_be_categorized[description].append([transaction_date, posted_date, description, category, trans_type, amount])

        index += 1

    # close file
    cur.close()
    file.close()
    reviewed_file.close()

    # return dictionary
    return to_be_categorized
