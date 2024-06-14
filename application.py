"""
My personal touch is a feature that allows the user to see his returns for each currently owned stock on the main page.
"""

import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
application = Flask(__name__)

# Custom filter
application.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@application.after_request
def after_request(response):
    # Ensure responses aren't cached
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


def get_owned_stocks(user_id):
    # Helper function to calculate a list of dictionaries with owned stocks for the given user

    # Define the final list and make a list of dictionaries containing the different stocks our user ever traded
    owned_stocks = []
    traded_stocks = db.execute(
        "SELECT DISTINCT stock_symbol FROM transactions WHERE user_id = ?", user_id
    )

    # Iterate over traded stocks to calculate amount, current price, total amount and earnings if we sold all now.
    for stock in traded_stocks:
        current_stock = stock["stock_symbol"]
        sold_stocks_number = 0
        bought_stocks_number = 0
        average_buying_price = 0
        average_selling_price = 0

        bought_stocks = db.execute(
            "SELECT number_of_stocks, price_of_stock FROM transactions WHERE transaction_type = 'purchase' AND user_id = ? AND stock_symbol = ?", user_id, current_stock
        )
        for index in bought_stocks:
            bought_stocks_number += index["number_of_stocks"]
            average_buying_price += index["number_of_stocks"] * index["price_of_stock"]

        sold_stocks = db.execute(
            "SELECT number_of_stocks, price_of_stock FROM transactions WHERE transaction_type = 'sale' AND user_id = ? AND stock_symbol = ?", user_id, current_stock
        )
        for index in sold_stocks:
            sold_stocks_number += index["number_of_stocks"]
            average_selling_price += index["number_of_stocks"] * index["price_of_stock"]

        total_stock_number = bought_stocks_number - sold_stocks_number

        # We find the average buying price by taken the total money we spend and divide by the number we bought.
        average_buying_price /= bought_stocks_number

        # For the average selling price we also need to add our current shares sold at their current price
        average_selling_price += (bought_stocks_number - sold_stocks_number) * \
            lookup(current_stock)['price']
        average_selling_price /= bought_stocks_number

        # We find the total returns by multiplying our average return per stock with the total number we ever had.
        stock_return = (average_selling_price - average_buying_price) * bought_stocks_number

        # If we still own shares in the stock we append it as a dictionary to our original list.
        if total_stock_number > 0:
            price = lookup(current_stock)['price']
            total_value = price * total_stock_number
            price_usd = usd(price)
            total_value_usd = usd(total_value)
            stock_return = usd(stock_return)
            owned_stock = {
                "stock_symbol": current_stock,
                "number_of_stocks": total_stock_number,
                "price_of_stock": price_usd,
                "total_stock_value": total_value_usd,
                "total_stock_value_non_usd": total_value,
                "return": stock_return
            }
            owned_stocks.append(owned_stock)
    return owned_stocks


@application.route("/")
@login_required
def index():
    # Show portfolio of stocks

    user_id = session["user_id"]
    owned_stocks = get_owned_stocks(user_id)

    # Find current cash balance and save in a variable
    cash_balance = db.execute(
        "SELECT cash FROM users WHERE id = ?", user_id
    )[0]['cash']

    # Find total value of stocks and cash together and save in a variable
    total_balance = cash_balance
    for stock in owned_stocks:
        total_balance += stock["total_stock_value_non_usd"]

    # Convert to USD
    cash_balance = usd(cash_balance)
    total_balance = usd(total_balance)

    return render_template("index.html", owned_stocks=owned_stocks, cash_balance=cash_balance, total_balance=total_balance)


@application.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    # Buy shares of stock

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Define common variables for readability
        shares = request.form.get("shares")
        symbol = request.form.get("symbol")
        user_id = session["user_id"]

        # Ensure valid input
        if not symbol:
            return apology("must provide stock symbol", 400)
        elif not lookup(symbol):
            return apology("Invalid stock symbol", 400)
        elif not shares:
            return apology("must provide number of stocks", 400)

        # Ensure number of stocks is valid
        try:
            if int(shares) < 1:
                return apology("must provide positive number of stocks", 400)
        except ValueError:
            return apology("must provide whole number of stocks", 400)

        # Ensure user can afford purchase
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?", user_id
        )[0]['cash']
        number_of_stocks = int(shares)
        price_of_stock = (lookup(symbol))['price']
        purchase_price = int(shares) * price_of_stock
        if cash < purchase_price:
            return apology("You do not have enough cash for this purchase", 400)

        # Update users table in database to account for the purchase
        db.execute(
            "UPDATE users SET cash = cash - ? WHERE id = ?", purchase_price, user_id
        )

        # Update transactions table in database to accout for purchase
        transaction_type = "purchase"
        now = datetime.now()
        db.execute(
            """
            INSERT INTO transactions (
                user_id,
                transaction_type,
                stock_symbol,
                number_of_stocks,
                price_of_stock,
                current_time)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            user_id,
            transaction_type,
            symbol,
            number_of_stocks,
            price_of_stock,
            now.strftime("%Y-%m-%d %H:%M")
        )

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@application.route("/history")
@login_required
def history():
    # Show history of transactions

    # Make a list of dictionaries from transactions table
    transactions = db.execute(
        "SELECT * FROM transactions WHERE user_id = ?", session["user_id"]
    )

    # Change price in each dictionary to display a string as price.
    for transaction in transactions:
        transaction["price_of_stock"] = usd(transaction["price_of_stock"])

    return render_template("history.html", transactions=transactions)


@application.route("/login", methods=["GET", "POST"])
def login():
    # Log user in

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Define variables for readability
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure valid input
        if not username:
            return apology("must provide username", 403)
        elif not password:
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@application.route("/logout")
def logout():
    # Log user out

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@application.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    # Get stock quote.

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Define common variables for readability
        symbol = request.form.get("symbol")

        # Ensure valid input
        if not symbol:
            return apology("must provide stock symbol", 400)
        if not lookup(symbol):
            return apology("Invalid stock symbol", 400)

        # Find stock information to pass to html
        rows = lookup(symbol)
        rows["price"] = usd(rows["price"])

        # Redirect user to info page
        return render_template("stock_info.html", stock=rows)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@application.route("/register", methods=["GET", "POST"])
def register():
    # Register user

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Define common variables for readability
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure valid input
        if not username:
            return apology("must provide username", 400)
        elif not password:
            return apology("must provide password", 400)
        elif not confirmation:
            return apology("must provide password confirmation", 400)
        elif confirmation != password:
            return apology("must provide password confirmation", 400)
        elif len(db.execute("SELECT * FROM users WHERE username = ?", username)) > 0:
            return apology("username is already taken", 400)

        # Generate password hash
        password_hash = generate_password_hash(password)

        # Update users table in database
        db.execute(
            "INSERT INTO users (username, hash) VALUES(?, ?)", username, password_hash
        )

        # Find generated id for new user
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )

        # Remember which user id has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@application.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    # Sell shares of stock

    # Define common variables
    user_id = session["user_id"]

    # Create list of dictionaries for all owned stocks
    owned_stocks = get_owned_stocks(user_id)

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Define common variables
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Find number the user owns of the chosen stock
        for stock in owned_stocks:
            if stock["stock_symbol"] == symbol:
                available_stocks = stock["number_of_stocks"]
                break

        # Ensure valid input
        if not symbol:
            return apology("must provide stock symbol", 400)
        elif not lookup(symbol):
            return apology("Invalid stock symbol", 400)
        elif not shares:
            return apology("must provide number of stocks", 400)
        elif int(shares) < 1:
            return apology("must provide positive number of stocks", 400)
        elif int(shares) > available_stocks:
            return apology("you do not own enough of the chosen stock to sell", 400)

        # Update users table in database to account for the purchase
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?", user_id
        )[0]['cash']
        number_of_stocks = int(shares)
        price_of_stock = (lookup(symbol))['price']
        sale_price = number_of_stocks * price_of_stock
        db.execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?", sale_price, user_id
        )

        # Update transactions table in database to account for purchase
        transaction_type = "sale"
        now = datetime.now()
        db.execute(
            """
            INSERT INTO transactions (
                user_id,
                transaction_type,
                stock_symbol,
                number_of_stocks,
                price_of_stock,
                current_time)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            user_id,
            transaction_type,
            symbol,
            number_of_stocks,
            price_of_stock,
            now.strftime("%Y-%m-%d %H:%M")
        )

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", owned_stocks=owned_stocks)
