import subprocess
import os
import shutil
import glob

def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)

def git_push(repo_path, commit_message="변경"):
    original_dir = os.getcwd()
    docs_path = os.path.join(original_dir, "docs")

    if not os.path.isdir(repo_path):
        raise FileNotFoundError(f"레포 경로가 아님: {repo_path}")

    os.chdir(repo_path)
    try:
        # 현재 브랜치 감지
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip() or "main"

        # 최신 원격 상태 받아오기
        run(["git", "fetch", "origin"])

        # 레포 루트의 *.html 삭제
        for html_file in glob.glob("*.html"):
            try:
                os.remove(html_file)
            except FileNotFoundError:
                pass
        print("🗑️ 레포 내 HTML 삭제 완료")

        # 외부 docs → 레포 복사
        if not os.path.exists(docs_path):
            raise FileNotFoundError(f"docs 폴더 없음: {docs_path}")
        for file in os.listdir(docs_path):
            if file.endswith(".html"):
                shutil.copy2(os.path.join(docs_path, file), repo_path)
        print("📄 외부 docs → 레포 HTML 복사 완료")

        # 변경 스테이징
        run(["git", "add", "-A"])
        print("✅ git add -A 완료")

        # 원격 대비 앞/뒤 카운트
        # 형식: "<behind>\t<ahead>"
        # (origin/main...HEAD 는 서로 다른 커밋만 비교)
        rev = run(["git", "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD"]).stdout.strip()
        behind, ahead = (int(x) for x in rev.split())

        # 커밋 필요 여부
        status = run(["git", "status", "--porcelain"]).stdout.strip()
        if status:
            run(["git", "commit", "-m", commit_message])
            print("✅ git commit 완료")
        else:
            print("ℹ️ 변경 사항 없음 → 커밋 스킵")

        # 원격이 앞서 있으면 우선 rebase로 정리
        if behind > 0:
            print(f"ℹ️ 원격이 {behind}개 앞섬 → pull --rebase 수행")
            try:
                run(["git", "pull", "--rebase", "origin", branch])
                print("✅ pull --rebase 완료")
            except subprocess.CalledProcessError as e:
                print(f"❌ rebase 중 충돌 발생\nSTDERR:\n{e.stderr}")
                print("👉 충돌 파일 수정 후: git add <파일들> → git rebase --continue 실행 필요")
                return  # 충돌 해결 후 재실행

        # 푸시
        try:
            run(["git", "push", "origin", branch])
            print(f"✅ git push origin {branch} 완료")
        except subprocess.CalledProcessError as e:
            # fast-forward 불가 등으로 거절될 때 마지막 방어
            print(f"❌ git push 실패: {e.stderr}")
            print("👉 먼저 `git pull --rebase origin {branch}` 후 다시 시도하세요.")
    except subprocess.CalledProcessError as e:
        print(f"❌ git 명령 실패: {e}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    repo_path = r"C:\optc\hayaden\optc-gimmicks"
    git_push(repo_path)
