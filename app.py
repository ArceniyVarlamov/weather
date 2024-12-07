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


# Логика проверки на плохую погоду
def check_bad_weather(temperature, wind_speed, precip_prob):
    if temperature > 35:
        if wind_speed > 20:
            if precip_prob > 70:
                return "Очень жаркая погода с сильным ветром и высокой вероятностью осадков."
            else:
                return "Очень жаркая погода с сильным ветром."
        elif precip_prob > 70:
            return "Очень жаркая погода с высокой вероятностью осадков."
        else:
            return "Очень жаркая и сухая погода."

    elif temperature > 25:
        if wind_speed > 20:
            return "Тёплая погода с сильным ветром."
        elif precip_prob > 70:
            return "Тёплая погода с высокой вероятностью осадков."
        else:
            return "Тёплая и хорошая погода."

    elif temperature > 15:
        if wind_speed > 20 or precip_prob > 70:
            return "Прохладная погода с ветром или осадками."
        else:
            return "Прохладная и спокойная погода."

    elif temperature > 0:
        if wind_speed > 20:
            return "Холодная погода с ветром."
        elif precip_prob > 70:
            return "Холодная погода с осадками."
        else:
            return "Холодная и сухая погода."

    else:
        return "Морозная погода. Одевайтесь теплее!"



### Серверная часть

@app.route('/weather', methods=['POST'])
def get_weather():
    start_city = request.form.get('start')
    end_city = request.form.get('end')

    if not start_city or not end_city:
        flash("Введите оба города!")
        return redirect(url_for('home'))

    # Получаем location_key для начальной точки
    start_location_key = get_location_key(start_city, API_KEY)
    if not start_location_key:
        flash(f"Не удалось найти город: {start_city}")
        return redirect(url_for('home'))

    # Получаем location_key для конечной точки
    end_location_key = get_location_key(end_city, API_KEY)
    if not end_location_key:
        flash(f"Не удалось найти город: {end_city}")
        return redirect(url_for('home'))

    # Получаем погоду для начальной точки
    start_weather = get_current_weather(start_location_key, API_KEY)
    if not start_weather:
        flash(f"Не удалось получить погоду для города: {start_city}")
        return redirect(url_for('home'))
    start_temp, start_wind, _ = extract_weather_details(start_weather)

    # Получаем прогноз осадков для начальной точки
    start_forecast = get_hourly_forecast(start_location_key, API_KEY)
    start_precip_prob = extract_precipitation_forecast(start_forecast)[0][1]

    # Анализ начальной точки
    start_status = check_bad_weather(start_temp, start_wind, start_precip_prob)

    # Получаем погоду для конечной точки
    end_weather = get_current_weather(end_location_key, API_KEY)
    if not end_weather:
        flash(f"Не удалось получить погоду для города: {end_city}")
        return redirect(url_for('home'))
    end_temp, end_wind, _ = extract_weather_details(end_weather)

    # Получаем прогноз осадков для конечной точки
    end_forecast = get_hourly_forecast(end_location_key, API_KEY)
    end_precip_prob = extract_precipitation_forecast(end_forecast)[0][1]

    # Анализ конечной точки
    end_status = check_bad_weather(end_temp, end_wind, end_precip_prob)

    return render_template('weather_result.html',
                           start_city=start_city,
                           start_temp=start_temp,
                           start_wind=start_wind,
                           start_precip=start_precip_prob,
                           start_status=start_status,
                           end_city=end_city,
                           end_temp=end_temp,
                           end_wind=end_wind,
                           end_precip=end_precip_prob,
                           end_status=end_status)

# Ключ мск - 294021

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
