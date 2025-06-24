# client.py
import socket
import threading
import time
import sys
import os
import subprocess
import platform
import ctypes
import logging
from datetime import datetime
import json
import requests
import tempfile
from pathlib import Path
import win32gui
import win32con
import win32api
from win10toast import Win10Toast
from packaging import version

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('client.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Константы
DISCOVERY_PORT = 12346
SERVER_PORT = 12345
BUFFER_SIZE = 1024
RECONNECT_DELAY = 5  # Задержка перед повторным подключением
MAX_RECONNECT_ATTEMPTS = 3  # Максимальное количество попыток переподключения

# Константы для обновлений
GITHUB_REPO = "knyazev692/checkaso"  # Замените на ваш репозиторий
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
VERSION = "1.0.0"  # Текущая версия клиента
UPDATE_CHECK_INTERVAL = 3600  # Проверка обновлений каждый час

class NotificationManager:
    def __init__(self):
        self.toaster = Win10Toast()
        
    def show_notification(self, title, message, duration=5):
        """Показывает уведомление в правом нижнем углу экрана"""
        try:
            self.toaster.show_toast(
                title,
                message,
                icon_path=None,  # Можно добавить путь к иконке
                duration=duration,
                threaded=True  # Не блокирует выполнение программы
            )
        except Exception as e:
            logging.error(f"Ошибка при показе уведомления: {e}")

class UpdateManager:
    def __init__(self, notification_manager):
        self.notification_manager = notification_manager
        
    def check_for_updates(self):
        """Проверяет наличие обновлений"""
        try:
            response = requests.get(GITHUB_API_URL)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release['tag_name'].lstrip('v')
                
                if version.parse(latest_version) > version.parse(VERSION):
                    self.notification_manager.show_notification(
                        "Доступно обновление",
                        f"Обновление до версии {latest_version}"
                    )
                    self.download_and_install_update(latest_release['assets'][0]['browser_download_url'])
                    return True
            return False
        except Exception as e:
            logging.error(f"Ошибка при проверке обновлений: {e}")
            return False

    def download_and_install_update(self, download_url):
        """Загружает и устанавливает обновление"""
        try:
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                # Загружаем новую версию
                response = requests.get(download_url, stream=True)
                update_file = os.path.join(temp_dir, "update.exe")
                
                with open(update_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Создаем батник для обновления
                update_script = os.path.join(temp_dir, "update.bat")
                current_exe = sys.executable
                with open(update_script, 'w') as f:
                    f.write(f'''@echo off
timeout /t 2 /nobreak
copy /Y "{update_file}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
''')

                # Запускаем скрипт обновления
                subprocess.Popen(['cmd', '/c', update_script], 
                               creationflags=subprocess.CREATE_NO_WINDOW,
                               cwd=temp_dir)
                
                # Завершаем текущий процесс
                sys.exit(0)

        except Exception as e:
            logging.error(f"Ошибка при установке обновления: {e}")
            self.notification_manager.show_notification(
                "Ошибка обновления",
                "Не удалось установить обновление"
            )

class MicrosipClient:
    def __init__(self):
        self.hostname = self.get_hostname()
        self.server_address = None
        self.main_socket = None
        self.connected = False
        self.running = True
        self.last_dnd_status = None
        self.reconnect_attempts = 0
        self.last_server_response = time.time()
        self.discovery_active = True  # Флаг активности поиска
        self.notification_manager = NotificationManager()
        self.update_manager = UpdateManager(self.notification_manager)
        
        # Запускаем поиск сервера
        self.discovery_thread = threading.Thread(target=self.discover_server, daemon=True)
        self.discovery_thread.start()
        
        # Запускаем поток проверки обновлений
        self.update_thread = threading.Thread(target=self.check_updates_periodically, daemon=True)
        self.update_thread.start()
        
        logging.info(f"Клиент инициализирован (hostname: {self.hostname})")

    def get_hostname(self):
        """Получает имя компьютера"""
        try:
            return socket.gethostname()
        except:
            return f"Unknown-{int(time.time())}"

    def discover_server(self):
        """Поиск сервера администратора через широковещательные сообщения"""
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.bind(('', DISCOVERY_PORT))
        discovery_socket.settimeout(1.0)  # Таймаут для возможности проверки флага
        
        logging.info("Начат поиск сервера администратора...")
        
        while self.running:
            try:
                # Если поиск не активен и есть подключение, пропускаем
                if not self.discovery_active and self.connected:
                    time.sleep(1)
                    continue

                try:
                    data, addr = discovery_socket.recvfrom(BUFFER_SIZE)
                    message = data.decode('utf-8')
                    
                    if message.startswith("ADMIN_SERVER_DISCOVERY:"):
                        server_info = message.split(':')
                        if len(server_info) >= 3:
                            server_ip = server_info[1]
                            server_port = int(server_info[2])
                            
                            # Проверяем, не подключены ли мы уже к этому серверу
                            if self.server_address != (server_ip, server_port):
                                old_server = self.server_address
                                self.server_address = (server_ip, server_port)
                                logging.info(f"Обнаружен сервер администратора: {server_ip}:{server_port}")
                                
                                # Если это новый сервер и мы не подключены, подключаемся
                                if not self.connected:
                                    self.connect_to_server()
                                # Если мы уже подключены к другому серверу, проверяем необходимость переключения
                                elif old_server and old_server != (server_ip, server_port):
                                    logging.info(f"Обнаружен новый сервер администратора, пока подключены к {old_server}")
                except socket.timeout:
                    continue
                    
            except Exception as e:
                logging.error(f"Ошибка при поиске сервера: {str(e)}")
                time.sleep(1)

        try:
            discovery_socket.close()
        except Exception as e:
            logging.error(f"Ошибка при закрытии discovery сокета: {str(e)}")

    def connect_to_server(self):
        """Подключение к серверу администратора"""
        if not self.server_address:
            logging.error("Нет адреса сервера для подключения")
            return False

        # Закрываем старое соединение, если оно существует
        if self.connected:
            self.disconnect_from_server()
        
        try:
            logging.info(f"Попытка подключения к серверу {self.server_address}")
            
            # Создаем новый сокет
            self.main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.main_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            if platform.system() == 'Windows':
                self.main_socket.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 3000))
            
            # Устанавливаем таймаут на подключение
            self.main_socket.settimeout(10)
            
            # Пытаемся подключиться
            self.main_socket.connect(self.server_address)
            
            # Отправляем имя хоста для идентификации
            self.main_socket.sendall(f"{self.hostname}\n".encode('utf-8'))
            
            # Ждем подтверждения от сервера
            try:
                self.main_socket.settimeout(10)  # Таймаут 10 секунд на получение подтверждения
                confirmation = self.main_socket.recv(1024).decode('utf-8').strip()
                if confirmation == "CONNECTION_ACCEPTED":
                    logging.info("Подключение подтверждено сервером")
                    self.connected = True
                    self.reconnect_attempts = 0  # Сбрасываем счетчик попыток
                    self.last_server_response = time.time()
                    self.discovery_active = False  # Отключаем активный поиск
                else:
                    logging.error(f"Неожиданный ответ от сервера: {confirmation}")
                    self.main_socket.close()
                    return False
            except socket.timeout:
                logging.error("Таймаут при ожидании подтверждения от сервера")
                self.main_socket.close()
                return False
            except Exception as e:
                logging.error(f"Ошибка при получении подтверждения от сервера: {str(e)}")
                self.main_socket.close()
                return False
            finally:
                self.main_socket.settimeout(None)
            
            # Запускаем обработчики
            threading.Thread(target=self.handle_commands, daemon=True).start()
            threading.Thread(target=self.maintain_connection, daemon=True).start()
            
            # Даем небольшую паузу для стабилизации соединения
            time.sleep(0.5)
            
            # Отправляем начальный статус DND
            initial_status = self.get_dnd_status()
            self.send_message(f"dnd_status:{initial_status}")
            logging.info(f"Отправлен начальный статус DND: {initial_status}")
            
            # Запускаем мониторинг DND статуса
            self.dnd_monitor_thread = threading.Thread(target=self.monitor_dnd_status, daemon=True)
            self.dnd_monitor_thread.start()
            
            logging.info(f"Успешно подключились к серверу {self.server_address}")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при подключении к серверу: {str(e)}")
            self.disconnect_from_server()
            return False

    def maintain_connection(self):
        """Поддержание активного соединения с сервером"""
        while self.connected and self.running:
            try:
                if not self.main_socket:
                    logging.error("Сокет закрыт при попытке поддержания соединения")
                    break
                
                # Отправляем ping каждые 15 секунд
                logging.debug("Отправляем ping серверу")
                if not self.send_message("ping"):
                    logging.error("Не удалось отправить ping")
                    break
                
                # Проверяем время последнего ответа
                if time.time() - self.last_server_response > 60:  # 1 минута без ответа
                    logging.warning("Нет ответа от сервера более 60 секунд")
                    break
                
                # Ждем 15 секунд
                for _ in range(15):
                    if not self.connected or not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logging.error(f"Ошибка при поддержании соединения: {str(e)}")
                break
        
        logging.info("Завершение поддержания соединения")
        self.disconnect_from_server()

    def disconnect_from_server(self):
        """Корректное отключение от сервера"""
        if self.connected:
            logging.info("Отключение от сервера...")
            self.connected = False
            
            if hasattr(self, 'main_socket') and self.main_socket:
                try:
                    self.main_socket.shutdown(socket.SHUT_RDWR)
                except Exception as e:
                    logging.debug(f"Ошибка при shutdown сокета: {str(e)}")
                try:
                    self.main_socket.close()
                except Exception as e:
                    logging.debug(f"Ошибка при закрытии сокета: {str(e)}")
                self.main_socket = None
            
            # Активируем поиск нового сервера
            self.discovery_active = True
            logging.info("Активирован поиск нового сервера администратора")
            
            # Если клиент все еще работает, пытаемся переподключиться к текущему серверу
            if self.running and self.reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
                self.reconnect_attempts += 1
                logging.info(f"Попытка переподключения {self.reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}")
                time.sleep(RECONNECT_DELAY)
                if self.connect_to_server():
                    logging.info("Успешное переподключение к серверу")
                else:
                    logging.error("Не удалось переподключиться к серверу")
            elif self.reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                logging.warning("Достигнуто максимальное количество попыток переподключения")
                # Сбрасываем счетчик попыток и адрес сервера для поиска нового
                self.reconnect_attempts = 0
                self.server_address = None

    def handle_commands(self):
        """Обработка команд от сервера"""
        buffer = ""
        
        while self.connected and self.running:
            try:
                if not self.main_socket:
                    logging.error("Сокет закрыт или не инициализирован")
                    break
                    
                try:
                    # Устанавливаем таймаут на чтение
                    self.main_socket.settimeout(30.0)
                    data = self.main_socket.recv(BUFFER_SIZE)
                    
                    if not data:
                        logging.warning("Получены пустые данные от сервера - возможно, сервер закрыл соединение")
                        break
                        
                    self.last_server_response = time.time()
                    
                    try:
                        buffer += data.decode('utf-8')
                    except UnicodeDecodeError as e:
                        logging.error(f"Ошибка декодирования данных: {str(e)}")
                        continue
                    
                    while '\n' in buffer:
                        command, buffer = buffer.split('\n', 1)
                        command = command.strip()
                        
                        if command == "check_dnd_status":
                            try:
                                status = self.get_dnd_status()
                                # Всегда отправляем с префиксом dnd_status:
                                if not self.send_message(f"dnd_status:{status}"):
                                    logging.error("Не удалось отправить статус DND")
                            except Exception as e:
                                logging.error(f"Ошибка при проверке статуса DND: {str(e)}")
                        elif command.startswith("display_message:"):
                            try:
                                message = command.split(':', 1)[1]
                                self.display_message(message)
                                if not self.send_message("message_displayed"):
                                    logging.error("Не удалось отправить подтверждение показа сообщения")
                            except Exception as e:
                                logging.error(f"Ошибка при отображении сообщения: {str(e)}")
                                
                except socket.timeout:
                    # Проверяем время последнего ответа
                    if time.time() - self.last_server_response > 60:  # 1 минута без ответа
                        logging.warning("Превышено время ожидания ответа от сервера")
                        break
                    continue
                    
            except ConnectionError as e:
                logging.error(f"Ошибка соединения: {str(e)}")
                break
            except Exception as e:
                logging.error(f"Неожиданная ошибка при обработке команд: {str(e)}")
                break
        
        logging.info("Завершение обработки команд")
        self.disconnect_from_server()

    def send_message(self, message):
        """Отправка сообщения серверу"""
        if not self.connected or not self.main_socket:
            logging.error("Попытка отправки сообщения при отключенном соединении")
            return False
            
        try:
            if not message.endswith('\n'):
                message += '\n'
            
            # Отправляем данные с таймаутом
            self.main_socket.settimeout(5.0)
            try:
                message_bytes = message.encode('utf-8')
                total_sent = 0
                while total_sent < len(message_bytes):
                    sent = self.main_socket.send(message_bytes[total_sent:])
                    if sent == 0:
                        logging.error("Соединение разорвано при отправке")
                        return False
                    total_sent += sent
                return True
            except socket.timeout:
                logging.error("Таймаут при отправке сообщения")
                return False
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {str(e)}")
                return False
            finally:
                self.main_socket.settimeout(None)
                
        except Exception as e:
            logging.error(f"Критическая ошибка при отправке сообщения: {str(e)}")
            self.disconnect_from_server()
            return False

    def get_dnd_status(self):
        """Получение статуса DND из MicroSIP"""
        try:
            # Путь к файлу настроек MicroSIP
            microsip_settings = os.path.join(os.getenv('APPDATA'), 'MicroSIP', 'microsip.ini')
            
            if not os.path.exists(microsip_settings):
                logging.warning("MicroSIP не установлен")
                return "1"  # По умолчанию DND выключен

            # Список кодировок для проверки
            encodings = ['utf-16', 'utf-16le', 'utf-16be', 'utf-8', 'cp1251']
            
            # Сначала определяем BOM
            with open(microsip_settings, 'rb') as f:
                raw = f.read()
                if raw.startswith(b'\xff\xfe'):
                    encodings.insert(0, 'utf-16le')
                elif raw.startswith(b'\xfe\xff'):
                    encodings.insert(0, 'utf-16be')

            # Пробуем разные кодировки
            for encoding in encodings:
                try:
                    with open(microsip_settings, 'r', encoding=encoding) as f:
                        content = f.read()
                        for line in content.splitlines():
                            if line.strip().startswith('DND='):
                                dnd_value = line.strip().split('=')[1]
                                # Проверяем, что значение - это число
                                if dnd_value.isdigit():
                                    return dnd_value  # Возвращаем "0" или "1"
                        logging.warning("Статус DND не найден")
                        return "1"  # По умолчанию DND выключен
                except UnicodeError:
                    continue
                except Exception as e:
                    logging.debug(f"Ошибка при чтении с кодировкой {encoding}: {e}")
                    continue

            # Если не удалось прочитать файл ни с одной кодировкой
            # Пробуем прочитать побайтово
            try:
                with open(microsip_settings, 'rb') as f:
                    content = f.read()
                    dnd_pattern = b'DND='
                    if dnd_pattern in content:
                        pos = content.index(dnd_pattern) + len(dnd_pattern)
                        # Ищем значение после DND=
                        value = chr(content[pos])
                        if value in ['0', '1']:
                            return value
            except Exception as e:
                logging.error(f"Ошибка при побайтовом чтении: {e}")

            logging.warning("Не удалось определить статус DND")
            return "1"  # По умолчанию DND выключен
            
        except Exception as e:
            logging.error(f"Ошибка при получении статуса DND: {e}")
            return "1"  # По умолчанию DND выключен

    def monitor_dnd_status(self):
        """Мониторинг изменений статуса DND"""
        while self.connected and self.running:
            try:
                current_status = self.get_dnd_status()
                if current_status != self.last_dnd_status:
                    self.last_dnd_status = current_status
                    # Всегда отправляем с префиксом dnd_status:
                    if not self.send_message(f"dnd_status:{current_status}"):
                        logging.error("Не удалось отправить обновление статуса DND")
                        # При ошибке отправки сбрасываем last_dnd_status
                        self.last_dnd_status = None
                time.sleep(2)  # Уменьшаем интервал проверки до 2 секунд
            except Exception as e:
                logging.error(f"Ошибка при мониторинге DND: {e}")
                self.last_dnd_status = None  # Сбрасываем статус при ошибке
                time.sleep(2)

    def display_message(self, message):
        """Отображает сообщение в виде уведомления"""
        try:
            self.notification_manager.show_notification(
                "Сообщение от сервера",
                message
            )
            return "message_displayed"
        except Exception as e:
            logging.error(f"Ошибка при отображении сообщения: {e}")
            return "error_displaying_message"

    def check_updates_periodically(self):
        """Периодически проверяет наличие обновлений"""
        while self.running:
            try:
                self.update_manager.check_for_updates()
            except Exception as e:
                logging.error(f"Ошибка при проверке обновлений: {e}")
            time.sleep(UPDATE_CHECK_INTERVAL)

    def run(self):
        """Запуск клиента"""
        try:
            logging.info(f"Клиент запущен (hostname: {self.hostname})")
            
            # Держим главный поток активным
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info("Получен сигнал завершения работы")
        finally:
            self.running = False
            self.disconnect_from_server()
            logging.info("Клиент остановлен")

if __name__ == "__main__":
    client = MicrosipClient()
    client.run() 