from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
import os
import flet

# Собираем все файлы данных
datas = collect_data_files('flet')

# Добавляем метаданные пакета
datas += copy_metadata('flet')

# Получаем путь к установленному пакету Flet
flet_path = os.path.dirname(flet.__file__)
web_path = os.path.join(flet_path, 'web')

# Если директория web существует, добавляем её
if os.path.exists(web_path):
    web_files = []
    for root, dirs, files in os.walk(web_path):
        for file in files:
            source = os.path.join(root, file)
            dest = os.path.join('flet', 'web', os.path.relpath(root, web_path))
            web_files.append((source, dest))
    datas.extend(web_files)

# Собираем все подмодули
hiddenimports = collect_submodules('flet')
hiddenimports.extend([
    'flet_core',
    'websockets',
    'asyncio',
    'uvicorn',
    'fastapi',
    'starlette',
    'httptools',
    'watchfiles',
    'websockets.legacy',
    'websockets.legacy.client',
    'websockets.legacy.server',
]) 