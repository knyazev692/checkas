import os
import sys
import re
import subprocess
import requests
import json
from pathlib import Path

# Конфигурация
GITHUB_REPO = "knyazev692/checkas"  # Замените на ваш репозиторий
CLIENT_FILE = "client.py"
TOKEN_FILE = "github_token.txt"

def get_github_token():
    """Получает токен GitHub из файла"""
    try:
        if not os.path.exists(TOKEN_FILE):
            print(f"Ошибка: Файл {TOKEN_FILE} не найден")
            print("Создайте файл github_token.txt и поместите в него ваш токен GitHub")
            sys.exit(1)
        
        with open(TOKEN_FILE, 'r') as f:
            token = f.read().strip()
            if not token:
                print("Ошибка: Токен в файле пустой")
                sys.exit(1)
            return token
    except Exception as e:
        print(f"Ошибка при чтении токена: {e}")
        sys.exit(1)

def get_current_version():
    """Получает текущую версию из файла client.py"""
    with open(CLIENT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    raise ValueError("Версия не найдена в файле client.py")

def build_exe():
    """Компилирует клиент в exe"""
    print("Сборка exe файла...")
    icon_path = 'icon.ico'
    
    # Получаем путь к Python и PyInstaller
    python_path = sys.executable
    scripts_dir = os.path.join(os.path.dirname(python_path), 'Scripts')
    pyinstaller_path = os.path.join(scripts_dir, 'pyinstaller.exe')
    
    # Проверяем наличие PyInstaller
    if not os.path.exists(pyinstaller_path):
        print(f"PyInstaller не найден по пути: {pyinstaller_path}")
        print("Пробуем установить PyInstaller...")
        try:
            subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pyinstaller"], 
                         check=True, capture_output=True)
            print("PyInstaller успешно установлен")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при установке PyInstaller: {e}")
            sys.exit(1)
    
    # Формируем команду
    cmd = [python_path, "-m", "PyInstaller", "--onefile", "--noconsole", "--name=MicroSIP"]
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
    cmd.extend([
        "--hidden-import=win32api",
        "--hidden-import=win32gui",
        "--hidden-import=win32con",
        "--hidden-import=win10toast",
        "--hidden-import=requests",
        "--hidden-import=packaging"
    ])
    cmd.append(CLIENT_FILE)
    
    print(f"Выполняем команду: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("Ошибка при сборке:")
            print(result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Ошибка при выполнении команды: {e}")
        sys.exit(1)
    
    exe_path = os.path.join('dist', 'MicroSIP.exe')
    if not os.path.exists(exe_path):
        print("Ошибка: exe файл не найден после сборки")
        sys.exit(1)
    
    return exe_path

def create_github_release(version, exe_path):
    """Создает релиз на GitHub"""
    token = get_github_token()
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    # Создаем релиз
    print(f"Создание релиза v{version}...")
    release_data = {
        'tag_name': f'v{version}',
        'name': f'MicroSIP Version {version}',
        'body': f'MicroSIP Release version {version}',
        'draft': False,
        'prerelease': False
    }

    response = requests.post(
        f'https://api.github.com/repos/{GITHUB_REPO}/releases',
        headers=headers,
        json=release_data
    )

    if response.status_code != 201:
        print("Ошибка при создании релиза:")
        print(response.json())
        sys.exit(1)

    release = response.json()

    # Загружаем exe файл
    print("Загрузка exe файла...")
    with open(exe_path, 'rb') as f:
        response = requests.post(
            release['upload_url'].replace('{?name,label}', ''),
            headers={
                'Authorization': f'token {token}',
                'Content-Type': 'application/octet-stream'
            },
            params={'name': 'MicroSIP.exe'},
            data=f
        )

    if response.status_code != 201:
        print("Ошибка при загрузке файла:")
        print(response.json())
        sys.exit(1)

    print(f"Релиз v{version} успешно создан!")
    print(f"URL релиза: {release['html_url']}")

def main():
    # Получаем текущую версию
    version = get_current_version()
    print(f"Текущая версия: {version}")

    # Собираем exe
    exe_path = build_exe()
    print(f"Exe файл собран: {exe_path}")

    # Создаем релиз на GitHub
    create_github_release(version, exe_path)

if __name__ == "__main__":
    main() 