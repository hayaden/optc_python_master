import os
import json
from readGimmickInformation import export_gimmick_html

# ✅ 서버 ID → 사용자 정의 이름 매핑
GIMMICK_NAME_MAP = {
    5000029: "궤적 VS 보니 패턴",
    5000030: "궤적 VS 행콕 패턴",
    5000031: "궤적 VS 빅맘 패턴",
  
    # 필요 시 추가...
}

# ✅ HTML 개별 생성
def batch_export_from_json_folder(json_folder=".", output_folder="./docs"):
    os.makedirs(output_folder, exist_ok=True)
    exported = []

    for file in os.listdir(json_folder):
        if file.startswith("gimmicks_raw_") and file.endswith(".json"):
            try:
                server_id = int(file.split("_")[-1].replace(".json", ""))
                json_path = os.path.join(json_folder, file)
                output_path = os.path.join(output_folder, f"gimmicks_{server_id}.html")

                export_gimmick_html(server_id=server_id, output_path=output_path)
                with open(json_path, "r", encoding="utf-8") as f:
                    parsed_json = json.load(f)
                exported.append((server_id, parsed_json))
            except Exception as e:
                print(f"❌ 처리 실패: {file} → {e}")
    return exported

# ✅ 설명 요약 추출
def extract_summary(parsed_json):
    stages = list(parsed_json.values())
    last_stage = stages[-1] if stages else None
    if not last_stage:
        return ""
    
    phase = last_stage[-1]
    summary = []

    if "level_condition_text" in phase:
        summary.append(phase["level_condition_text"].strip())

    for v in phase.values():
        if isinstance(v, dict) and "texts" in v:
            for t in v["texts"]:
                clean = t.replace("<", "").replace(">", "")
                if len(summary) < 4:
                    summary.append(clean)

    return " / ".join(summary)

# ✅ index.html 생성
def generate_index_html(entries, output_path="./docs/index.html"):
    html = [
        "<!DOCTYPE html><html><head><meta charset='UTF-8'>",
        "<title>기믹 목록</title>",
        "<style>",
        "body { background-color: #13514d; color: #f2f2f7; font-family: sans-serif; padding: 2em; font-size: 32px; }",  # ← 폰트 크기 수정
        "a { color: #87cefa; font-weight: bold; text-decoration: none; font-size: 32px; }",  # ← 링크도 키움
        ".entry { margin-bottom: 1em; }",
        ".id { font-weight: bold; color: gold; font-size: 32px; }",
        ".summary { color: #dddddd; font-size: 16px; margin-left: 1em; }",  # ← 요약도 조금 키움
        "</style></head><body>",
        "<h1 style='font-size: 40px;'>🚩 기믹 패턴 목록</h1><hr>"
    ]

    for server_id, parsed_json in sorted(entries, key=lambda x: x[0]):
        filename = f"gimmicks_{server_id}.html"
        display_name = GIMMICK_NAME_MAP.get(server_id, str(server_id))
        summary = ""
        html.append(
            f"<div class='entry'><a href='{filename}'><span class='id'>[{display_name}]</span></a>"
            f"<span class='summary'> {summary}</span></div>"
        )

    html.append("</body></html>")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"✅ index.html 생성 완료 → {output_path}")

# ✅ 전체 실행
if __name__ == "__main__":
    JSON_DIR = "."
    HTML_DIR = "./docs"
    entries = batch_export_from_json_folder(JSON_DIR, HTML_DIR)
    generate_index_html(entries, os.path.join(HTML_DIR, "index.html"))
