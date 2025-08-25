import subprocess
import os



#1. 페이지 생성
#subprocess.run(["python", "eventBoostList.py"], check=True)

#subprocess.run(["python", "saveHtml2png.py", "./output/event_boost_characters.html", "./output/event_boost_characters.png"], check=True)

subprocess.run(["python", "saveHtml2png.py", "./docs/OPTC Ships.html", "./docs/ship.png"], check=True)
