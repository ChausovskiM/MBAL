MBAL: модульная реализация материального баланса и вспомогательных расчётов

Этот репозиторий — рабочая реализация расчётного комплекса для газоконденсатного/нефтегазового объекта. Проект переносит логику Excel/VBA-книги (листы: PVT, KGF, PZ, GDI, Productivity, Temperature, Base, Components) в модульные скрипты на Python с JSON-вводом/выводом и возможностью построения графиков.

Ключевые возможности

PVT-блок: вычисление 
𝑍
Z, плотности, вязкости и связанных величин для газовой смеси (поддержка методов: BB, GUR, PR, табличные значения).

KGF (конденсат-газовый фактор): работа с экспериментальными/табличными данными и аппроксимацией (полином 4-й степени).

PZ (материальный баланс): расчёт функции давления, накопленной добычи, вспомогательные модулы 
𝑀
𝑏
𝑎
𝑙
_
𝐴
.
.
𝐸
,
𝐻
𝑢
𝑟
𝑠
𝑡
,
𝑅
𝑒
Mbal_A..E,Hurst,Re.

GDI / Productivity: расчёт дебита, устьевого давления, производительности по IPR и др.

Temperature: расчёты температурных профилей (по необходимости).

Components: валидация и нормализация компонентного состава газа.

Графики: сохранение результатов и построение профилей/кривых (Matplotlib).

Автодокументация: при запуске отдельных функций создаются краткие текст-описания в .txt (если включено в модулях).

Структура репозитория
.
├─ code_sheets/
│  ├─ PVT/                # PVT расчёты
│  │  └─ pvt_controller.py
│  ├─ KGF/                # Конденсат-газовый фактор
│  │  └─ kgf_controller.py
│  ├─ PZ/                 # Материальный баланс
│  │  └─ pz_controller.py
│  ├─ GDI/
│  │  └─ gdi_controller.py
│  ├─ Productivity/
│  │  └─ prod_controller.py
│  ├─ Temperature/
│  │  └─ temperature_controller.py
│  ├─ Components/
│  │  └─ components_controller.py
│  └─ Base/
│     └─ base_controller.py
├─ data/
│  ├─ input_properties.json          # входные общие свойства
│  ├─ gas_components.json            # исходный состав газа
│  ├─ gas_components_normalized.json # нормализованный состав (генерируется)
│  └─ ... (доп. входные файлы)
├─ results/                          # все выходные JSON/PNG/CSV
├─ runner.py                         # линейный запуск всех контроллеров
├─ requirements.txt
└─ README.md


📌 В некоторых версиях проекта контроллеры лежат в корне (pvt_controller.py, kgf_controller.py и т.д.). Либо сохраните текущую структуру, либо обновите пути в runner.py.

Установка и запуск
1) Среда и зависимости
# Рекомендуется Python 3.10.x
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt


Если requirements.txt отсутствует, установите базовые пакеты вручную:

pip install numpy pandas matplotlib scipy openpyxl python-dateutil

2) Подготовьте входные JSON

Минимальный набор находится в data/. Примеры:

data/gas_components.json

{
  "components": [
    {"name": "N2", "z": 0.02},
    {"name": "CO2", "z": 0.03},
    {"name": "C1", "z": 0.78},
    {"name": "C2", "z": 0.10},
    {"name": "C3+", "z": 0.07}
  ],
  "units": "mole_fraction"
}


data/input_properties.json

{
  "reservoir_pres": 28.0,
  "oil_rate_res": 0.0,
  "gor_res": 0.0,
  "wcut_res": 0.0,
  "temperature": 90.0,
  "pressure_points": [10,15,20,25,30]
}


⚙️ Мольные доли не обязательно должны быть нормализованы — модуль Components создаст gas_components_normalized.json и будет использовать его далее.

3) Запуск по одному модулю
# Примеры — адаптируйте к вашей структуре
python code_sheets/Components/components_controller.py
python code_sheets/PVT/pvt_controller.py
python code_sheets/KGF/kgf_controller.py
python code_sheets/PZ/pz_controller.py
python code_sheets/GDI/gdi_controller.py
python code_sheets/Productivity/prod_controller.py
python code_sheets/Temperature/temperature_controller.py
python code_sheets/Base/base_controller.py


Результаты сохраняются в results/ в виде JSON/PNG/CSV.
Графики сохраняются в файлы и, при желании, могут отображаться интерактивно (см. ниже).

4) Линейный запуск всех модулей
python runner.py


runner.py последовательно вызывает контроллеры. Убедитесь, что пути к скриптам внутри него совпадают со структурой репозитория.

Вход/Выход и соглашения

Вход: JSON-файлы в data/ (параметры среды, таблицы, состав, контрольные точки давления/температуры).

Выход: рассчитываемые таблицы и кривые записываются в results/ (обычно *.json + *.png).

Компонентный состав: модуль Components выполняет проверку и при необходимости создаёт gas_components_normalized.json; дальнейшие расчёты используют именно его.

PVT: функции Z_calc, Density_calc, Visc_calc принимают явный аргумент gas_components — глобальные переменные не используются.

Материальный баланс: ключевая ветвь расчётов от calc → MBAL_fP → Mbal_*, Z_calc, далее — расчёт дебитов/давлений и т.п.

Графики и режим отображения

По умолчанию скрипты сохраняют графики в results/*.png.
Если нужен интерактивный показ:

Убедитесь, что не используется «безголовый» backend Matplotlib.

Не блокируйте выполнение, если запуск идёт в батче — замените plt.show() на сохранение (plt.savefig(...)) или делайте это через флаг окружения/аргумент CLI.

Упаковка в EXE (Windows, PyInstaller)

Базовый сценарий:

pip install pyinstaller
pyinstaller --onefile --name MBAL runner.py


Рекомендации:

Пропишите в runner.spec копирование директории data/ и создание пустой results/.

Если используете Matplotlib, проверьте backend (частая причина зависаний при старте).

Для доступа к данным используйте пути, независимые от cwd (например, через Path(__file__).parent).

Отладка и типовые проблемы

Зависание на графиках: используйте сохранение вместо plt.show() в пакетном режиме, либо задайте подходящий backend.

Нет файла входных данных: проверьте, что data/*.json на месте и структура соответствует примерам выше.

Сумма мольных долей ≠ 1: просто запустите components_controller.py — он создаст нормализованный файл.

Сломались пути: синхронизируйте структуру code_sheets/* и пути в runner.py.
