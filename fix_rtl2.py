import re
import shutil

path = "app/static/css/style.css"
shutil.copy(path, path + ".bak2")

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
removed = 0
for line in lines:
    stripped = line.strip()
    if stripped == "direction:rtl;" or stripped == "flex-direction:row-reverse;":
        removed += 1
        continue
    out.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(out)

print(f"Removed {removed} lines.")