import subprocess
import os
import shutil
import glob

def git_push(repo_path, commit_message="변경"):
    original_dir = os.getcwd()  # 현재 파이썬 실행 디렉토리
    docs_path = os.path.join(original_dir, "docs")  # 외부 docs 폴더

    os.chdir(repo_path)

    try:
        # 1️⃣ 레포 폴더 내 HTML 삭제
        for html_file in glob.glob("*.html"):
            os.remove(html_file)
        print("🗑️ 레포 내 HTML 삭제 완료")

        # 2️⃣ docs 폴더 → 레포로 복사
        if not os.path.exists(docs_path):
            raise FileNotFoundError(f"docs 폴더 없음: {docs_path}")
        for file in os.listdir(docs_path):
            if file.endswith(".html"):
                shutil.copy(os.path.join(docs_path, file), repo_path)
        print("📄 외부 docs → 레포 HTML 복사 완료")

        # 3️⃣ Git 명령 실행
        subprocess.run(["git", "add", "."], check=True)
        print("✅ git add 완료")

        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("✅ git commit 완료")

        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ git push 완료")

    except subprocess.CalledProcessError as e:
        print(f"❌ git 명령 실패: {e}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    repo_path = r"C:\optc\hayaden\optc-gimmicks"
    git_push(repo_path)
