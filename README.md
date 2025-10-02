# MicroSIP Manager API

Современная система управления MicroSIP через REST API с поддержкой удаленного управления статусом DND.

## 🌟 Основные возможности

- **REST API архитектура** - современный HTTP API вместо TCP/UDP
- **Удаленное управление DND** - администратор может включать/выключать статус "Не беспокоить" через Windows API
- **Heartbeat система** - клиенты отправляют статус каждые 7 секунд
- **Автоматическое обнаружение статуса MicroSIP** - offline/online/dnd
- **Веб-интерфейс управления** - интерактивные скрипты для администраторов
- **Сонный режим** - клиент активируется только при запуске MicroSIP
- **Мультисерверная поддержка** - автоматическое переключение между серверами

## 📁 Структура проекта

```
├── client/                    # Клиентская часть
│   ├── api_client_stable.py   # Основной клиент с Flask сервером (порт 8084)
│   └── start_stable_client.bat # Запуск клиента
│
├── examples/                  # Примеры использования
│   ├── admin_dnd_control.py   # Панель управления DND клиентов
│   ├── get_client_status.py   # Получение статуса клиента
│   ├── server_control_example.py # Пример управления сервером
│   └── README_DND_CONTROL.md  # Подробная инструкция по управлению DND
│
├── docs/                      # Документация
│   └── API_REFERENCE.md       # Полная документация API
│
├── scripts/                   # Утилиты
│   ├── setup_token.py         # Настройка GitHub токена
│   └── migrate_to_api.py      # Миграция на новый API
│
├── api_config.py              # Общая конфигурация
├── requirements.txt           # Python зависимости
└── pyproject.toml            # Конфигурация проекта
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск клиента

```bash
# Запуск клиента (автоматически поднимает Flask сервер на порту 8084)
python client/api_client_stable.py

# Или через batch файл
client/start_stable_client.bat
```

## 🎛️ Управление DND статусом

### Через интерактивный скрипт:
```bash
python examples/admin_dnd_control.py
```

### Через curl:
```bash
# Выключить DND
curl -X POST "http://server:8083/api/clients/HOSTNAME/set_dnd?enabled=false"

# Включить DND
curl -X POST "http://server:8083/api/clients/HOSTNAME/set_dnd?enabled=true"
```

### Через Python:
```python
import requests

# Получить статус клиента
response = requests.get("http://server:8083/api/clients/HOSTNAME/status")
status = response.json()

# Управлять DND
requests.post("http://server:8083/api/clients/HOSTNAME/set_dnd", 
              params={"enabled": False})
```

## 📊 API Эндпоинты

### Основные серверные API (порт 8083):
- `GET /api/clients` - список всех клиентов
- `GET /api/clients/{hostname}/status` - получить статус клиента (опрос в реальном времени)
- `POST /api/clients/{hostname}/set_dnd` - управление DND статусом
- `POST /api/heartbeat` - приём heartbeat от клиентов
- `GET /api/calls` - получить все звонки
- `GET /api/stats` - статистика системы

### Клиентские API (порт 8084):
- `GET /health` - проверка живости
- `GET /api/status` - детальный статус клиента
- `POST /api/set_dnd` - управление DND через Windows API
- `POST /api/get_setting` - получение настроек MicroSIP
- `POST /api/display_message` - показать уведомление пользователю

Полная документация: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

## ⚙️ Конфигурация

### Основные настройки в `api_config.py`:
```python
# API серверы (можно настроить через переменные окружения)
API_SERVERS = [
    "http://172.16.99.12:8083",  # Основной сервер
    "http://172.16.99.31:8083",  # Резервный сервер 1
    "http://172.16.99.112:8083",  # Резервный сервер 2
]

# Настройки клиента
HEARTBEAT_INTERVAL = 7  # Heartbeat каждые 7 секунд
API_TIMEOUT = 10
```

### Переменные окружения:
- `API_SERVER_1` - основной сервер
- `HEARTBEAT_INTERVAL` - интервал heartbeat
- `LOG_LEVEL` - уровень логирования

## 🔒 Безопасность

- Порт 8084 должен быть доступен только для API сервера
- Используйте firewall для ограничения доступа
- GitHub токены не попадают в репозиторий
- Логи могут содержать чувствительную информацию

## 📋 Требования

- **Python 3.8+**
- **Windows 10/11** (для Windows API)
- **MicroSIP** установлен и настроен
- **Сетевые порты:**
  - 8083 - FastAPI сервер
  - 8084 - Flask клиент (должен быть доступен серверу)

## 🎯 Статусы клиентов

| Статус | Эмодзи | Описание |
|--------|--------|----------|
| `offline` | ⚫ | MicroSIP не запущен |
| `online` | 🟢 | MicroSIP запущен, доступен |
| `dnd` | 🔴 | MicroSIP запущен, DND включен |

## 🔄 Heartbeat система

Клиенты автоматически отправляют heartbeat каждые **7 секунд**:

```json
POST http://server:8083/api/heartbeat
{
  "hostname": "NIKITA",
  "extension": "485", 
  "status": 0
}
```

Где `status`: 0 = доступен, 1 = DND

## 🛠️ Разработка

### Структура кода:
- `client/api_client_stable.py` - основной клиент с Flask сервером
- `server/api_server.py` - FastAPI сервер с SQLite БД
- `examples/` - готовые скрипты для администраторов

### Добавление новых функций:
1. Добавить эндпоинт в `server/api_server.py`
2. Обновить клиент в `client/api_client_stable.py`
3. Создать пример в `examples/`
4. Обновить документацию в `docs/API_REFERENCE.md`

## 📚 Документация

- [API_REFERENCE.md](docs/API_REFERENCE.md) - Полная документация API
- [README_DND_CONTROL.md](examples/README_DND_CONTROL.md) - Управление DND клиентов
- Встроенная справка в скриптах: `python examples/admin_dnd_control.py --help`

## 🚀 Примеры использования

### Массовое управление DND (обеденный перерыв):
```python
import requests

server = "http://172.16.99.123:8083"
clients = requests.get(f"{server}/api/clients").json()

# Включить DND для всех
for client in clients:
    requests.post(f"{server}/api/clients/{client['hostname']}/set_dnd", 
                  params={"enabled": True})
```

### Мониторинг статуса:
```bash
# Непрерывный мониторинг клиента каждые 10 секунд
python examples/get_client_status.py NIKITA monitor 10
```

## 📝 Лицензия

Этот проект предназначен для внутреннего использования в корпоративной среде.

---

**Готово к продакшену!** 🎉

Для быстрого старта запустите:
1. `python server/api_server.py` (сервер)
2. `python client/api_client_stable.py` (клиент) 
3. `python examples/admin_dnd_control.py` (управление)
