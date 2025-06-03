from flask import Flask, request, jsonify
import os
import requests
import redis
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 載入 .env
load_dotenv()

app = Flask(__name__)

# Rate limiter
limiter = Limiter(app=app, key_func=get_remote_address)

# 讀取環境變數
API_KEY = os.getenv('API_KEY')
REDIS_URL = os.getenv('REDIS_URL')

# 初始化 Redis
cache = redis.Redis.from_url(REDIS_URL)

# 設定快取過期時間（秒）
CACHE_EXPIRY = 60 * 60 * 12  # 12 小時

@app.route('/weather')
@limiter.limit("10/minute")  # 每分鐘最多 10 次
def get_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'Missing city parameter'}), 400

    cache_key = f"weather:{city.lower()}"

    # 先從快取讀取
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify({'data': eval(cached_data.decode()), 'cached': True})

    # 呼叫 Visual Crossing API
    try:
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}?key={API_KEY}&unitGroup=metric"
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()

        # 儲存到快取
        cache.set(cache_key, str(weather_data), ex=CACHE_EXPIRY)

        return jsonify({'data': weather_data, 'cached': False})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to fetch weather data', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
