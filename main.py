from flask import Flask, render_template_string, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///betting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.String(120), nullable=False)
    result = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'deposit' or 'withdrawal'
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return render_template_string(home_html)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username already exists')
                return redirect(url_for('register'))
            
            new_user = User(username=username, password=generate_password_hash(password, method='sha256'))
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            # Log the error for debugging
            print(f"Error during registration: {e}")
            flash('An error occurred during registration. Please try again.')
            return redirect(url_for('register'))
    
    return render_template_string(register_html)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template_string(login_html)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string(dashboard_html, user=current_user)

@app.route('/place_bet', methods=['POST'])
@login_required
def place_bet():
    amount = float(request.form.get('amount'))
    prediction = request.form.get('prediction')
    
    if current_user.balance < amount:
        flash('Insufficient balance')
        return redirect(url_for('dashboard'))
    
    new_bet = Bet(user_id=current_user.id, amount=amount, prediction=prediction)
    current_user.balance -= amount
    db.session.add(new_bet)
    db.session.commit()
    
    flash('Bet placed successfully')
    return redirect(url_for('dashboard'))

@app.route('/bet_history')
@login_required
def bet_history():
    bets = Bet.query.filter_by(user_id=current_user.id).order_by(Bet.created_at.desc()).all()
    return render_template_string(bet_history_html, bets=bets)

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        current_user.balance += amount
        new_transaction = Transaction(user_id=current_user.id, amount=amount, type='deposit')
        db.session.add(new_transaction)
        db.session.commit()
        flash(f'Deposit of ${amount} successful')
        return redirect(url_for('dashboard'))
    return render_template_string(deposit_html)

@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        if current_user.balance < amount:
            flash('Insufficient balance')
        else:
            current_user.balance -= amount
            new_transaction = Transaction(user_id=current_user.id, amount=amount, type='withdrawal')
            db.session.add(new_transaction)
            db.session.commit()
            flash(f'Withdrawal of ${amount} requested')
        return redirect(url_for('dashboard'))
    return render_template_string(withdraw_html)

@app.route('/transactions')
@login_required
def transactions():
    user_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).all()
    return render_template_string(transactions_html, transactions=user_transactions)

@app.route('/update_bet_result/<int:bet_id>', methods=['POST'])
@login_required
def update_bet_result(bet_id):
    result = request.form.get('result')
    bet = Bet.query.get(bet_id)
    
    if not bet:
        flash('Bet not found')
        return redirect(url_for('dashboard'))
    
    if bet.result != 'Pending':
        flash('Bet result already updated')
        return redirect(url_for('dashboard'))
    
    bet.result = result
    db.session.commit()
    
    if result == 'Win':
        current_user.balance += bet.amount * 2  # Assuming 2x payout
        db.session.commit()

    flash('Bet result updated')
    return redirect(url_for('dashboard'))

# Templates (HTML as string literals)
home_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Home</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/swiper/swiper-bundle.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper/swiper-bundle.min.css" />
    <style>
        .swiper-container {
            width: 100%;
            height: 400px;
        }
        .swiper-slide {
            display: flex;
            justify-content: center;
            align-items: center;
            background: #4a90e2;
            color: white;
            font-size: 24px;
            text-align: center;
        }
    </style>
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">BetPro</h1>
    </header>

    <!-- Top Slider Section -->
    <div class="swiper-container mb-8">
        <div class="swiper-wrapper">
            <div class="swiper-slide">
                <div>
                    <h2>Join the Excitement!</h2>
                    <p>Bet on your favorite teams and win big!</p>
                    <a href="{{ url_for('login') }}" class="bg-white text-blue-600 font-bold py-2 px-4 rounded mr-4">Login</a>
                    <a href="{{ url_for('register') }}" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Register</a>
                </div>
            </div>
            <div class="swiper-slide">
                <div>
                    <h2>Bet Responsibly</h2>
                    <p>Your fun is our priority! Play responsibly and enjoy the thrill.</p>
                    <a href="{{ url_for('login') }}" class="bg-white text-blue-600 font-bold py-2 px-4 rounded mr-4">Login</a>
                    <a href="{{ url_for('register') }}" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Register</a>
                </div>
            </div>
            <div class="swiper-slide">
                <div>
                    <h2>Latest Betting Odds!</h2>
                    <p>Check out the latest odds and make your predictions!</p>
                    <a href="{{ url_for('login') }}" class="bg-white text-blue-600 font-bold py-2 px-4 rounded mr-4">Login</a>
                    <a href="{{ url_for('register') }}" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Register</a>
                </div>
            </div>
        </div>
        <div class="swiper-pagination"></div>
        <div class="swiper-button-next"></div>
        <div class="swiper-button-prev"></div>
    </div>

    <main class="container mx-auto mt-8 p-4">
        <h2 class="text-3xl mb-4">Welcome to BetPro</h2>
        <p class="mb-4">Explore a variety of betting options and enhance your gaming experience.</p>

        <section class="mb-8">
            <h3 class="text-2xl mb-4">Featured Matches</h3>
            <ul class="list-disc list-inside">
                <li>Match 1: Team A vs Team B - Odds: 1.5</li>
                <li>Match 2: Team C vs Team D - Odds: 2.0</li>
                <li>Match 3: Team E vs Team F - Odds: 1.8</li>
                <li>Match 4: Team G vs Team H - Odds: 1.7</li>
            </ul>
        </section>

        <section class="bg-blue-100 p-4 rounded-lg mb-8">
            <h3 class="text-2xl mb-4">Ready to Place Your Bets?</h3>
            <p class="mb-4">Join us now and take advantage of exciting betting opportunities!</p>
            <a href="{{ url_for('register') }}" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Get Started</a>
        </section>

        <section class="mb-8">
            <h3 class="text-2xl mb-4">Upcoming Matches</h3>
            <ul class="list-disc list-inside">
                <li>Match 1: Team X vs Team Y - Date & Time</li>
                <li>Match 2: Team Z vs Team W - Date & Time</li>
                <li>Match 3: Team U vs Team V - Date & Time</li>
                <li>Match 4: Team S vs Team T - Date & Time</li>
                <li>Match 5: Team R vs Team Q - Date & Time</li>
            </ul>
        </section>

        <section>
            <h3 class="text-2xl mb-4">Betting Tips</h3>
            <p>Stay informed with the latest betting tips and strategies to maximize your winning potential. Consider factors like team performance, player injuries, and historical data when placing your bets.</p>
        </section>

        <section>
            <h3 class="text-2xl mb-4">Responsible Gambling</h3>
            <p>At BetPro, we encourage responsible gambling. Please gamble responsibly and seek help if you feel that gambling is becoming a problem.</p>
            <p>For support, you can visit: <a href="https://www.begambleaware.org/" class="text-blue-500 underline">BeGambleAware</a></p>
        </section>
    </main>

    <footer class="bg-gray-800 text-white text-center p-4 mt-8">
        <p>&copy; 2024 BetPro. All rights reserved.</p>
    </footer>

    <script>
        const swiper = new Swiper('.swiper-container', {
            loop: true,
            pagination: {
                el: '.swiper-pagination',
                clickable: true,
            },
            navigation: {
                nextEl: '.swiper-button-next',
                prevEl: '.swiper-button-prev',
            },
        });
    </script>
</body>
</html>
"""





register_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Register</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">BetPro</h1>
    </header>
    <main class="container mx-auto mt-8 p-4">
        <h2 class="text-3xl mb-4">Register</h2>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST" class="max-w-md">
            <div class="mb-4">
                <label for="username" class="block mb-2">Username:</label>
                <input type="text" id="username" name="username" required class="w-full p-2 border rounded">
            </div>
            <div class="mb-4">
                <label for="password" class="block mb-2">Password:</label>
                <input type="password" id="password" name="password" required class="w-full p-2 border rounded">
            </div>
            <button type="submit" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Register</button>
        </form>
        <p class="mt-4">Already have an account? <a href="{{ url_for('login') }}" class="text-blue-500">Login here</a>.</p>
    </main>
</body>
</html>
"""

login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">BetPro</h1>
    </header>
    <main class="container mx-auto mt-8 p-4">
        <h2 class="text-3xl mb-4">Login</h2>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST" class="max-w-md">
            <div class="mb-4">
                <label for="username" class="block mb-2">Username:</label>
                <input type="text" id="username" name="username" required class="w-full p-2 border rounded">
            </div>
            <div class="mb-4">
                <label for="password" class="block mb-2">Password:</label>
                <input type="password" id="password" name="password" required class="w-full p-2 border rounded">
            </div>
            <button type="submit" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">Login</button>
        </form>
        <p class="mt-4">Don't have an account? <a href="{{ url_for('register') }}" class="text-green-500">Register here</a>.</p>
    </main>
</body>
</html>
"""

dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">Welcome, {{ user.username }}</h1>
        <a href="{{ url_for('logout') }}" class="bg-red-500 hover:bg-red-700 text-white py-2 px-4 rounded">Logout</a>
    </header>
    <main class="container mx-auto mt-8 p-4">
        <h2 class="text-3xl mb-4">Your Dashboard</h2>
        <p>Your balance: ${{ user.balance }}</p>
        <h3 class="text-2xl mt-4">Place a Bet</h3>
        <form method="POST" action="{{ url_for('place_bet') }}" class="mb-4">
            <div class="mb-4">
                <label for="amount" class="block mb-2">Amount:</label>
                <input type="number" id="amount" name="amount" required class="w-full p-2 border rounded" step="0.01">
            </div>
            <div class="mb-4">
                <label for="prediction" class="block mb-2">Prediction:</label>
                <input type="text" id="prediction" name="prediction" required class="w-full p-2 border rounded">
            </div>
            <button type="submit" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Place Bet</button>
        </form>
        <h3 class="text-2xl mt-4">Your Bet History</h3>
        <a href="{{ url_for('bet_history') }}" class="text-blue-500">View Bet History</a>
        <h3 class="text-2xl mt-4">Deposit Money</h3>
        <a href="{{ url_for('deposit') }}" class="text-green-500">Deposit</a>
        <h3 class="text-2xl mt-4">Withdraw Money</h3>
        <a href="{{ url_for('withdraw') }}" class="text-red-500">Withdraw</a>
    </main>
</body>
</html>
"""

bet_history_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Bet History</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">Your Bet History</h1>
        <a href="{{ url_for('dashboard') }}" class="bg-gray-500 hover:bg-gray-700 text-white py-2 px-4 rounded">Back to Dashboard</a>
    </header>
    <main class="container mx-auto mt-8 p-4">
        <table class="min-w-full border">
            <thead>
                <tr class="bg-gray-200">
                    <th class="border px-4 py-2">ID</th>
                    <th class="border px-4 py-2">Amount</th>
                    <th class="border px-4 py-2">Prediction</th>
                    <th class="border px-4 py-2">Result</th>
                    <th class="border px-4 py-2">Date</th>
                </tr>
            </thead>
            <tbody>
                {% for bet in bets %}
                    <tr>
                        <td class="border px-4 py-2">{{ bet.id }}</td>
                        <td class="border px-4 py-2">${{ bet.amount }}</td>
                        <td class="border px-4 py-2">{{ bet.prediction }}</td>
                        <td class="border px-4 py-2">{{ bet.result }}</td>
                        <td class="border px-4 py-2">{{ bet.created_at }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </main>
</body>
</html>
"""

deposit_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Deposit</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">Deposit Money</h1>
        <a href="{{ url_for('dashboard') }}" class="bg-gray-500 hover:bg-gray-700 text-white py-2 px-4 rounded">Back to Dashboard</a>
    </header>
    <main class="container mx-auto mt-8 p-4">
        <form method="POST" class="max-w-md">
            <div class="mb-4">
                <label for="amount" class="block mb-2">Deposit Amount:</label>
                <input type="number" id="amount" name="amount" required class="w-full p-2 border rounded" step="0.01">
            </div>
            <button type="submit" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Deposit</button>
        </form>
    </main>
</body>
</html>
"""

withdraw_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BetPro - Withdraw</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-100">
    <header class="bg-blue-600 text-white p-4">
        <h1 class="text-2xl font-bold">Withdraw Money</h1>
        <a href="{{ url_for('dashboard') }}" class="bg-gray-500 hover:bg-gray-700 text-white py-2 px-4 rounded">Back to Dashboard</a>
    </header>
    <main class="container mx-auto mt-8 p-4">
        <form method="POST" class="max-w-md">
            <div class="mb-4">
                <label for="amount" class="block mb-2">Withdrawal Amount:</label>
                <input type="number" id="amount" name="amount" required class="w-full p-2 border rounded" step="0.01">
            </div>
            <button type="submit" class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">Withdraw</button>
        </form>
    </main>
</body>
</html>
"""

# To render these templates, you'll use Flask's render_template function:
# from flask import render_template

# In your Flask routes, you can do something like this:
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     # Your registration logic here
#     return render_template('register.html')
