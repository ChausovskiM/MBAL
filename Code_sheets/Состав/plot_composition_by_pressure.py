
import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# Загрузка данных
with open("composition_input.json", "r", encoding="utf-8") as f:
    data = json.load(f)

Pnk = data["Pnk_MPA"]
components = data["components"]
comp_pnk = np.array(data["composition_at_pnk"])  # массив в %
ogr_data = data["ogr_table"]
P = np.array(ogr_data["pressure"])
OGR = np.array(ogr_data["ogr"])

# Интерполяции
ogr_func = interp1d(P, OGR, kind="linear", fill_value="extrapolate")
ogr_pnk = float(ogr_func(Pnk))

# Генерация таблицы состава при каждом давлении
composition_table = []
for p in P:
    ogr_p = float(ogr_func(p))
    Z = ogr_p / ogr_pnk
    norm_factors = comp_pnk / comp_pnk  # по сути = 1
    weighted = norm_factors * Z
    composition = (weighted / weighted.sum()) * (100 - comp_pnk[-1])  # без C5+
    composition = list(composition[:-1]) + [comp_pnk[-1]]  # добавляем C5+ как есть
    composition_table.append(composition)

# Построение графиков
composition_table = np.array(composition_table)

fig, axes = plt.subplots(4, 3, figsize=(15, 12), sharex=True)
axes = axes.flatten()

for i in range(len(components)):
    ax = axes[i]
    ax.plot(P, composition_table[:, i], label=components[i])
    ax.set_title(components[i])
    ax.grid(True)
    if i >= 9:
        ax.set_xlabel("Давление, МПа")
    if i % 3 == 0:
        ax.set_ylabel("Содержание, %")
    ax.legend()

plt.tight_layout()
plt.show()
