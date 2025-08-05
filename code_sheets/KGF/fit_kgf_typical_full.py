
import json
import numpy as np
import matplotlib.pyplot as plt

# Загрузка входного файла
with open("kgf_typical_input.json", encoding="utf-8") as f:
    data = json.load(f)

# Получение данных
pressures = list(map(float, data["типовая_зависимость"].keys()))
kgf_values = list(data["типовая_зависимость"].values())

# Апроксимация полиномом 6-й степени
coeffs = np.polyfit(pressures, kgf_values, deg=6)
coeff_names = ["A", "B", "C", "D", "E", "F", "G"]
for i, name in enumerate(coeff_names):
    data[name] = round(coeffs[i], 8)

# Сохраняем обновлённые данные
with open("kgf_typical_input.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Построение графика
x = np.linspace(min(pressures), max(pressures), 200)
y = np.polyval(coeffs, x)

plt.figure(figsize=(6, 4))
plt.plot(x, y, label="Апроксимация", color="black")
plt.scatter(pressures, kgf_values, color="gold", edgecolor="black", zorder=5, label="Типовая зависимость")
plt.xlabel("Пластовое давление, МПа")
plt.ylabel("КГФ, г/м³")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("kgf_typical_fit.png", dpi=200)
plt.close()
