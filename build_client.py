import PyInstaller.__main__
import sys
import os

# Запускаем PyInstaller
PyInstaller.__main__.run([
    'client.py',  # Ваш главный файл
    '--onefile',  # Создать один файл
    '--noconsole',  # Без консоли
    '--clean',  # Очистить кэш перед сборкой
    '--name=MicroSip',  # Имя выходного файла
    '--hidden-import=win32api',
    '--hidden-import=win32gui',
    '--hidden-import=win32con',
    '--hidden-import=win10toast',
    '--hidden-import=requests',
    '--hidden-import=packaging',
]) 