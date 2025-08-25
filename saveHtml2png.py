import os
import base64
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def capture_html_screenshot(html_path, output_image):
    # ✅ output 폴더 생성
    os.makedirs(os.path.dirname(output_image), exist_ok=True)

    # ✅ Headless 크롬 옵션
    options = Options()
    options.add_argument("--headless=new")  # 최신 버전용
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,2000")  # 창 사이즈 조정

    # ✅ 크롬 드라이버 실행
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # ✅ HTML 열기
    file_url = "file://" + os.path.abspath(html_path)
    driver.get(file_url)

    # ✅ DevTools 프로토콜로 전체 페이지 스크린샷
    result = driver.execute_cdp_cmd("Page.captureScreenshot", {
        "format": "png",
        "captureBeyondViewport": True,
        "fromSurface": True
    })

    # ✅ 저장
    with open(output_image, "wb") as f:
        f.write(base64.b64decode(result['data']))

    driver.quit()
    print(f"✅ 전체 페이지 이미지 저장 완료: {output_image}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("❗ 사용법: python script.py <HTML파일경로> <출력이미지경로>")
        sys.exit(1)

    html_path = sys.argv[1]
    output_image = sys.argv[2]

    capture_html_screenshot(html_path, output_image)
