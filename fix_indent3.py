path = "app/i18n/en.py"

with open(path, encoding="utf-8") as f:
    lines = f.readlines()

if lines[0].lstrip().startswith('"""') and lines[0] != '"""\n':
    lines[0] = '"""\n'
for i in range(1, 6):
    if lines[i].lstrip().startswith('"""') and lines[i] != '"""\n':
        lines[i] = '"""\n'
        break

close_index = None
for i, line in enumerate(lines):
    if line.strip() == "}":
        close_index = i
        break

if close_index is not None:
    before = lines[:close_index]
    after = lines[close_index+1:]
    after = [l for l in after if l.strip() != "}"]
    new_lines = before + after + ["}\n"]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Fixed. Old close at line {close_index+1}, moved to end.")
else:
    print("No closing '}' line found.")