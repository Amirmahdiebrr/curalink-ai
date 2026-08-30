path = "app/i18n/fa.py"

with open(path, encoding="utf-8") as f:
    lines = f.readlines()

out = []
for line in lines:
    stripped = line.lstrip(" \t")
    if stripped.strip() == "" or stripped.lstrip().startswith("#"):
        out.append(line)
        continue
    if stripped.startswith('"'):
        out.append("    " + stripped)
    else:
        out.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(out)

print("Done.")