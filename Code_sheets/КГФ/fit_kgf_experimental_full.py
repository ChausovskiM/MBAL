import json
import numpy as np
import matplotlib.pyplot as plt

def load_data(path="kgf_experimental_input.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def fit_polynomial(points, degree=4):
    p = [row["P"] for row in points]
    kgf = [row["KGF_fact"] for row in points]
    coeffs = np.polyfit(p, kgf, degree)
    return coeffs, p, kgf

def calculate_c5_and_kik(coeffs, Pнк, Pпл):
    kgf_pnk = np.polyval(coeffs, Pнк)
    kgf_ppl = np.polyval(coeffs, Pпл)
    kik = kgf_pnk / kgf_ppl if kgf_ppl else 0
    return round(kgf_pnk, 3), round(kik, 3)

def append_results(data, coeffs, c5, kik):
    labels = ["A", "B", "C", "D", "E"]
    for label, value in zip(labels, coeffs):
        data[label] = round(value, 8)
    data["C5+"] = c5
    data["КИК"] = kik
    return data

def save_data(data, path="kgf_experimental_input.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def plot(p_exp, kgf_exp, coeffs, Pнк, Pпл):
    p_range = np.linspace(0, max(p_exp) + 2, 200)
    kgf_fit = np.polyval(coeffs, p_range)

    plt.figure(figsize=(10, 5))
    plt.plot(p_range, kgf_fit, label="Аппроксимация", linewidth=2)
    plt.scatter(p_exp, kgf_exp, color="orange", label="Экспериментальные данные", zorder=5)
    plt.axvline(Pнк, color='gray', linestyle='--', label=f"Pнк = {Pнк}")
    plt.axvline(Pпл, color='blue', linestyle='--', label=f"Pпл = {Pпл}")
    plt.xlabel("Давление, МПа")
    plt.ylabel("КГФ, г/м³")
    plt.title("Экспериментальная зависимость КГФ от давления")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("kgf_experimental_fit.png", dpi=300)
    plt.show()

def main():
    data = load_data()
    coeffs, p_list, kgf_list = fit_polynomial(data["points"])
    c5, kik = calculate_c5_and_kik(coeffs, data["Pнк"], data["Pпл"])
    updated = append_results(data, coeffs, c5, kik)
    save_data(updated)
    plot(p_list, kgf_list, coeffs, data["Pнк"], data["Pпл"])
    print("Коэффициенты, C5+ и КИК добавлены в kgf_experimental_input.json")
    print("График сохранён как kgf_experimental_fit.png")

if __name__ == "__main__":
    main()
