from flask import Flask, render_template, request, flash, redirect, url_for
import os
import requests
from dotenv import load_dotenv

from dash import Dash, html, dcc
import plotly.graph_objs as go
import plotly.express as px
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
API_KEY = os.getenv('API_KEY')


def get_location_info(city_name, api_key):
    """
    Запрос к AccuWeather locations/v1/cities/search, 
    чтобы вернуть (location_key, latitude, longitude) для указанного города.
    Возвращает (None, None, None), если город не найден.
    """
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
            loc_key = data[0]['Key']
            lat = data[0]['GeoPosition']['Latitude']
            lon = data[0]['GeoPosition']['Longitude']
            return loc_key, lat, lon
        else:
            return None, None, None
    except requests.RequestException as e:
        print(f"Ошибка при запросе локации: {e}")
        return None, None, None


def get_daily_forecast(location_key, api_key, days=1):
    """
    Запрашиваем суточный (daily) прогноз на 1, 3 или 5 дней.
    Возвращаем список из n элементов (где n = 1,3,5).
    """
    if days not in [1, 3, 5]:
        days = 1
    url = f'http://dataservice.accuweather.com/forecasts/v1/daily/{days}day/{location_key}'
    params = {
        'apikey': api_key,
        'metric': 'true',
        'language': 'ru-ru',
        'details': 'true'  # чтобы получать PrecipitationProbability и др.
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("DailyForecasts", [])
    except requests.RequestException as e:
        print(f"Ошибка при запросе ежедневного прогноза: {e}")
        return []


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/weather', methods=['POST'])
def get_weather():
    # Список городов (некоторые могут быть пустыми, если пользователь не заполнил)
    all_cities = request.form.getlist('cities')
    # Фильтруем пустые поля
    cities = [c.strip() for c in all_cities if c.strip()]

    if not cities:
        flash("Введите хотя бы один город!")
        return redirect(url_for('home'))

    # Количество дней для прогноза
    days = int(request.form.get('days', 1))

    # Здесь сохраним результаты: { 'Город': [список дневных прогнозов], ... }
    forecast_results = {}
    # Сохраняем координаты: { 'Город': (lat, lon), ... }
    coord_results = {}

    for city in cities:
        location_key, lat, lon = get_location_info(city, API_KEY)
        if not location_key:
            flash(f"Не удалось найти город: {city}")
            continue

        forecast_data = get_daily_forecast(location_key, API_KEY, days=days)
        forecast_results[city] = forecast_data
        coord_results[city] = (lat, lon)

    # Сохраняем всё для Dash
    global g_route_data
    g_route_data = {
        'days': days,
        'cities_order': cities,             # порядок ввода (важно для линии маршрута)
        'forecast_data': forecast_results,  # { city: [DailyForecasts] }
        'coords_data': coord_results        # { city: (lat, lon) }
    }

    return render_template('weather_result.html', results=forecast_results, days=days)


# Инициализируем Dash для более гибкой визуализации
dash_app = Dash(__name__, server=app, url_base_pathname='/dash/', external_stylesheets=[dbc.themes.BOOTSTRAP])

dash_app.layout = dbc.Container([
    html.H1("Прогноз погоды для маршрута", style={'marginTop': 20}),

    # Выбор параметра для графика
    html.Div(id='controls-container', children=[
        dcc.Dropdown(
            id='param-dropdown',
            options=[
                {'label': 'Максимальная температура', 'value': 'max_temp'},
                {'label': 'Минимальная температура', 'value': 'min_temp'},
                {'label': 'Вероятность осадков (днём)', 'value': 'day_precip'},
                {'label': 'Вероятность осадков (ночью)', 'value': 'night_precip'}
            ],
            value='max_temp',
            clearable=False
        )
    ], style={'marginBottom': 20}),

    # График прогноза
    dcc.Graph(id='weather-graph', style={'marginTop': 20}),

    html.H2("Карта маршрута", style={'marginTop': 40}),
    # График с картой
    dcc.Graph(id='map-graph', style={'marginTop': 20, 'height': '600px'}),

    html.Div([
        dcc.Link('Вернуться на главную', href='/')
    ], style={'marginTop': 20})
], fluid=True)


@dash_app.callback(
    [Output('weather-graph', 'figure'),
     Output('map-graph', 'figure')],
    [Input('param-dropdown', 'value')]
)
def update_graphs(param):
    global g_route_data
    if 'g_route_data' not in globals() or not g_route_data:
        # Если нет данных, возвращаем пустые фигуры
        return go.Figure(), go.Figure()

    days = g_route_data['days']
    # Порядок городов, в каком пользователь их вводил (важно для рисования линии)
    cities_order = g_route_data['cities_order']
    forecast_dict = g_route_data['forecast_data']  # { city: [list_of_days], ... }
    coords_dict = g_route_data['coords_data']      # { city: (lat, lon) }

    # ========== (1) Линейный график прогноза ==========
    fig_line = go.Figure()

    for city in cities_order:
        daily_list = forecast_dict[city]  # список дневных прогнозов для данного города

        x_labels = []
        y_values = []

        for day_forecast in daily_list:
            date_str = day_forecast.get('Date', '')
            if param == 'max_temp':
                val = day_forecast['Temperature']['Maximum']['Value']
            elif param == 'min_temp':
                val = day_forecast['Temperature']['Minimum']['Value']
            elif param == 'day_precip':
                val = day_forecast['Day'].get('PrecipitationProbability', 0)
            elif param == 'night_precip':
                val = day_forecast['Night'].get('PrecipitationProbability', 0)
            else:
                val = 0

            short_date = date_str.split('T')[0] if 'T' in date_str else date_str
            x_labels.append(short_date)
            y_values.append(val)

        fig_line.add_trace(go.Scatter(
            x=x_labels,
            y=y_values,
            mode='lines+markers',
            name=city
        ))

    param_name = {
        'max_temp': 'Макс. температура (°C)',
        'min_temp': 'Мин. температура (°C)',
        'day_precip': 'Осадки днём (%)',
        'night_precip': 'Осадки ночью (%)'
    }
    fig_line.update_layout(
        title=f"Прогноз на {days} дн.",
        xaxis_title="Дата",
        yaxis_title=param_name.get(param, 'Значение'),
        template='plotly_white'
    )

    # ========== (2) Карта маршрута ==========
    # Соберём массив широт/долгот в том порядке, как ввёл пользователь (это важно для рисования линии)
    lat_list = []
    lon_list = []
    hover_texts = []

    for city in cities_order:
        lat, lon = coords_dict[city]
        lat_list.append(lat)
        lon_list.append(lon)

        # Для более подробной информации во всплывающей подсказке возьмём первый день прогноза (или любой другой)
        if forecast_dict[city]:
            day0 = forecast_dict[city][0]
            max_t = day0['Temperature']['Maximum']['Value']
            min_t = day0['Temperature']['Minimum']['Value']
            day_p = day0['Day'].get('PrecipitationProbability', 0)
            night_p = day0['Night'].get('PrecipitationProbability', 0)
            # Можно вывести ещё описание и т.п.
            txt = (f"{city}\n"
                   f"Макс. темп: {max_t}°C\n"
                   f"Мин. темп: {min_t}°C\n"
                   f"Осадки днём: {day_p}%\n"
                   f"Осадки ночью: {night_p}%")
        else:
            txt = f"{city}\nНет данных о погоде"

        hover_texts.append(txt)

    # 2.1 trace: Линия маршрута (соединяем точки в порядке ввода)
    route_trace = go.Scattermapbox(
        lat=lat_list,
        lon=lon_list,
        mode='lines',  # только линия
        line=dict(width=3, color='blue'),
        name='Маршрут'
    )

    # 2.2 trace: Маркеры городов (с подсказками)
    markers_trace = go.Scattermapbox(
        lat=lat_list,
        lon=lon_list,
        mode='markers+text',
        marker=go.scattermapbox.Marker(size=10, color='red'),
        text=cities_order,          # названия городов на карте
        textposition='top center',  # положение подписи
        hovertext=hover_texts,
        hoverinfo='text',
        name='Города'
    )

    fig_map = go.Figure()
    fig_map.add_trace(route_trace)
    fig_map.add_trace(markers_trace)

    # Настройки карты
    fig_map.update_layout(
        mapbox_style="open-street-map",  # не требует токена
        mapbox_zoom=3,
        mapbox_center={"lat": lat_list[0], "lon": lon_list[0]} if lat_list else {"lat": 55, "lon": 40},
        margin={"r":0, "t":0, "l":0, "b":0}
    )
    fig_map.update_layout(title="Карта маршрута")

    return fig_line, fig_map


if __name__ == '__main__':
    app.run(debug=True)
