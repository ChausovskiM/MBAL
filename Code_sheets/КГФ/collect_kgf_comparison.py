
import json

# Загрузка экспериментальных данных
with open("kgf_experimental_input.json", encoding="utf-8") as f:
    exp_data = json.load(f)

# Загрузка типовых данных
with open("kgf_typical_input.json", encoding="utf-8") as f:
    typ_data = json.load(f)

# Подготовка сводного файла
comparison_data = {
    "P_нк": exp_data["Pнк"],
    "P_пл": exp_data["Pпл"],
    "давление": list(exp_data["типовая_зависимость"].keys()) if "типовая_зависимость" in exp_data else [],
    "экспериментальные_данные": list(exp_data["типовая_зависимость"].values()) if "типовая_зависимость" in exp_data else [],
    "типовая_зависимость": list(typ_data["типовая_зависимость"].values()) if "типовая_зависимость" in typ_data else [],
    "табличные_данные": []
}

# Переписываем давление в числовой вид
comparison_data["давление"] = [float(x) for x in comparison_data["давление"]]

# Сохраняем
with open("kgf_comparison_input.json", "w", encoding="utf-8") as f:
    json.dump(comparison_data, f, ensure_ascii=False, indent=2)
