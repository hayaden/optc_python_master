import subprocess
import os



#1. 페이지 생성
subprocess.run(["python", "Gimmick_generate_total.py"], check=True)

#2. TM 이미지 저장
subprocess.run(["python", "saveHtml2png.py", "./docs/TM_NW_full.html", "./docs/TM.png"], check=True)

#3. kizuna 이미지 저장
subprocess.run(["python", "saveHtml2png.py", "./docs/KIZUNA_BOSS1.html", "./docs/KIZUNA_BOSS1.png"], check=True)
subprocess.run(["python", "saveHtml2png.py", "./docs/KIZUNA_BOSS2.html", "./docs/KIZUNA_BOSS2.png"], check=True)
subprocess.run(["python", "saveHtml2png.py", "./docs/KIZUNA_SUPERBOSS1.html", "./docs/KIZUNA_SUPERBOSS1.png"], check=True)
subprocess.run(["python", "saveHtml2png.py", "./docs/KIZUNA_SUPERBOSS2.html", "./docs/KIZUNA_SUPERBOSS2.png"], check=True)

#4. pka 이미지 저장
subprocess.run(["python", "saveHtml2png.py", "./docs/PKA_BOSS.html", "./docs/PKA_BOSS.png"], check=True)

# git push
subprocess.run(["python", "git_optc_gimmicks.py"], check=True)
