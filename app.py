from flask import Flask, render_template, request, redirect
import sqlite3, os, datetime

app = Flask(__name__)
DB_FILE = "database.db"

# Initialize database and tables
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, username TEXT UNIQUE, password TEXT, role TEXT)''')
        c.execute('''CREATE TABLE meals (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, date TEXT, meals INTEGER)''')
        c.execute('''CREATE TABLE deposits (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, amount REAL, date TEXT)''')
        c.execute('''CREATE TABLE bazar (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, cost REAL, date TEXT, added_by INTEGER, status TEXT)''')
        try:
            c.execute("INSERT INTO members (name, username, password, role) VALUES (?, ?, ?, ?)",
                      ("Shahadat","admin","1234","admin"))
        except:
            pass
        conn.commit()
        conn.close()

init_db()

# DB connection helper
def connect_db():
    return sqlite3.connect(DB_FILE)

# ---------------- LOGIN ----------------
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def do_login():
    username = request.form["username"]
    password = request.form["password"]
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE username=? AND password=?", (username,password))
    user = c.fetchone()
    conn.close()
    if user:
        if user[4] == "admin":
            return redirect("/admin")
        else:
            return redirect(f"/member/{user[0]}")
    else:
        return "Login Failed"

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin_dashboard():
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE role!='admin'")
    members = c.fetchall()
    c.execute("SELECT b.id,b.item,b.cost,b.date,m.name FROM bazar b JOIN members m ON b.added_by=m.id WHERE b.status='pending'")
    pending_bazar = c.fetchall()
    c.execute("SELECT d.id,d.amount,d.date,m.name FROM deposits d JOIN members m ON d.member_id=m.id")
    all_deposits = c.fetchall()
    c.execute("SELECT me.id,me.date,me.meals,m.name FROM meals me JOIN members m ON me.member_id=m.id")
    all_meals = c.fetchall()
    conn.close()
    return render_template("admin.html", members=members, pending_bazar=pending_bazar,
                           all_deposits=all_deposits, all_meals=all_meals)

@app.route("/admin/add_member", methods=["POST"])
def add_member():
    name = request.form["name"]
    username = request.form["username"]
    password = request.form["password"]
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO members (name, username, password, role) VALUES (?, ?, ?, ?)", (name,username,password,"member"))
        conn.commit()
    except:
        conn.close()
        return "Username already exists"
    conn.close()
    return redirect("/admin")

@app.route("/admin/approve_bazar/<int:bazar_id>")
def approve_bazar(bazar_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("UPDATE bazar SET status='approved' WHERE id=?", (bazar_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin/add_deposit", methods=["POST"])
def add_deposit():
    member_id = int(request.form["member_id"])
    amount = float(request.form["amount"])
    date = datetime.date.today().isoformat()
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO deposits (member_id, amount, date) VALUES (?, ?, ?)", (member_id, amount, date))
    conn.commit()
    conn.close()
    return redirect("/admin")

# ---------------- MEMBER ----------------
@app.route("/member/<int:member_id>")
def member_dashboard(member_id):
    today = datetime.date.today().isoformat()
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    member = c.fetchone()
    c.execute("SELECT * FROM meals WHERE member_id=?", (member_id,))
    meals = c.fetchall()
    c.execute("SELECT * FROM deposits WHERE member_id=?", (member_id,))
    deposits = c.fetchall()
    c.execute("SELECT SUM(cost) FROM bazar WHERE status='approved'")
    total_bazar = c.fetchone()[0] or 0
    c.execute("SELECT SUM(meals) FROM meals")
    total_meals = c.fetchone()[0] or 0
    meal_rate = total_bazar/total_meals if total_meals>0 else 0
    member_meals = sum([m[3] for m in meals])
    member_deposit = sum([d[2] for d in deposits])
    balance = member_deposit - member_meals*meal_rate
    conn.close()
    return render_template("member.html", member=member, meals=meals, deposits=deposits,
                           meal_rate=meal_rate, balance=balance, member_meals=member_meals,
                           total_bazar=total_bazar, total_meals=total_meals, today=today)

@app.route("/member/<int:member_id>/add_meal", methods=["POST"])
def add_meal(member_id):
    meals = int(request.form["meals"])
    date = datetime.date.today().isoformat()
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO meals (member_id, date, meals) VALUES (?, ?, ?)", (member_id,date,meals))
    conn.commit()
    conn.close()
    return redirect(f"/member/{member_id}")

@app.route("/member/<int:member_id>/add_bazar", methods=["POST"])
def add_bazar(member_id):
    item = request.form["item"]
    cost = float(request.form["cost"])
    date = datetime.date.today().isoformat()
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO bazar (item, cost, date, added_by, status) VALUES (?, ?, ?, ?, ?)", (item,cost,date,member_id,"pending"))
    conn.commit()
    conn.close()
    return redirect(f"/member/{member_id}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)