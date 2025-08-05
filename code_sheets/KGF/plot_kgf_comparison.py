
import json
import matplotlib.pyplot as plt

# Загрузка данных
with open("kgf_comparison_input.json", encoding="utf-8") as f:
    data = json.load(f)

p = data["давление"]
plt.figure(figsize=(10, 5))

# Типовая зависимость
if data["типовая_зависимость"]:
    plt.plot(p, data["типовая_зависимость"], label="Типовая зависимость", linewidth=2)

# Экспериментальные данные
if data["экспериментальные_данные"]:
    plt.plot(p, data["экспериментальные_данные"], label="Экспериментальные данные", linewidth=2)

# Табличные данные
if data["табличные_данные"]:
    plt.plot(p, data["табличные_данные"], label="Табличные данные", linewidth=2)

plt.xlabel("Давление, МПа")
plt.ylabel("КГФ, г/м³")
plt.title("Сравнение зависимостей КГФ от давления")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("kgf_comparison_plot.png", dpi=300)
plt.show()
