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


# Получаем погоду на 12 следующих часов
def get_hourly_forecast(location_key, api_key):
    url = f'http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}'
    params = {
        'apikey': api_key,
        'metric': 'true'  # Используем метрическую систему (градусы Цельсия)
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data  # Возвращаем список прогнозов на ближайшие 12 часов
    except requests.RequestException as e:
        print(f"Ошибка при запросе почасового прогноза: {e}")
        return None


# Создадаём функцию для извлечения вероятности осадков и времени из почасового прогноза
def extract_precipitation_forecast(forecast_data):
    try:
        forecast = []
        for hour in forecast_data:
            time = hour['DateTime']  # Время прогноза
            precipitation_prob = hour.get('PrecipitationProbability', 0)  # Вероятность осадков
            forecast.append((time, precipitation_prob))
        return forecast
    except (KeyError, TypeError) as e:
        print(f"Ошибка при извлечении почасового прогноза: {e}")
        return []





### Серверная часть

@app.route('/weather', methods=['POST'])
def get_weather():
    city_name = request.form.get('city')  # Получаем название города из формы
    if not city_name:
        flash("Введите название города!")
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

    # Получаем почасовой прогноз
    hourly_forecast = get_hourly_forecast(location_key, API_KEY)
    if not hourly_forecast:
        flash(f"Не удалось получить почасовой прогноз для города: {city_name}")
        return redirect(url_for('home'))

    # Извлекаем вероятность осадков
    precipitation_forecast = extract_precipitation_forecast(hourly_forecast)

    # Отображаем результат
    return render_template('weather_result.html',
                           city=city_name,
                           temperature=temperature,
                           wind_speed=wind_speed,
                           weather_text=weather_text,
                           precipitation_forecast=precipitation_forecast)






# Ключ мск - 294021

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
