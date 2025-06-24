import socket
import time

DISCOVERY_PORT = 12346 # Убедитесь, что это тот же порт, что и в admin.py и client.py

print(f"--- Тестовый UDP-слушатель запущен на порту {DISCOVERY_PORT} ---")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Разрешить повторное использование адреса
    
try:
    sock.bind(('', DISCOVERY_PORT)) # Слушаем на всех сетевых интерфейсах
    print("Ожидаю широковещательные сообщения...")
except OSError as e:
    print(f"Ошибка при привязке сокета: {e}. Возможно, порт уже используется.")
    print("Пожалуйста, убедитесь, что никакие другие программы не используют порт 12346 UDP.")
    exit()

sock.settimeout(5) # Таймаут для ожидания данных

while True:
    try:
        data, addr = sock.recvfrom(1024)
        message = data.decode('utf-8')
        print(f"Получено сообщение от {addr}: {message}")
        if message.startswith("ADMIN_SERVER_DISCOVERY"):
            print("--- Обнаружено сообщение администратора! ---")
    except socket.timeout:
        print("Таймаут, продолжаю ожидание...")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    time.sleep(1) 