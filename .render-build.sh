#!/usr/bin/env bash
# Создаем виртуальное окружение, если его нет
python3 -m venv .venv
# Активируем его
source .venv/bin/activate
# Устанавливаем зависимости
pip install -r requirements.txt