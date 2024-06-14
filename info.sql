CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00
);

CREATE UNIQUE INDEX username ON users (username);

CREATE TABLE transactions (
    id INTEGER NOT NULL,
    user_id INTEGER,
    transaction_type TEXT NOT NULL,
    stock_symbol TEXT NOT NULL,
    number_of_stocks NUMERIC NOT NULL,
    price_of_stock NUMERIC NOT NULL,
    current_time TEXT NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);








