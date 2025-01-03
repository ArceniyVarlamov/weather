# Прогноз погоды

## Установка и запуск

### 1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш_репозиторий.git
cd weather_service
```

### 2. Установите зависимости:
```bash
pip install -r requirements.txt
```

### 3. Создайте файл .env c API ключами:
API_KEY=ваш_api_ключ

### 4. Запустите приложение:
```bash
python app.py
```

**Или если не запускается:**
```bash
python3 app.py
```

### 4. Откройте браузер и перейдите по адресу:
http://127.0.0.1:5000/ - стандартный адрес

---

## Использование

1. На главной странице введите начальную и конечную точки маршрута.
2. Нажмите "Проверить погоду".
3. Просмотрите результаты:
   - Текущая температура, скорость ветра и вероятность осадков для обеих точек.
   - Анализ погодных условий с рекомендациями.

---

## Ошибки и проверка работоспособности системы

### Обработанные ошибки

1. **Неверно введённые данные**:
   - Если пользователь оставил поля пустыми или ввёл некорректные символы, отображается сообщение об ошибке.
   - Например: "Введите оба города!" или "Введите корректные названия городов".

2. **Город не найден**:
   - Если введённый город отсутствует в базе данных AccuWeather, приложение уведомляет пользователя.
   - Например: "Не удалось найти город: Москва".

3. **Ошибка подключения к API**:
   - Если произошла ошибка подключения к AccuWeather API, приложение выводит сообщение об ошибке и возвращает пользователя на главную страницу.

4. **Отсутствие данных о погоде**:
   - Если API не возвращает данные о погоде (например, в случае технических проблем), приложение уведомляет пользователя.

5. **Обработка тайм-аута**:
   - Если время ожидания ответа от API превышено, пользователь также получает соответствующее сообщение.

---

### Влияние ошибок на систему

Ошибки обрабатываются так, чтобы:
- Приложение не прерывало свою работу.
- Пользователь оставался на странице (главная или результаты).
- Пользователь получал чёткие и понятные инструкции для исправления ошибок.
