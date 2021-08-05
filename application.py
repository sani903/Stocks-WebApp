import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
import datetime

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    db.execute("CREATE TABLE IF NOT EXISTS ind(user_id INTEGER NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, nos INTEGER NOT NULL, price NUMERIC, total NUMERIC, FOREIGN KEY(user_id) REFERENCES users(id))")

    bef = db.execute("SELECT COUNT(name) FROM ind WHERE user_id = ?", session["user_id"])
    if bef[0]["COUNT(name)"] != 0:
        symbols = db.execute("SELECT symbol FROM ind WHERE user_id = ?", session["user_id"])
        i = 0
        for symbol in symbols:
            no = db.execute("SELECT nos FROM ind where user_id = ?", session["user_id"])
            db.execute("UPDATE ind SET price = :price, total = :total WHERE user_id = :user_id AND symbol = :symbol", price = lookup(symbol["symbol"])["price"], total = (lookup(symbol["symbol"])["price"] * no[i]["nos"]), user_id = session["user_id"], symbol = symbol["symbol"])
            i = i + 1
        stocks = db.execute("SELECT * FROM ind WHERE user_id = ?", session["user_id"])
        totcash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        extot = db.execute("SELECT SUM (total) FROM ind WHERE user_id = ?", session["user_id"])
        db.execute("CREATE TABLE IF NOT EXISTS sind(user_id INTEGER NOT NULL, total NUMERIC NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
        bef = db.execute("SELECT COUNT(total) FROM sind WHERE user_id = ?", session["user_id"])
        if bef[0]["COUNT(total)"] != 0:
            db.execute("UPDATE sind SET total = ? WHERE user_id = ?", extot[0]["SUM (total)"], session["user_id"])
        else:
            db.execute("INSERT INTO sind(user_id, total) VALUES (:user_id, :total)", user_id = session["user_id"], total = extot[0]["SUM (total)"])
        fintot = db.execute("SELECT total FROM sind WHERE user_id = ?", session["user_id"])
        return render_template("index.html", stocks = stocks, cash = usd(totcash[0]["cash"]), fintot = usd(fintot[0]["total"] + totcash[0]["cash"]))
    else:
        stocks = {}
        totcash = 10000.00
        fintot = totcash
        return render_template("index.html", stocks = stocks, cash = usd(totcash), fintot = usd(fintot))

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please specify which stock to buy", 403)
        if not request.form.get("nos"):
            return apology("Please specify how many stocks you want to buy", 403)
        if int(request.form.get("nos")) < 1:
            return apology("Please input a positive integer", 403)
        if request.form.get("nos").isnumeric() != True:
            return apology("Please input a positive integer", 403)
        symbol = request.form.get("symbol")
        if not lookup(symbol):
            return apology("Invalid symbol", 403)
        cost = (lookup(symbol)["price"]) * int(request.form.get("nos"))
        bro = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        money = bro[0]["cash"]
        if cost > money:
            return apology("Cannot afford", 400)
        money = money - cost
        bef = db.execute("SELECT COUNT (?) FROM ind WHERE user_id = ?", lookup(symbol)["symbol"], session["user_id"])
        if len(bef):
            tot = 0
            nob = 0
            tota = cost

        else:
            tot = db.execute("SELECT total FROM ind where symbol = ?", lookup(symbol)["symbol"])
            no = db.execute("SELECT nos FROM ind where symbol = ?", lookup(symbol)["symbol"])
            nob = no[0]["nos"]
            tota = tot[0]["total"] - cost




        nos = int(request.form.get("nos"))
        db.execute("UPDATE users SET cash = ? WHERE id = ?", money, session["user_id"])
        db.execute("CREATE TABLE IF NOT EXISTS buys (user_id INTEGER NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price NUMERIC NOT NULL, nos INTEGER NOT NULL, cost NUMERIC NOT NULL, time datetime NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
        db.execute("INSERT INTO hist(user_id, typ, symbol, name, price, nos, cost, time) VALUES (:user_id, :typ, :symbol, :name, :price, :nos, :cost, :time)", user_id = session["user_id"], typ = "BOUGHT", symbol = lookup(symbol)["symbol"], name = lookup(symbol)["name"], price = lookup(symbol)["price"], nos = nos, cost = cost, time = datetime.datetime.now())
        db.execute("INSERT INTO buys(user_id, symbol, name, price, nos, cost, time) VALUES (:user_id, :symbol, :name, :price, :nos, :cost, :time)", user_id = session["user_id"], symbol = lookup(symbol)["symbol"], name = lookup(symbol)["name"], price = lookup(symbol)["price"], nos = nos, cost = cost, time = datetime.datetime.now())
        bef = db.execute("SELECT symbol FROM ind WHERE symbol=:symbol AND user_id=:id", symbol=lookup(symbol)["symbol"], id=session["user_id"])

        # add to portfolio database
        # if symbol is new, add to portfolio
        if not bef:
            db.execute("INSERT INTO ind (symbol, name, nos, user_id, price, total) VALUES (:symbol, :name, :nos, :id, :price, :total)",
                name = lookup(symbol)["name"], symbol=lookup(symbol)["symbol"], nos=int(request.form.get("nos")), id = session["user_id"], price = lookup(symbol)["price"], total = cost)

        # if symbol is already in portfolio, update quantity of shares and total
        else:
            db.execute("UPDATE ind SET nos=nos+:nos WHERE symbol=:symbol AND user_id=:id",
                nos=int(request.form.get("nos")), symbol=lookup(symbol)["symbol"], id = session["user_id"]);
        return redirect("/")


    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    db.execute("CREATE TABLE IF NOT EXISTS hist(user_id INTEGER NOT NULL, typ TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price NUMERIC NOT NULL, nos INTEGER NOT NULL, cost NUMERIC NOT NULL, time DATETIME NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
    stocks = db.execute("SELECT * FROM hist WHERE user_id = ?", session["user_id"])
    return render_template("history.html", stocks = stocks)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        sym = request.form.get("symbol")
        if not lookup(sym):
            return apology("Invalid symbol", 403)
        else:
            name = lookup(sym)["name"]
            price = usd(lookup(sym)["price"])
            symb = lookup(sym)["symbol"]
            return render_template("quoted.html", name = name, price = price, symbol = symb)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif db.execute("SELECT * FROM users WHERE EXISTS (SELECT 1 FROM users WHERE username = ?)", request.form.get("username")):
            return apology("username already taken", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif request.form.get("password") != request.form.get("password1"):
            return apology("passwords don't match", 403)

        else:
            insert_query = "INSERT INTO users (username, hash, cash) VALUES (?, ?, ?)"
            db.execute(insert_query, request.form.get("username"), generate_password_hash(request.form.get("password")), 10000)
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
            session["user_id"] = rows[0]["id"]
            # Redirect user to home page
            return redirect("/")



    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        bef = db.execute("SELECT symbol FROM ind WHERE user_id = ?", session["user_id"])
        if not request.form.get("symbol"):
            return apology("Please specify which valid stock to sell", 403)
        symbol = request.form.get("symbol")
        p = db.execute("SELECT COUNT(symbol) FROM ind WHERE user_id = ?", session["user_id"])
        q = 0

        for i in range(int(p[0]["COUNT(symbol)"])):
            if symbol == bef[i]["symbol"]:
                q = 1
        if q == 0:
            return apology("Please specify which valid stock to sell", 403)
        if not request.form.get("shares"):
            return apology("Please specify how many stocks you want to sell", 403)
        if int(request.form.get("shares")) < 1:
            return apology("Please input a positive integer", 403)
        if request.form.get("shares").isnumeric() != True:
            return apology("Please input a positive integer", 403)
        hav = db.execute("SELECT nos FROM ind WHERE symbol = ? AND user_id = ?", request.form.get("symbol"), session["user_id"])
        if int(hav[0]["nos"]) < int(request.form.get("shares")):
            return apology("You do not own that many shares", 403)
        shares = int(request.form.get("shares"))
        db.execute("CREATE TABLE IF NOT EXISTS sells (user_id INTEGER NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price NUMERIC NOT NULL, shares INTEGER NOT NULL, cost NUMERIC NOT NULL, time datetime NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
        bro = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cost = (lookup(symbol)["price"]) * int(request.form.get("shares"))
        money = bro[0]["cash"]
        money = money + cost
        db.execute("UPDATE users SET cash = ? WHERE id = ?", money, session["user_id"])
        db.execute("INSERT INTO sells(user_id, symbol, name, price, shares, cost, time) VALUES (:user_id, :symbol, :name, :price, :shares, :cost, :time)", user_id = session["user_id"], symbol = lookup(symbol)["symbol"], name = lookup(symbol)["name"], price = lookup(symbol)["price"], shares = shares, cost = cost, time = datetime.datetime.now())
        db.execute("INSERT INTO hist(user_id, typ, symbol, name, price, nos, cost, time) VALUES (:user_id, :typ, :symbol, :name, :price, :nos, :cost, :time)", user_id = session["user_id"], typ = "SOLD", symbol = lookup(symbol)["symbol"], name = lookup(symbol)["name"], price = lookup(symbol)["price"], nos = shares, cost = cost, time = datetime.datetime.now())

        db.execute("UPDATE ind SET nos = ? WHERE symbol = ? AND user_id = ?", int(hav[0]["nos"]) - shares, request.form.get("symbol"), session["user_id"])
        hav = db.execute("SELECT nos FROM ind WHERE symbol = ? AND user_id = ?", request.form.get("symbol"), session["user_id"])
        if int(hav[0]["nos"]) == 0:
            db.execute("DELETE FROM ind WHERE symbol = ? AND user_id = ?", request.form.get("symbol"), session["user_id"])
        return redirect("/")

    else:
        stocks = db.execute("SELECT * FROM ind WHERE user_id = ?", session["user_id"])

        return render_template("sell.html", stocks = stocks)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
