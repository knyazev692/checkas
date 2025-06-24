# admin.py
import socket
import threading
import time
import flet as ft
import asyncio
import os
import sys
import platform

DISCOVERY_PORT = 12346
DISCOVERY_MESSAGE = "ADMIN_SERVER_DISCOVERY"
WEB_PORT = 8082

def is_port_available(port):
    """Проверяет, доступен ли порт"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False

class AdminServer:
    def __init__(self, host, port):
        self.host = self.get_local_ip()
        self.port = port
        self.clients = {}
        self.client_info = {}
        self.clients_view = None

        # Находим свободный порт для веб-интерфейса
        self.web_port = WEB_PORT
        while not is_port_available(self.web_port):
            self.web_port += 1

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(5)

        print("\n=== Сервер администратора запущен ===")
        print(f"IP адрес сервера: {self.host}")
        print(f"Порт сервера: {self.port}")
        print(f"Порт веб-интерфейса: {self.web_port}")
        print("\n=== Инструкция по доступу к веб-интерфейсу ===")
        print("1. С этого компьютера:")
        print(f"   http://localhost:{self.web_port}")
        print("   или")
        print(f"   http://{self.host}:{self.web_port}")
        print("\n2. С других компьютеров в локальной сети:")
        print(f"   http://{self.host}:{self.web_port}")
        print("\nВажно: компьютеры должны быть в одной локальной сети")
        print("=======================================\n")

        # UDP сокет для широковещательной рассылки
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_thread = threading.Thread(target=self.broadcast_presence, daemon=True)
        self.discovery_thread.start()

        # Запускаем сервер в отдельном потоке
        threading.Thread(target=self.accept_connections, daemon=True).start()

        # Настраиваем event loop для Windows
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        try:
            # Запускаем Flet приложение
            ft.app(
                target=self.main,
                view=None,  # Используем встроенный рендерер
                port=self.web_port,
                host="0.0.0.0",
                route_url_strategy="hash",
                assets_dir=os.path.join(os.path.dirname(__file__), "assets") if not getattr(sys, 'frozen', False) else os.path.join(sys._MEIPASS, "assets")
            )
        except Exception as e:
            print(f"Ошибка при запуске веб-интерфейса: {e}")
            print(f"Тип ошибки: {type(e)}")
            import traceback
            print(f"Подробности:\n{traceback.format_exc()}")

    def main(self, page: ft.Page):
        try:
            # Быстрая инициализация основных настроек
            self.page = page
            page.title = "Панель администратора MicroSIP"
            page.window_width = 1200
            page.window_height = 800
            page.padding = 20
            page.theme_mode = ft.ThemeMode.DARK
            page.theme = ft.Theme(
                color_scheme_seed=ft.Colors.BLUE,
                visual_density=ft.VisualDensity.COMFORTABLE,
            )
            
            # Настройка страницы
            page.spacing = 20
            page.scroll = ft.ScrollMode.AUTO
            page.vertical_alignment = ft.MainAxisAlignment.START
            page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            
            # Настройка адаптивности для мобильных устройств
            page.on_resize = self.handle_resize
            
            # Показываем индикатор загрузки
            progress = ft.ProgressBar(width=400, color=ft.Colors.BLUE)
            page.add(progress)
            page.update()
            
            # Создаем все компоненты интерфейса
            components = self.create_all_components()
            
            # Удаляем индикатор загрузки и добавляем компоненты
            page.controls.clear()
            page.add(components)
            
            # Загружаем существующие подключения
            self.load_existing_connections()
            
            # Применяем начальные настройки размера
            self.handle_resize(page)
            
            # Добавляем обработчик обновления для синхронизации состояния
            def page_update(e):
                self.load_existing_connections()
            page.on_view_pop = page_update
            
            # Настраиваем автоматическое обновление списка клиентов
            def update_clients():
                while True:
                    time.sleep(5)  # Обновляем каждые 5 секунд
                    if hasattr(self, 'page'):
                        self.load_existing_connections()
            
            # Запускаем поток обновления клиентов
            threading.Thread(target=update_clients, daemon=True).start()
            
            page.update()
            
        except Exception as e:
            print(f"Ошибка при инициализации страницы: {e}")
            if hasattr(self, 'page'):
                self.page.add(
                    ft.Text(
                        f"Ошибка загрузки: {str(e)}",
                        color=ft.Colors.RED_400,
                        size=20,
                        weight=ft.FontWeight.BOLD
                    )
                )
                self.page.update()

    def create_all_components(self):
        # Переключатель темы
        theme_switch = ft.IconButton(
            icon=ft.Icons.DARK_MODE,
            selected_icon=ft.Icons.LIGHT_MODE,
            on_click=self.toggle_theme,
            tooltip="Переключить тему",
            style=ft.ButtonStyle(
                color={"": ft.Colors.BLUE_200, "selected": ft.Colors.YELLOW_200},
            ),
        )

        # Создаем заголовок с переключателем темы
        header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Панель администратора MicroSIP", 
                           size=30, 
                           weight=ft.FontWeight.BOLD,
                           color=ft.Colors.BLUE_200),
                    theme_switch
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"Сервер: {self.host}:{self.port}",
                       size=16,
                       color=ft.Colors.GREY_400)
            ]),
            padding=10,
            margin=ft.margin.only(bottom=20)
        )

        # Создаем основные элементы интерфейса
        self.clients_view = ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            height=400,
            expand=True,  # Добавляем expand для лучшего отображения
        )

        # Добавляем поиск по клиентам
        self.search_field = ft.TextField(
            label="Поиск клиентов",
            width=300,
            prefix_icon=ft.Icons.SEARCH,
            on_change=self.filter_clients,
            border_radius=10,
            filled=True,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            label_style=ft.TextStyle(color=ft.Colors.BLUE_200),
            bgcolor=ft.Colors.BLACK12,
        )

        # Кнопки управления выбором
        select_buttons = ft.Row([
            ft.ElevatedButton(
                text="Выбрать все",
                on_click=self.select_all_clients,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_700,
                ),
            ),
            ft.ElevatedButton(
                text="Снять выбор",
                on_click=self.deselect_all_clients,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE_700,
                ),
            ),
        ], spacing=10)

        # Контейнер для клиентов с заголовком и поиском
        clients_container = ft.Container(
            content=ft.Column([
                ft.Text("Подключенные клиенты:", 
                       size=20, 
                       weight=ft.FontWeight.BOLD,
                       color=ft.Colors.BLUE_200),
                ft.Row([
                    self.search_field,
                    select_buttons,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.clients_view
            ], expand=True),  # Добавляем expand для колонки
            padding=20,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_400),
            expand=True  # Добавляем expand для контейнера
        )

        self.message_input = ft.TextField(
            label="Сообщение для отправки",
            width=600,
            multiline=True,
            min_lines=2,
            max_lines=5,
            border_radius=10,
            filled=True,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            label_style=ft.TextStyle(color=ft.Colors.BLUE_200),
            bgcolor=ft.Colors.BLACK12,
        )

        send_button = ft.ElevatedButton(
            text="Отправить выбранным",
            on_click=self.send_message_to_selected,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_700,
                padding=20,
            )
        )

        message_container = ft.Container(
            content=ft.Column([
                ft.Text("Отправка сообщений:", 
                       size=20, 
                       weight=ft.FontWeight.BOLD,
                       color=ft.Colors.BLUE_200),
                ft.Row([
                    self.message_input,
                    send_button
                ])
            ]),
            padding=20,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_400)
        )

        self.log_view = ft.TextField(
            label="Лог событий",
            width=800,
            height=200,
            multiline=True,
            read_only=True,
            border_radius=10,
            filled=True,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            label_style=ft.TextStyle(color=ft.Colors.BLUE_200),
            bgcolor=ft.Colors.BLACK12,
        )

        log_container = ft.Container(
            content=ft.Column([
                ft.Text("Журнал событий:", 
                       size=20, 
                       weight=ft.FontWeight.BOLD,
                       color=ft.Colors.BLUE_200),
                self.log_view
            ]),
            padding=20,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10,
            border=ft.border.all(1, ft.Colors.BLUE_400)
        )

        # Создаем основной контейнер для всего содержимого
        return ft.Container(
            content=ft.Column([
                header,
                clients_container,
                message_container,
                log_container
            ], scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

    def toggle_theme(self, e):
        """Переключает тему между светлой и темной"""
        e.control.selected = not e.control.selected
        self.page.theme_mode = (
            ft.ThemeMode.LIGHT if self.page.theme_mode == ft.ThemeMode.DARK 
            else ft.ThemeMode.DARK
        )
        self.page.update()

    def create_client_row(self, hostname):
        """Создает строку клиента для интерфейса"""
        # Создаем чекбокс для выбора клиента
        checkbox = ft.Checkbox(
            value=False,
            scale=1.2,
            fill_color=ft.Colors.BLUE_400,
            data=hostname
        )

        # Создаем кнопку для клиента
        client_button = ft.ElevatedButton(
            text=hostname,
            width=200,
            bgcolor=ft.Colors.BLUE_GREY_700,
            color=ft.Colors.WHITE,
            data=hostname,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=15,
            )
        )

        # Создаем кнопку проверки DND
        check_dnd_button = ft.ElevatedButton(
            text="Проверить DND",
            on_click=lambda e, h=hostname: self.check_dnd_status(h),
            bgcolor=ft.Colors.BLUE_500,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=15,
            )
        )

        # Создаем контейнер с элементами управления
        controls = ft.Row(
            controls=[
                checkbox,
                client_button,
                check_dnd_button
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        # Создаем строку с клиентом в контейнере
        client_row = ft.Container(
            content=controls,
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.BLACK12,
            border=ft.border.all(1, ft.Colors.BLUE_400)
        )

        # Сохраняем элементы в информации о клиенте
        if hostname in self.client_info:
            self.client_info[hostname].update({
                'button': client_button,
                'row': client_row,
                'checkbox': checkbox
            })

        return client_row

    def filter_clients(self, e):
        """Фильтрация клиентов по поисковому запросу"""
        try:
            search_text = self.search_field.value.lower()
            for hostname in self.client_info:
                if hostname in self.client_info and 'row' in self.client_info[hostname]:
                    row = self.client_info[hostname]['row']
                    row.visible = search_text in hostname.lower()
            self.page.update()
        except Exception as e:
            self.log_message(f"Ошибка при фильтрации клиентов: {str(e)}")

    def select_all_clients(self, e):
        """Выбрать всех видимых клиентов"""
        try:
            for hostname in self.client_info:
                if hostname in self.client_info and 'checkbox' in self.client_info[hostname]:
                    checkbox = self.client_info[hostname]['checkbox']
                    row = self.client_info[hostname]['row']
                    if row.visible:
                        checkbox.value = True
            self.page.update()
        except Exception as e:
            self.log_message(f"Ошибка при выборе всех клиентов: {str(e)}")

    def deselect_all_clients(self, e):
        """Снять выбор со всех клиентов"""
        try:
            for hostname in self.client_info:
                if hostname in self.client_info and 'checkbox' in self.client_info[hostname]:
                    self.client_info[hostname]['checkbox'].value = False
            self.page.update()
        except Exception as e:
            self.log_message(f"Ошибка при снятии выбора с клиентов: {str(e)}")

    def send_message_to_selected(self, e):
        """Отправка сообщения выбранным клиентам"""
        message = self.message_input.value.strip()
        if not message:
            self.log_message("Пожалуйста, введите сообщение для отправки.")
            return
        
        selected_clients = []
        for hostname in self.client_info:
            if (hostname in self.client_info and 
                'checkbox' in self.client_info[hostname] and 
                self.client_info[hostname]['checkbox'].value):
                selected_clients.append(hostname)
        
        if not selected_clients:
            self.log_message("Пожалуйста, выберите клиентов для отправки сообщения.")
            return
            
        success_count = 0
        for hostname in selected_clients:
            if self.send_message_to_client(hostname, message):
                success_count += 1

        self.message_input.value = ""
        self.page.update()
        
        if success_count > 0:
            self.log_message(f"Сообщение успешно отправлено {success_count} из {len(selected_clients)} клиентам.")
        else:
            self.log_message("Не удалось отправить сообщение ни одному клиенту.")

    def send_message_to_client(self, hostname, message=None):
        """Отправка сообщения конкретному клиенту"""
        if not message:
            message = self.message_input.value.strip()
            if not message:
                self.log_message("Пожалуйста, введите сообщение для отправки.")
                return False

        try:
            result = self._send_command_async(hostname, "display_message", self._handle_message_response, message)
            if result:
                self.log_message(f"Сообщение отправлено клиенту {hostname}")
                return True
            else:
                self.log_message(f"Не удалось отправить сообщение клиенту {hostname}")
                return False
        except Exception as e:
            self.log_message(f"Ошибка при отправке сообщения клиенту {hostname}: {str(e)}")
            return False

    def _handle_message_response(self, hostname, response):
        self.log_message(f"Ответ на сообщение от {hostname}: {response}")

    def _send_command_async(self, hostname, command, callback, message_data=None):
        if hostname not in self.client_info:
            self.log_message(f"Клиент {hostname} не найден.")
            return False
        
        max_retries = 3
        retry_delay = 1  # секунды
        
        for attempt in range(max_retries):
            try:
                if hostname not in self.client_info:
                    self.log_message(f"Клиент {hostname} был отключен во время выполнения команды.")
                    return False

                main_socket = self.client_info[hostname]['main_socket']
                if not main_socket:
                    raise ConnectionError("Сокет не инициализирован")

                # Формируем команду
                full_command = command
                if message_data:
                    full_command = f"{command}:{message_data}"
                if not full_command.endswith('\n'):
                    full_command += '\n'
                
                # Проверяем состояние сокета
                try:
                    main_socket.getpeername()
                except Exception:
                    raise ConnectionError("Сокет не подключен")

                # Отправляем команду
                message_bytes = full_command.encode('utf-8')
                main_socket.settimeout(5.0)
                
                try:
                    total_sent = 0
                    while total_sent < len(message_bytes):
                        try:
                            sent = main_socket.send(message_bytes[total_sent:])
                            if sent == 0:
                                raise ConnectionError("Сокет закрыт при отправке")
                            total_sent += sent
                        except BlockingIOError:
                            time.sleep(0.1)
                            continue
                        except socket.error as e:
                            if e.errno == 10035:  # WSAEWOULDBLOCK
                                time.sleep(0.1)
                                continue
                            raise

                    return True
                    
                finally:
                    main_socket.settimeout(None)
                    
            except (ConnectionError, socket.error) as e:
                self.log_message(f"Ошибка соединения с {hostname} (попытка {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.log_message(f"Не удалось выполнить команду '{command}' для {hostname} после {max_retries} попыток")
                    return False
            except Exception as e:
                self.log_message(f"Неожиданная ошибка при работе с {hostname}: {str(e)}")
                return False
        return False

    def log_message(self, message):
        print(message)  # Добавляем вывод в консоль для отладки
        if hasattr(self, 'page'):
            self.update_log(message)

    def update_log(self, message):
        try:
            self.log_view.value = f"{message}\n{self.log_view.value if self.log_view.value else ''}"
            self.page.update()
        except Exception as e:
            print(f"Ошибка при обновлении лога: {e}")

    def accept_connections(self):
        while True:
            try:
                main_socket, client_address = self.server_socket.accept()
                main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                main_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                
                ip_address = client_address[0]
                print(f"Новое соединение от {ip_address}:{client_address[1]}")
                
                def handle_new_connection():
                    try:
                        # Увеличиваем таймаут до 10 секунд для получения имени хоста
                        main_socket.settimeout(10.0)
                        print(f"Ожидание имени хоста от {ip_address}...")
                        
                        # Читаем данные до символа новой строки
                        data = ""
                        while '\n' not in data:
                            try:
                                chunk = main_socket.recv(1024).decode('utf-8')
                                print(f"Получены данные от {ip_address}: {chunk!r}")
                                if not chunk:
                                    print(f"Соединение с {ip_address} закрыто клиентом")
                                    return
                                data += chunk
                            except socket.timeout:
                                print(f"Таймаут при ожидании данных от {ip_address}")
                                return
                            except Exception as e:
                                print(f"Ошибка при чтении данных от {ip_address}: {str(e)}")
                                return
                        
                        # Обрабатываем первую строку как имя хоста
                        hostname = data.split('\n')[0].strip()
                        if not hostname:
                            print(f"Не удалось получить имя хоста от {ip_address} (пустая строка)")
                            return
                            
                        print(f"Клиент {ip_address} успешно представился как: {hostname}")

                        # Если клиент с таким именем уже существует
                        if hostname in self.clients:
                            print(f"Клиент с именем '{hostname}' уже подключен. Закрываем старое соединение.")
                            try:
                                old_socket = self.clients[hostname]
                                old_socket.close()
                                self.remove_client(hostname)
                            except Exception as e:
                                print(f"Ошибка при закрытии старого соединения для {hostname}: {str(e)}")

                        # Регистрируем клиента
                        self.clients[hostname] = main_socket
                        self.client_info[hostname] = {
                            'ip': ip_address,
                            'main_socket': main_socket,
                            'connected_time': time.time(),
                            'last_activity': time.time()
                        }

                        # Создаем и добавляем новый клиент в интерфейс
                        if hasattr(self, 'page'):
                            self.add_client_to_ui(hostname)

                        # Запускаем поток обработки клиента
                        client_handler_thread = threading.Thread(
                            target=self.handle_client,
                            args=(main_socket, hostname),
                            daemon=True
                        )
                        self.client_info[hostname]['thread'] = client_handler_thread
                        client_handler_thread.start()

                    except Exception as e:
                        print(f"Ошибка при обработке нового подключения: {str(e)}")
                        try:
                            main_socket.close()
                        except Exception:
                            pass

                # Запускаем обработку подключения в отдельном потоке
                threading.Thread(target=handle_new_connection, daemon=True).start()

            except Exception as e:
                print(f"Ошибка при приеме соединений: {str(e)}")
                time.sleep(1)  # Добавляем задержку перед следующей попыткой

    def handle_client(self, main_socket, hostname):
        """Обработка клиента"""
        try:
            # Настраиваем сокет
            main_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            main_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            buffer = ""
            
            while True:
                try:
                    main_socket.settimeout(30.0)  # Таймаут 30 секунд
                    chunk = main_socket.recv(1024)
                    if not chunk:
                        print(f"Соединение с {hostname} закрыто клиентом")
                        break

                    main_socket.settimeout(None)
                    if hostname in self.client_info:
                        self.client_info[hostname]['last_activity'] = time.time()
                    
                    # Обрабатываем полученные данные
                    try:
                        buffer += chunk.decode('utf-8')
                    except UnicodeDecodeError as e:
                        print(f"Ошибка декодирования данных от {hostname}: {str(e)}")
                        continue
                    
                    # Обрабатываем сообщения в буфере
                    while '\n' in buffer:
                        message, buffer = buffer.split('\n', 1)
                        message = message.strip()
                        
                        if message.startswith("dnd_status:"):
                            try:
                                dnd_status = message.split(':', 1)[1]
                                if hostname in self.client_info:
                                    self.handle_dnd_response(hostname, dnd_status)
                            except Exception as e:
                                print(f"Ошибка обработки статуса DND от {hostname}: {str(e)}")
                        elif message == "message_displayed":
                            print(f"Сообщение показано клиенту {hostname}")
                        else:
                            print(f"Ответ от {hostname}: {message}")
                    
                except socket.timeout:
                    # При таймауте проверяем статус DND
                    if hostname in self.clients:
                        self.check_dnd_status(hostname)
                    continue
                except Exception as e:
                    print(f"Ошибка при обработке данных от {hostname}: {str(e)}")
                    break

        except Exception as e:
            print(f"Критическая ошибка при обработке клиента {hostname}: {str(e)}")
        finally:
            # Очищаем ресурсы
            try:
                main_socket.close()
            except Exception:
                pass
            
            self.remove_client(hostname)

    def add_client_to_ui(self, hostname):
        """Добавляет клиента в интерфейс"""
        try:
            print(f"Начало добавления клиента {hostname} в UI")
            
            if not hasattr(self, 'clients_view') or self.clients_view is None:
                print(f"Ошибка: clients_view не инициализирован")
                return

            # Проверяем, нет ли уже такого клиента в UI
            for control in self.clients_view.controls[:]:
                if isinstance(control, ft.Container) and any(
                    isinstance(c, ft.ElevatedButton) and c.data == hostname 
                    for c in control.content.controls
                ):
                    print(f"Удаляем существующую строку клиента {hostname}")
                    self.clients_view.controls.remove(control)
                    break

            # Создаем новую строку клиента
            print(f"Создаем новую строку для клиента {hostname}")
            client_row = self.create_client_row(hostname)
            if client_row is None:
                print(f"Не удалось создать строку для клиента {hostname}")
                return

            # Добавляем строку в список клиентов
            print(f"Добавляем строку клиента {hostname} в clients_view")
            self.clients_view.controls.append(client_row)
            
            # Обновляем UI
            if hasattr(self, 'page'):
                print(f"Обновляем страницу для клиента {hostname}")
                self.page.update()
                print(f"Страница обновлена")

            print(f"Клиент {hostname} успешно добавлен в UI")

            # Даем небольшую задержку перед проверкой DND
            def delayed_dnd_check():
                time.sleep(1)  # Даем время на стабилизацию соединения
                if hostname in self.clients:  # Проверяем, что клиент все еще подключен
                    self.check_dnd_status(hostname)

            threading.Thread(target=delayed_dnd_check, daemon=True).start()

        except Exception as e:
            print(f"Ошибка при добавлении клиента {hostname} в UI: {str(e)}")
            import traceback
            print(f"Подробности:\n{traceback.format_exc()}")

    def remove_client(self, hostname):
        """Удаляет клиента и очищает все связанные ресурсы"""
        if hostname in self.clients:
            try:
                # Логируем информацию о клиенте перед удалением
                if hostname in self.client_info:
                    connected_time = self.client_info[hostname].get('connected_time', 0)
                    duration = time.time() - connected_time
                    self.log_message(
                        f"Отключение клиента {hostname}\n"
                        f"IP: {self.client_info[hostname].get('ip', 'неизвестно')}\n"
                        f"Время работы: {int(duration)} секунд"
                    )

                # Закрываем сокет
                try:
                    self.clients[hostname].shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self.clients[hostname].close()
                except Exception:
                    pass

                # Удаляем клиента из интерфейса
                if hasattr(self, 'page'):
                    try:
                        self.remove_client_from_ui(hostname)
                    except Exception as e:
                        self.log_message(f"Ошибка при удалении клиента {hostname} из UI: {str(e)}")

                # Очищаем информацию о клиенте
                if hostname in self.clients:
                    del self.clients[hostname]
                if hostname in self.client_info:
                    del self.client_info[hostname]

                self.log_message(f"Клиент {hostname} успешно отключен и удален из системы")
                
            except Exception as e:
                self.log_message(f"Ошибка при удалении клиента {hostname}: {str(e)}")
        else:
            self.log_message(f"Попытка удаления несуществующего клиента: {hostname}")

    def remove_client_from_ui(self, hostname):
        """Удаляет клиента из интерфейса"""
        try:
            if not hasattr(self, 'clients_view') or self.clients_view is None:
                return
                
            # Ищем и удаляем строку клиента
            for control in self.clients_view.controls[:]:
                if isinstance(control, ft.Container) and any(
                    isinstance(c, ft.ElevatedButton) and c.data == hostname 
                    for c in control.content.controls
                ):
                    self.clients_view.controls.remove(control)
                    break

            # Обновляем UI
            if hasattr(self, 'page'):
                self.page.update()

            self.log_message(f"Клиент {hostname} удален из UI")
        except Exception as e:
            self.log_message(f"Ошибка при удалении клиента {hostname} из UI: {str(e)}")

    def get_local_ip(self):
        """Получает локальный IP адрес компьютера"""
        try:
            # Создаем UDP соединение для определения основного сетевого интерфейса
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            # Если не удалось определить IP, пробуем альтернативный метод
            try:
                # Получаем имя компьютера
                hostname = socket.gethostname()
                # Получаем IP адрес по имени компьютера
                ip = socket.gethostbyname(hostname)
                return ip
            except Exception:
                return '127.0.0.1'  # Возвращаем localhost в крайнем случае

    def broadcast_presence(self):
        message = f"{DISCOVERY_MESSAGE}:{self.host}:{self.port}".encode('utf-8')
        while True:
            try:
                # Отправляем на широковещательный адрес
                self.discovery_socket.sendto(message, ('255.255.255.255', DISCOVERY_PORT))
            except Exception as e:
                print(f"Ошибка при широковещательной рассылке: {e}")
            time.sleep(5)

    def load_existing_connections(self):
        """Загружает существующие подключения в интерфейс"""
        try:
            if not hasattr(self, 'clients_view') or not self.clients_view:
                self.log_message("Ошибка: компонент clients_view не инициализирован")
                return

            # Сохраняем текущие состояния чекбоксов
            checkbox_states = {}
            for control in self.clients_view.controls:
                if isinstance(control, ft.Container):
                    for c in control.content.controls:
                        if isinstance(c, ft.Checkbox):
                            checkbox_states[c.data] = c.value

            # Очищаем текущий список
            self.clients_view.controls.clear()

            # Добавляем существующие подключения
            for hostname in list(self.clients.keys()):
                try:
                    if hostname in self.client_info:
                        # Создаем строку для клиента
                        client_row = self.create_client_row(hostname)
                        if client_row:
                            # Восстанавливаем состояние чекбокса
                            for c in client_row.content.controls:
                                if isinstance(c, ft.Checkbox):
                                    c.value = checkbox_states.get(hostname, False)
                            
                            self.clients_view.controls.append(client_row)
                            
                            # Запрашиваем статус DND для обновления цвета
                            self.check_dnd_status(hostname)
                except Exception as e:
                    self.log_message(f"Ошибка при добавлении клиента {hostname} в интерфейс: {str(e)}")

            # Обновляем интерфейс
            if hasattr(self, 'page'):
                self.page.update()

            self.log_message(f"Загружено {len(self.clients)} существующих подключений")
        except Exception as e:
            self.log_message(f"Ошибка при загрузке существующих подключений: {str(e)}")

    def handle_resize(self, page):
        """Обработка изменения размера окна"""
        try:
            is_mobile = page.width < 600
            
            # Настраиваем размеры элементов для мобильных устройств
            if hasattr(self, 'message_input'):
                self.message_input.width = page.width - 80 if is_mobile else 600
            
            if hasattr(self, 'log_view'):
                self.log_view.width = page.width - 80 if is_mobile else 800
            
            if hasattr(self, 'search_field'):
                self.search_field.width = page.width - 80 if is_mobile else 300

            # Обновляем размер контейнера клиентов
            if hasattr(self, 'clients_view'):
                self.clients_view.height = page.height * 0.4  # 40% высоты страницы
                
            # Перезагружаем список клиентов
            self.load_existing_connections()
            
            # Обновляем страницу
            page.update()
        except Exception as e:
            self.log_message(f"Ошибка при адаптации интерфейса: {str(e)}")

    def check_dnd_status(self, hostname):
        """Запрос статуса DND у клиента"""
        if hostname not in self.clients:
            return
            
        try:
            main_socket = self.clients[hostname]
            if not main_socket:
                return
                
            main_socket.sendall("check_dnd_status\n".encode('utf-8'))
        except Exception as e:
            print(f"Ошибка при запросе статуса DND у {hostname}: {str(e)}")

    def handle_dnd_response(self, hostname, response):
        """Обработка ответа на запрос статуса DND"""
        try:
            if hostname not in self.client_info:
                return
                
            # Определяем цвет в зависимости от статуса
            if "Включен" in response:
                new_color = ft.Colors.RED_500
            elif "Выключен" in response:
                new_color = ft.Colors.GREEN_500
            else:
                new_color = ft.Colors.GREY_500

            # Обновляем цвет кнопки
            if 'button' in self.client_info[hostname]:
                button = self.client_info[hostname]['button']
                button.bgcolor = new_color
                button.color = ft.Colors.WHITE
                
                # Обновляем UI если страница доступна
                if hasattr(self, 'page'):
                    self.page.update()
                
        except Exception as e:
            print(f"Ошибка при обработке статуса DND для {hostname}: {str(e)}")

if __name__ == "__main__":
    # Запускаем сервер на всех интерфейсах, чтобы он был доступен в локальной сети
    admin_server = AdminServer('0.0.0.0', 12345)
    print(f"Веб-интерфейс доступен по адресу: http://{admin_server.host}:{admin_server.web_port}") 