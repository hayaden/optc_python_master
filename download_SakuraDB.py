from src.auth import register_user, login_user
from database import check_database

# If no errors are thrown, the user registration, login, and database download should be successful.

def main():
    for lang in ['ko']:
        print(f"--- {lang} 버전 처리중 ---")
        register_user(language=lang)
        login_user(language=lang)
        check_database(lang)  # 언어별로 파일명 다르게 저장하도록

if __name__ == "__main__":
    main()
#pip install -r requirements.txt   
#python login.py