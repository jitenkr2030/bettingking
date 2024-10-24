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
# Updated Template (HTML as string literals)
home_html = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BettingKing - Home</title>
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
            background: #1A73E8;
            color: white;
            font-size: 24px;
            text-align: center;
        }

        .bet-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            background-color: white;
            transition: box-shadow 0.3s ease-in-out;
        }

        .bet-card:hover {
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
        }

        .bet-card h4 {
            font-size: 18px;
            font-weight: bold;
        }

        .bet-card .odds {
            font-size: 16px;
            font-weight: bold;
            color: #1A73E8;
        }

        .bet-card .cta {
            background-color: #1A73E8;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 14px;
            transition: background-color 0.3s;
        }

        .bet-card .cta:hover {
            background-color: #0d47a1;
        }

        .top-banner {
            background: url('https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.gulfharbourcountryclub.co.nz%2Fwhat-is-a-social-casino%2F&psig=AOvVaw1ucHLTyWRDrR44SBEsBbno&ust=1729750914789000&source=images&cd=vfe&opi=89978449&ved=0CBQQjRxqFwoTCNi2oJbvo4kDFQAAAAAdAAAAABAK;
            height: 400px;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
            font-size: 3rem;
            text-align: center;
            font-weight: bold;
            background-blend-mode: overlay;
        }
    </style>
</head>

<body class="bg-gray-100">

    <!-- Header -->
    <header class="bg-blue-600 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-3xl font-bold">BettingKing</h1>
            <nav>
                <!-- Mobile-friendly navigation -->
                <ul class="flex space-x-4 hidden md:flex">
                    <!-- Hidden on mobile -->
                    <li><a href="#" class="hover:underline">Home</a></li>
                    <li><a href="#" class="hover:underline">Live Bets</a></li>
                    <li><a href="#" class="hover:underline">Casino</a></li>
                    <li><a href="#" class="hover:underline">Promotions</a></li>
                    <li><a href="#" class="hover:underline">Contact Us</a></li>
                </ul>

                <!-- Mobile menu button -->
                <div class="md:hidden">
                    <button id="mobileMenuBtn" class="text-white">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
                        </svg>
                    </button>
                </div>
            </nav>

            <!-- Mobile dropdown menu -->
            <div id="mobileMenu" class="hidden flex-col space-y-4 bg-blue-700 p-4 md:hidden">
                <a href="#" class="hover:underline">Home</a>
                <a href="#" class="hover:underline">Live Bets</a>
                <a href="#" class="hover:underline">Casino</a>
                <a href="#" class="hover:underline">Promotions</a>
                <a href="#" class="hover:underline">Contact Us</a>
            </div>

            <!-- Login/Register Buttons -->
            <div class="flex space-x-2">
                <a href="{{ url_for('login') }}" class="bg-white text-blue-600 font-bold py-2 px-4 rounded">Login</a>
                <a href="{{ url_for('register') }}" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">Register</a>
            </div>
        </div>
    </header>

    <script>
        // Mobile menu toggle
        document.getElementById('mobileMenuBtn').addEventListener('click', function() {
            const mobileMenu = document.getElementById('mobileMenu');
            mobileMenu.classList.toggle('hidden');
        });
    </script>

    <!-- Top Banner -->
    <div class="top-banner bg-cover bg-center text-white text-center flex items-center justify-center">
        <div class="bg-black bg-opacity-50 p-8 rounded">
            <p class="text-3xl md:text-5xl font-bold">Bet on Your Favorite Sports!</p>
        </div>
    </div>

    <style>
        .top-banner {
            background-image: url('https://www.example.com/banner-image.jpg');
            height: 300px;
            /* Reduced for mobile */
            background-size: cover;
        }

        @media (min-width: 768px) {
            .top-banner {
                height: 400px;
                /* Larger height for tablets and desktops */
            }
        }
    </style>

    <!-- Search Filter Section -->
    <section class="container mx-auto mt-8 p-4">
        <h2 class="text-2xl font-bold mb-4">Search Bets</h2>
        <input id="searchBar" type="text" class="w-full p-2 border border-gray-300 rounded" placeholder="Search for a team or sport...">
    </section>

    <script>
        // Search filter functionality
        const searchBar = document.getElementById('searchBar');
        const betCards = document.querySelectorAll('.bet-card');

        searchBar.addEventListener('input', function() {
            const filterValue = searchBar.value.toLowerCase();
            betCards.forEach(card => {
                const betText = card.textContent.toLowerCase();
                if (betText.includes(filterValue)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    </script>

    <!-- Betting Categories -->
    <section class="container mx-auto mt-8 p-4">
        <h2 class="text-2xl font-bold mb-4">Betting Categories</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bet-card">
                <h4>Soccer: Team A vs Team B</h4>
                <p>Odds: <span class="odds">1.5</span></p>
                <button class="cta">Bet Now</button>
            </div>
            <div class="bet-card">
                <h4>Basketball: Team C vs Team D</h4>
                <p>Odds: <span class="odds">2.0</span></p>
                <button class="cta">Bet Now</button>
            </div>
            <div class="bet-card">
                <h4>Tennis: Player X vs Player Y</h4>
                <p>Odds: <span class="odds">1.8</span></p>
                <button class="cta">Bet Now</button>
            </div>
            <div class="bet-card">
                <h4>Cricket: Team E vs Team F</h4>
                <p>Odds: <span class="odds">1.7</span></p>
                <button class="cta">Bet Now</button>
            </div>
        </div>
    </section>

    <!-- Favorites Section -->
    <section class="container mx-auto mt-8 p-4">
        <h2 class="text-2xl font-bold mb-4">Favorites</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bet-card">
                <h4>Soccer: Team G vs Team H</h4>
                <p>Odds: <span class="odds">2.5</span></p>
                <button class="cta">Bet Now</button>
            </div>
            <!-- More favorite bet cards can be added here -->
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-gray-800 text-white p-4">
        <div class="container mx-auto text-center">
            <p>&copy; 2024 BettingKing. All rights reserved.</p>
        </div>
    </footer>

</body>

</html>
"""





register_html = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BettingKing - Register</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>

<body class="bg-gray-100">
    <!-- Header Section -->
    <header class="bg-blue-600 text-white p-4">
        <div class="container mx-auto">
            <h1 class="text-2xl font-bold">BettingKing</h1>
        </div>
    </header>

    <!-- Main Section -->
    <main class="container mx-auto mt-8 p-4">
        <div class="max-w-lg mx-auto bg-white shadow-md rounded-lg p-6">
            <h2 class="text-3xl font-bold mb-6 text-center">Register</h2>
            
            <!-- Flash Messages -->
            {% with messages = get_flashed_messages() %}
            {% if messages %}
            <div class="mb-4">
                {% for message in messages %}
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                    {{ message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            {% endwith %}
            
            <!-- Registration Form -->
            <form method="POST">
                <div class="mb-4">
                    <label for="username" class="block text-lg font-medium mb-2">Username:</label>
                    <input type="text" id="username" name="username" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring focus:ring-blue-300">
                </div>
                <div class="mb-6">
                    <label for="password" class="block text-lg font-medium mb-2">Password:</label>
                    <input type="password" id="password" name="password" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring focus:ring-blue-300">
                </div>
                <button type="submit" class="w-full bg-green-500 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg transition duration-200">Register</button>
            </form>
            
            <!-- Login Link -->
            <p class="mt-6 text-center">Already have an account? <a href="{{ url_for('login') }}" class="text-blue-500 hover:underline">Login here</a>.</p>
        </div>
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
    <title>BettingKing - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>

<body class="bg-gray-100">
    <!-- Header Section -->
    <header class="bg-blue-600 text-white p-4">
        <div class="container mx-auto">
            <h1 class="text-2xl font-bold">BettingKing</h1>
        </div>
    </header>

    <!-- Main Section -->
    <main class="container mx-auto mt-8 p-4">
        <div class="max-w-lg mx-auto bg-white shadow-md rounded-lg p-6">
            <h2 class="text-3xl font-bold mb-6 text-center">Login</h2>

            <!-- Flash Messages -->
            {% with messages = get_flashed_messages() %}
            {% if messages %}
            <div class="mb-4">
                {% for message in messages %}
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                    {{ message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            {% endwith %}

            <!-- Login Form -->
            <form method="POST">
                <div class="mb-4">
                    <label for="username" class="block text-lg font-medium mb-2">Username:</label>
                    <input type="text" id="username" name="username" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring focus:ring-blue-300">
                </div>
                <div class="mb-6">
                    <label for="password" class="block text-lg font-medium mb-2">Password:</label>
                    <input type="password" id="password" name="password" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring focus:ring-blue-300">
                </div>
                <button type="submit" class="w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition duration-200">Login</button>
            </form>

            <!-- Register Link -->
            <p class="mt-6 text-center">Don't have an account? <a href="{{ url_for('register') }}" class="text-green-500 hover:underline">Register here</a>.</p>
        </div>
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
    <title>BettingKing - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>

<body class="bg-gray-100">
    <!-- Header -->
    <header class="bg-blue-600 text-white p-4 flex justify-between items-center">
        <h1 class="text-2xl font-bold">Welcome, {{ user.username }}</h1>
        <a href="{{ url_for('logout') }}" class="bg-red-500 hover:bg-red-700 text-white py-2 px-4 rounded-lg transition duration-200">Logout</a>
    </header>

    <!-- Main Section -->
    <main class="container mx-auto mt-8 p-4">
        <!-- Balance Section -->
        <div class="bg-white shadow-md rounded-lg p-6 mb-6 text-center">
            <h2 class="text-2xl font-bold mb-4">Your Dashboard</h2>
            <p class="text-lg">Your Balance: <span class="text-green-500 font-bold">${{ user.balance }}</span></p>
            <button class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg mt-4 transition duration-200">
                <a href="{{ url_for('deposit') }}">Deposit</a>
            </button>
            <button class="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg mt-4 transition duration-200">
                <a href="{{ url_for('withdraw') }}">Withdraw</a>
            </button>
        </div>

        <!-- Bet Placement Section -->
        <div class="bg-white shadow-md rounded-lg p-6 mb-6">
            <h3 class="text-2xl font-bold mb-4">Place a Bet</h3>
            <form method="POST" action="{{ url_for('place_bet') }}">
                <div class="mb-4">
                    <label for="amount" class="block text-lg mb-2">Amount:</label>
                    <input type="number" id="amount" name="amount" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring focus:ring-blue-300" step="0.01">
                </div>
                <div class="mb-4">
                    <label for="prediction" class="block text-lg mb-2">Prediction:</label>
                    <input type="text" id="prediction" name="prediction" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring focus:ring-blue-300">
                </div>
                <button type="submit" class="bg-green-500 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition duration-200 w-full">Place Bet</button>
            </form>
        </div>

        <!-- Bet History Section -->
        <div class="bg-white shadow-md rounded-lg p-6 mb-6">
            <h3 class="text-2xl font-bold mb-4">Your Bet History</h3>
            <a href="{{ url_for('bet_history') }}" class="text-blue-500 hover:underline">View Bet History</a>
        </div>

        <!-- Navigation Section (Mobile Friendly) -->
        <div class="fixed bottom-0 inset-x-0 bg-blue-600 text-white flex justify-around py-4">
            <a href="{{ url_for('dashboard') }}" class="text-lg font-bold">Dashboard</a>
            <a href="{{ url_for('deposit') }}" class="text-lg font-bold">Deposit</a>
            <a href="{{ url_for('withdraw') }}" class="text-lg font-bold">Withdraw</a>
            <a href="{{ url_for('bet_history') }}" class="text-lg font-bold">History</a>
        </div>
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
    <title>BettingKing - Bet History</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
</head>

<body class="bg-gray-100">
    <!-- Header -->
    <header class="bg-blue-600 text-white p-4 flex justify-between items-center">
        <h1 class="text-2xl font-bold">Your Bet History</h1>
        <a href="{{ url_for('dashboard') }}" class="bg-gray-500 hover:bg-gray-700 text-white py-2 px-4 rounded-lg transition duration-200">Back to Dashboard</a>
    </header>

    <!-- Main Section -->
    <main class="container mx-auto mt-8 p-4">

        <!-- Filter and Sort Section -->
        <div class="mb-6 flex justify-between items-center">
            <div>
                <label for="filter" class="block mb-2 text-lg font-bold">Filter by Result:</label>
                <select id="filter" class="p-2 border border-gray-300 rounded-md" onchange="filterBets()">
                    <option value="all">All</option>
                    <option value="win">Win</option>
                    <option value="lose">Lose</option>
                    <option value="pending">Pending</option>
                </select>
            </div>
            <div>
                <label for="sort" class="block mb-2 text-lg font-bold">Sort by Date:</label>
                <select id="sort" class="p-2 border border-gray-300 rounded-md" onchange="sortBets()">
                    <option value="newest">Newest First</option>
                    <option value="oldest">Oldest First</option>
                </select>
            </div>
        </div>

        <!-- Bet History Table -->
        <div class="overflow-x-auto">
            <table class="min-w-full border text-center">
                <thead>
                    <tr class="bg-gray-200">
                        <th class="border px-4 py-2">ID</th>
                        <th class="border px-4 py-2">Amount</th>
                        <th class="border px-4 py-2">Prediction</th>
                        <th class="border px-4 py-2">Result</th>
                        <th class="border px-4 py-2">Date</th>
                    </tr>
                </thead>
                <tbody id="betTable">
                    {% for bet in bets %}
                        <tr>
                            <td class="border px-4 py-2">{{ bet.id }}</td>
                            <td class="border px-4 py-2">${{ bet.amount }}</td>
                            <td class="border px-4 py-2">{{ bet.prediction }}</td>
                            <td class="border px-4 py-2">
                                <span class="py-1 px-3 rounded-full {% if bet.result == 'win' %} bg-green-500 text-white {% elif bet.result == 'lose' %} bg-red-500 text-white {% else %} bg-yellow-400 text-white {% endif %}">{{ bet.result }}</span>
                            </td>
                            <td class="border px-4 py-2">{{ bet.created_at }}</td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Pagination (if necessary) -->
        <div class="mt-6 flex justify-between">
            <button class="bg-blue-500 hover:bg-blue-700 text-white py-2 px-4 rounded" onclick="prevPage()">Previous</button>
            <button class="bg-blue-500 hover:bg-blue-700 text-white py-2 px-4 rounded" onclick="nextPage()">Next</button>
        </div>

    </main>

    <script>
        // Sample data (replace with actual data handling logic)
        const bets = {{ bets | tojson }};
        let filteredBets = [...bets];
        let currentPage = 1;
        const itemsPerPage = 10;

        // Function to filter bets by result
        function filterBets() {
            const filterValue = document.getElementById('filter').value;
            filteredBets = bets.filter(bet => filterValue === 'all' || bet.result === filterValue);
            renderTable();
        }

        // Function to sort bets by date
        function sortBets() {
            const sortValue = document.getElementById('sort').value;
            filteredBets.sort((a, b) => {
                if (sortValue === 'newest') {
                    return new Date(b.created_at) - new Date(a.created_at);
                } else {
                    return new Date(a.created_at) - new Date(b.created_at);
                }
            });
            renderTable();
        }

        // Function to render the table
        function renderTable() {
            const tableBody = document.getElementById('betTable');
            tableBody.innerHTML = '';
            const start = (currentPage - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const pageBets = filteredBets.slice(start, end);

            pageBets.forEach(bet => {
                const row = `<tr>
                    <td class="border px-4 py-2">${bet.id}</td>
                    <td class="border px-4 py-2">$${bet.amount}</td>
                    <td class="border px-4 py-2">${bet.prediction}</td>
                    <td class="border px-4 py-2">
                        <span class="py-1 px-3 rounded-full ${bet.result === 'win' ? 'bg-green-500 text-white' : bet.result === 'lose' ? 'bg-red-500 text-white' : 'bg-yellow-400 text-white'}">${bet.result}</span>
                    </td>
                    <td class="border px-4 py-2">${bet.created_at}</td>
                </tr>`;
                tableBody.innerHTML += row;
            });
        }

        // Pagination functions
        function nextPage() {
            if (currentPage * itemsPerPage < filteredBets.length) {
                currentPage++;
                renderTable();
            }
        }

        function prevPage() {
            if (currentPage > 1) {
                currentPage--;
                renderTable();
            }
        }

        // Initial render
        renderTable();
    </script>
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
    <!-- Header Section -->
    <header class="bg-blue-600 text-white p-4 flex justify-between items-center">
        <h1 class="text-2xl font-bold">Deposit Money</h1>
        <a href="{{ url_for('dashboard') }}" class="bg-gray-500 hover:bg-gray-700 text-white py-2 px-4 rounded-lg transition duration-200">Back to Dashboard</a>
    </header>

    <!-- Main Section -->
    <main class="container mx-auto mt-8 p-4">
        <div class="max-w-md mx-auto bg-white p-6 rounded-lg shadow-lg">
            <h2 class="text-xl font-bold mb-4 text-center">Enter Deposit Amount</h2>
            
            <!-- Deposit Form -->
            <form method="POST" class="space-y-6" id="depositForm" onsubmit="return validateDeposit()">
                <!-- Amount Input -->
                <div class="mb-4">
                    <label for="amount" class="block mb-2 text-lg font-bold">Deposit Amount:</label>
                    <input type="number" id="amount" name="amount" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 transition" step="0.01" min="0">
                    <span id="error-message" class="text-red-500 text-sm hidden">Please enter a valid deposit amount.</span>
                </div>
                
                <!-- Deposit Button -->
                <button type="submit" class="w-full bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200">Deposit</button>
            </form>

            <!-- Confirmation Message -->
            <div id="confirmationMessage" class="hidden mt-4 p-4 bg-green-100 text-green-700 text-center rounded-lg">
                Deposit successful! Your account has been credited.
            </div>
        </div>
    </main>

    <!-- JavaScript for validation and confirmation -->
    <script>
        function validateDeposit() {
            const amount = document.getElementById('amount').value;
            const errorMessage = document.getElementById('error-message');
            const confirmationMessage = document.getElementById('confirmationMessage');

            if (amount <= 0) {
                errorMessage.classList.remove('hidden');
                return false;
            } else {
                errorMessage.classList.add('hidden');
                confirmationMessage.classList.remove('hidden');
                return true;
            }
        }
    </script>
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
    <!-- Header Section -->
    <header class="bg-blue-600 text-white p-4 flex justify-between items-center">
        <h1 class="text-2xl font-bold">Withdraw Money</h1>
        <a href="{{ url_for('dashboard') }}" class="bg-gray-500 hover:bg-gray-700 text-white py-2 px-4 rounded-lg transition duration-200">Back to Dashboard</a>
    </header>

    <!-- Main Section -->
    <main class="container mx-auto mt-8 p-4">
        <div class="max-w-md mx-auto bg-white p-6 rounded-lg shadow-lg">
            <h2 class="text-xl font-bold mb-4 text-center">Enter Withdrawal Amount</h2>

            <!-- Display Available Balance -->
            <p class="text-gray-700 text-center mb-4">Your current balance: <strong>${{ user.balance }}</strong></p>
            
            <!-- Withdrawal Form -->
            <form method="POST" class="space-y-6" id="withdrawForm" onsubmit="return validateWithdrawal()">
                <!-- Amount Input -->
                <div class="mb-4">
                    <label for="amount" class="block mb-2 text-lg font-bold">Withdrawal Amount:</label>
                    <input type="number" id="amount" name="amount" required class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 transition" step="0.01" min="0">
                    <span id="error-message" class="text-red-500 text-sm hidden">Please enter a valid withdrawal amount.</span>
                </div>

                <!-- Withdraw Button -->
                <button type="submit" class="w-full bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200">Withdraw</button>
            </form>

            <!-- Confirmation Message -->
            <div id="confirmationMessage" class="hidden mt-4 p-4 bg-green-100 text-green-700 text-center rounded-lg">
                Withdrawal successful! Your account has been debited.
            </div>
        </div>
    </main>

    <!-- JavaScript for validation and balance check -->
    <script>
        function validateWithdrawal() {
            const amount = document.getElementById('amount').value;
            const balance = {{ user.balance }};
            const errorMessage = document.getElementById('error-message');
            const confirmationMessage = document.getElementById('confirmationMessage');

            if (amount <= 0 || amount > balance) {
                errorMessage.textContent = amount <= 0 
                    ? "Please enter a valid withdrawal amount." 
                    : "You cannot withdraw more than your current balance.";
                errorMessage.classList.remove('hidden');
                return false;
            } else {
                errorMessage.classList.add('hidden');
                confirmationMessage.classList.remove('hidden');
                return true;
            }
        }
    </script>

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
