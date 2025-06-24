from cx_Freeze import setup, Executable
import sys

# Настройки для компиляции
build_exe_options = {
    "packages": ["os", "tkinter", "socket", "threading", "configparser", "platform", 
                "ipaddress", "ctypes", "win32gui", "win32con", "win32process"],
    "excludes": ["pygame", "numpy"],
    "include_msvcr": True,
    "include_files": [],
    "optimize": 2,
    "silent": True
}

# Создаем исполняемый файл
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # Используем Win32GUI для скрытия консоли

setup(
    name="MicroSip",
    version="1.0",
    description="MicroSip Process",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "client.py",
            base=base,
            target_name="MicroSip.exe",
            icon="microsip.ico",  # Иконка будет добавлена позже
            copyright="© MicroSip",
        )
    ]
) 