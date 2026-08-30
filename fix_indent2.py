path = "app/i18n/fa.py"

with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# فیکس ایندنت داکیومنت اول فایل
if lines[0].startswith("    \"\"\""):
    lines[0] = '"""\n'
if lines[5].startswith("    \"\"\""):
    lines[5] = '"""\n'

# پیدا کردن خط '}\n' که دیکشنری رو زودتر از موعد بسته
close_index = None
for i, line in enumerate(lines):
    if line.strip() == "}":
        close_index = i
        break

if close_index is not None:
    before = lines[:close_index]
    after = lines[close_index+1:]
    # آخرین خط فایل رو هم بررسی کن که خودش '}' نباشه (تکراری)
    after = [l for l in after if l.strip() != "}"]
    new_lines = before + after + ["}\n"]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Fixed. Old close at line {close_index+1}, moved to end.")
else:
    print("No closing '}' line found.")