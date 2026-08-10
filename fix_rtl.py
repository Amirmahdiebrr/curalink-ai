import re
import shutil

path = "app/static/css/style.css"
shutil.copy(path, path + ".bak")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    (r'text-align\s*:\s*right\s*;', 'text-align:start;'),
    (r'text-align\s*:\s*left\s*;', 'text-align:end;'),
    (r'\bright\s*:\s*(-?[\d.]+(?:px|%|em|rem|vh|vw)|0)\s*;', r'inset-inline-start:\1;'),
    (r'\bleft\s*:\s*(-?[\d.]+(?:px|%|em|rem|vh|vw)|0)\s*;', r'inset-inline-end:\1;'),
    (r'border-right\s*:', 'border-inline-start:'),
    (r'border-left\s*:', 'border-inline-end:'),
    (r'margin-right\s*:', 'margin-inline-start:'),
    (r'margin-left\s*:', 'margin-inline-end:'),
    (r'padding-right\s*:', 'padding-inline-start:'),
    (r'padding-left\s*:', 'padding-inline-end:'),
    (r'border-top-right-radius', 'border-start-start-radius'),
    (r'border-top-left-radius', 'border-start-end-radius'),
    (r'border-bottom-right-radius', 'border-end-start-radius'),
    (r'border-bottom-left-radius', 'border-end-end-radius'),
    (r'float\s*:\s*right\s*;', 'float:inline-start;'),
    (r'float\s*:\s*left\s*;', 'float:inline-end;'),
]

for pattern, repl in replacements:
    content = re.sub(pattern, repl, content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done. Backup saved as style.css.bak")