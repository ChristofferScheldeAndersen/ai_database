import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

user_id = 1

def get_owned_stocks(user_id):
    """Helper function to get the list of dictionaries with owned stocks for the given user"""
    owned_stocks = []
    traded_stocks = db.execute("SELECT DISTINCT stock_symbol FROM transactions WHERE user_id = ?", user_id)

    for stock in traded_stocks:
        current_stock = stock["stock_symbol"]
        total_stock_number = 0
        sold_stocks_number = 0
        bought_stocks_number = 0
        average_buying_price = 0
        average_selling_price = 0

        bought_stocks = db.execute("SELECT number_of_stocks FROM transactions WHERE transaction_type = 'purchase' AND user_id = ? AND stock_symbol = ?", user_id, current_stock)
        for number in bought_stocks:
            total_stock_number += number["number_of_stocks"]
            bought_stocks_number += number["number_of_stocks"]
            average_buying_price += number["number_of_stocks"] * lookup(current_stock)['price']

        average_buying_price /= bought_stocks_number

        sold_stocks = db.execute("SELECT number_of_stocks FROM transactions WHERE transaction_type = 'sale' AND user_id = ? AND stock_symbol = ?", user_id, current_stock)
        for number in sold_stocks:
            total_stock_number -= number["number_of_stocks"]
            sold_stocks_number += number["number_of_stocks"]
            average_selling_price += number["number_of_stocks"] * lookup(current_stock)['price']

        average_selling_price += (bought_stocks_number - sold_stocks_number) * lookup(current_stock)['price']
        average_selling_price /= bought_stocks_number
        stock_return = (average_selling_price - average_buying_price) * bought_stocks_number

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

owned_stocks = get_owned_stocks(user_id)

for stock in owned_stocks:
    print("returns are ?", stock["return"])

