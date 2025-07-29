import json
import numpy as np

def load_input(path="kgf_experimental_input.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save_result(data, path="kgf_experimental_result.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def compute_approximation(input_data):
    coeffs = [input_data[k] for k in ["A", "B", "C", "D", "E"]]
    results = []
    for point in input_data["points"]:
        P = point["P"]
        KGF_fact = point["KGF_fact"]
        KGF_approx = np.polyval(coeffs, P)
        deviation = (KGF_approx - KGF_fact) / KGF_fact * 100 if KGF_fact else None
        results.append({
            "P, МПа": round(P, 3),
            "KGF_факт, г/м³": round(KGF_fact, 2),
            "KGF_аппрокс, г/м³": round(KGF_approx, 2),
            "откл, %": round(deviation, 1)
        })
    return results

def main():
    input_data = load_input()
    results = compute_approximation(input_data)
    save_result(results)
    print("Расчёт КГФ_аппрокс и отклонения завершён. Результат в kgf_experimental_result.json")

if __name__ == "__main__":
    main()
