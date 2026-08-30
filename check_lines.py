path = "app/i18n/fa.py"

with open(path, encoding="utf-8") as f:
    lines = f.readlines()

for i in range(1, 8):
    print(i, repr(lines[i-1]))

print("...")

for i in range(1078, 1090):
    if i-1 < len(lines):
        print(i, repr(lines[i-1]))