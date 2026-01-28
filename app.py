"""
ASTEROID ALERT SYSTEM - Backend (Python + Flask)
Стартер-код для разработки
"""

# ===== FILE: requirements.txt =====
flask==2.3.0
flask-cors==4.0.0
python-telegram-bot==20.0
requests==2.31.0
psycopg2-binary==2.9.0
sqlalchemy==2.0.0
python-dotenv==1.0.0
stripe==5.4.0
flask-sqlalchemy==3.0.0
gunicorn==21.0.0

# ===== FILE: .env (создай этот файл сам и заполни) =====
# NASA API
NASA_API_KEY=YOUR_NASA_API_KEY_HERE

# Telegram
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE

# Database
DATABASE_URL=postgresql://user:password@localhost/asteroid_db

# Stripe (платежи)
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_PUBLIC_KEY=pk_test_YOUR_KEY_HERE

# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-this

# ===== FILE: app.py =====
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///asteroid.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-this')

db = SQLAlchemy(app)

# ===== DATABASE MODELS =====

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100))
    subscription_tier = db.Column(db.String(20), default='free')  # free, pro, expert, enterprise
    subscription_start = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_end = db.Column(db.DateTime)
    notifications_enabled = db.Column(db.Boolean, default=True)
    notification_time = db.Column(db.String(5), default='09:00')  # HH:MM формат
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    favorites = db.relationship('Asteroid', secondary='user_favorites', backref='favorited_by')
    
    def is_active_subscriber(self, tier_level):
        """Проверяет, имеет ли пользователь активную подписку уровня tier_level"""
        if self.subscription_tier == 'free':
            return False
        if not self.subscription_end:
            return False
        if datetime.utcnow() > self.subscription_end:
            self.subscription_tier = 'free'
            db.session.commit()
            return False
        return True

class Asteroid(db.Model):
    __tablename__ = 'asteroids'
    
    id = db.Column(db.Integer, primary_key=True)
    nasa_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    diameter_km = db.Column(db.Float)  # диаметр в км
    closest_approach_date = db.Column(db.DateTime)  # дата ближайшего сближения
    distance_km = db.Column(db.Float)  # расстояние в км
    distance_au = db.Column(db.Float)  # расстояние в астрономических единицах
    velocity_km_s = db.Column(db.Float)  # скорость в км/сек
    is_potentially_hazardous = db.Column(db.Boolean, default=False)
    spectral_type = db.Column(db.String(50))  # спектральный класс
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nasa_id': self.nasa_id,
            'name': self.name,
            'diameter_km': self.diameter_km,
            'closest_approach_date': self.closest_approach_date.isoformat() if self.closest_approach_date else None,
            'distance_km': self.distance_km,
            'distance_au': self.distance_au,
            'velocity_km_s': self.velocity_km_s,
            'is_potentially_hazardous': self.is_potentially_hazardous,
            'spectral_type': self.spectral_type,
        }

user_favorites = db.Table(
    'user_favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('asteroid_id', db.Integer, db.ForeignKey('asteroids.id'), primary_key=True)
)

class AsteroidAlert(db.Model):
    __tablename__ = 'asteroid_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asteroid_id = db.Column(db.Integer, db.ForeignKey('asteroids.id'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='alerts')
    asteroid = db.relationship('Asteroid', backref='alerts')

# ===== API ENDPOINTS =====

@app.route('/api/health', methods=['GET'])
def health():
    """Проверка, работает ли сервер"""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/asteroids/today', methods=['GET'])
def asteroids_today():
    """Получить астероиды на сегодня"""
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    asteroids = Asteroid.query.filter(
        Asteroid.closest_approach_date >= today,
        Asteroid.closest_approach_date < tomorrow
    ).all()
    
    return jsonify([ast.to_dict() for ast in asteroids])

@app.route('/api/asteroids/week', methods=['GET'])
def asteroids_week():
    """Получить астероиды на неделю"""
    today = datetime.utcnow().date()
    week_later = today + timedelta(days=7)
    
    asteroids = Asteroid.query.filter(
        Asteroid.closest_approach_date >= today,
        Asteroid.closest_approach_date < week_later
    ).order_by(Asteroid.closest_approach_date).all()
    
    return jsonify([ast.to_dict() for ast in asteroids])

@app.route('/api/asteroids/dangerous', methods=['GET'])
def asteroids_dangerous():
    """Получить опасные астероиды (потенциально опасные)"""
    threshold = request.args.get('threshold', 0.05, type=float)  # default 0.05 AU
    
    asteroids = Asteroid.query.filter(
        Asteroid.is_potentially_hazardous == True,
        Asteroid.distance_au <= threshold,
        Asteroid.closest_approach_date >= datetime.utcnow()
    ).order_by(Asteroid.distance_au).all()
    
    return jsonify([ast.to_dict() for ast in asteroids])

@app.route('/api/asteroid/<int:asteroid_id>', methods=['GET'])
def get_asteroid(asteroid_id):
    """Получить детали конкретного астероида"""
    asteroid = Asteroid.query.get_or_404(asteroid_id)
    return jsonify(asteroid.to_dict())

@app.route('/api/search', methods=['GET'])
def search_asteroids():
    """Поиск по названию"""
    query = request.args.get('name', '', type=str)
    
    if not query or len(query) < 2:
        return jsonify({'error': 'Query too short'}), 400
    
    asteroids = Asteroid.query.filter(
        Asteroid.name.ilike(f'%{query}%')
    ).limit(20).all()
    
    return jsonify([ast.to_dict() for ast in asteroids])

@app.route('/api/user/register', methods=['POST'])
def register_user():
    """Регистрация пользователя из Telegram бота"""
    data = request.json
    telegram_id = data.get('telegram_id')
    username = data.get('username')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    # Проверяем, есть ли уже такой пользователь
    user = User.query.filter_by(telegram_id=telegram_id).first()
    
    if user:
        return jsonify({
            'id': user.id,
            'telegram_id': user.telegram_id,
            'subscription_tier': user.subscription_tier
        })
    
    # Создаём нового пользователя
    new_user = User(
        telegram_id=telegram_id,
        username=username,
        subscription_tier='free'
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'id': new_user.id,
        'telegram_id': new_user.telegram_id,
        'subscription_tier': 'free'
    }), 201

@app.route('/api/user/<telegram_id>/subscription', methods=['GET'])
def get_subscription(telegram_id):
    """Получить информацию о подписке пользователя"""
    user = User.query.filter_by(telegram_id=telegram_id).first_or_404()
    
    return jsonify({
        'id': user.id,
        'telegram_id': user.telegram_id,
        'subscription_tier': user.subscription_tier,
        'subscription_end': user.subscription_end.isoformat() if user.subscription_end else None,
        'is_active': user.is_active_subscriber(user.subscription_tier)
    })

@app.route('/api/user/<telegram_id>/upgrade', methods=['POST'])
def upgrade_subscription(telegram_id):
    """Обновить подписку пользователя (после платежа)"""
    data = request.json
    tier = data.get('tier')  # pro, expert, enterprise
    
    if tier not in ['pro', 'expert', 'enterprise']:
        return jsonify({'error': 'Invalid tier'}), 400
    
    user = User.query.filter_by(telegram_id=telegram_id).first_or_404()
    user.subscription_tier = tier
    user.subscription_start = datetime.utcnow()
    
    # Определяем длительность подписки
    if tier == 'pro':
        user.subscription_end = datetime.utcnow() + timedelta(days=30)
    elif tier == 'expert':
        user.subscription_end = datetime.utcnow() + timedelta(days=30)
    elif tier == 'enterprise':
        user.subscription_end = datetime.utcnow() + timedelta(days=365)
    
    db.session.commit()
    
    return jsonify({'success': True, 'subscription_tier': user.subscription_tier})

# ===== NASA API INTEGRATION =====

def fetch_asteroids_from_nasa():
    """Получить данные об астероидах из NASA API"""
    api_key = os.getenv('NASA_API_KEY')
    if not api_key:
        print('WARNING: NASA_API_KEY not set')
        return False
    
    today = datetime.utcnow().date()
    week_later = today + timedelta(days=7)
    
    url = 'https://api.nasa.gov/neo/rest/v1/feed'
    params = {
        'start_date': str(today),
        'end_date': str(week_later),
        'api_key': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Парсим полученные данные
        for date_str, asteroids in data['near_earth_objects'].items():
            for ast_data in asteroids:
                nasa_id = ast_data['id']
                
                # Проверяем, есть ли уже этот астероид
                existing = Asteroid.query.filter_by(nasa_id=nasa_id).first()
                
                # Получаем данные о сближении
                close_approach = ast_data['close_approach_data'][0]
                
                asteroid = existing or Asteroid(nasa_id=nasa_id)
                asteroid.name = ast_data['name']
                asteroid.diameter_km = ast_data['estimated_diameter']['kilometers']['estimated_diameter_max']
                asteroid.closest_approach_date = datetime.fromisoformat(close_approach['close_approach_date'])
                asteroid.distance_km = float(close_approach['miss_distance']['kilometers'])
                asteroid.distance_au = float(close_approach['miss_distance']['astronomical'])
                asteroid.velocity_km_s = float(close_approach['relative_velocity']['kilometers_per_second'])
                asteroid.is_potentially_hazardous = ast_data['is_potentially_hazardous_asteroid']
                asteroid.last_updated = datetime.utcnow()
                
                if not existing:
                    db.session.add(asteroid)
        
        db.session.commit()
        return True
    
    except Exception as e:
        print(f'Error fetching NASA data: {e}')
        return False

# ===== INITIALIZATION =====

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Загружаем астероиды при первом запуске
        fetch_asteroids_from_nasa()
    
    app.run(debug=True, port=5000)
