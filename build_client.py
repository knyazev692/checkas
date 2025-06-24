import PyInstaller.__main__
import sys
import os

# Параметры сборки
PyInstaller.__main__.run([
    'client.py',  # Имя основного файла
    '--name=MicroSip',  # Имя выходного файла
    '--noconsole',  # Без консоли
    '--onefile',  # Один исполняемый файл
    '--clean',  # Очистка предыдущей сборки
    '--uac-admin',  # Запрос прав администратора
    '--hidden-import=winreg',  # Скрытые импорты
    '--hidden-import=socket',
    '--hidden-import=threading',
    '--hidden-import=platform',
    '--hidden-import=ctypes',
    '--hidden-import=logging',
    '--hidden-import=datetime',
    '--version-file=version.txt',  # Информация о версии
]) 