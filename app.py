from flask import Flask, render_template, request, flash, redirect, url_for
import os
from dotenv import load_dotenv
import requests

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

API_KEY = os.getenv('API_KEY')

### Функции
# Получаем ключ города (для вызова погоды по нему)
def get_location_key(city_name, api_key):
    url = 'http://dataservice.accuweather.com/locations/v1/cities/search'
    params = {
        'apikey': api_key,
        'q': city_name,
        'language': 'ru-RU'
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]['Key']
        else:
            return None
    except requests.RequestException as e:
        print(f"Ошибка при запросе: {e}")
        return None

# Получаем погоду города по его ключу
def get_current_weather(location_key, api_key):
    url = f'http://dataservice.accuweather.com/currentconditions/v1/{location_key}'
    params = {
        'apikey': api_key,
        'details': 'true'
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0]
        else:
            return None
    except requests.RequestException as e:
        print(f"Ошибка при запросе текущей погоды: {e}")
        return None

# Получаем детальную информацию с погоды (температура, скорость ветра, описание погоды)
def extract_weather_details(data):
    try:
        temperature = data['Temperature']['Metric']['Value']
        wind_speed = data['Wind']['Speed']['Metric']['Value']
        weather_text = data['WeatherText']  # Текстовое описание погоды
        return temperature, wind_speed, weather_text
    except (KeyError, TypeError) as e:
        print(f"Ошибка при извлечении данных о погоде: {e}")
        return None, None, None








### Серверная часть

@app.route('/weather', methods=['POST'])
def get_weather():
    # Получаем с формы название города
    city_name = request.form.get('city')
    if not city_name:
        flash("Введите название города")
        return redirect(url_for('home'))
    
    # Получаем location_key
    location_key = get_location_key(city_name, API_KEY)
    if not location_key:
        flash(f"Не удалось найти город: {city_name}")
        return redirect(url_for('home'))

    # Получаем данные о погоде
    weather_data = get_current_weather(location_key, API_KEY)
    if not weather_data:
        flash(f"Не удалось получить данные о погоде для города: {city_name}")
        return redirect(url_for('home'))

    # Извлекаем ключевые параметры
    temperature, wind_speed, weather_text = extract_weather_details(weather_data)
    if temperature is None or wind_speed is None:
        flash(f"Ошибка при обработке данных о погоде для города: {city_name}")
        return redirect(url_for('home'))

    # Отображаем результат
    return f"Погода в городе {city_name}: {weather_text}, температура {temperature}°C, ветер {wind_speed} км/ч"





# Ключ мск - 294021

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
