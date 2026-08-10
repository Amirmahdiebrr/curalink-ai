import re

path = "app/static/css/style.css"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r'(\.cl-mega-panel\{[^}]*?)inset-inline-start\s*:\s*50%\s*;\s*\n(\s*)transform\s*:\s*translateX\(50%\)\s*;',
    r'\1left:50%;\n\2transform:translateX(-50%);',
    content, flags=re.DOTALL
)

content = re.sub(
    r'(\.cl-tooltip::after\{[^}]*?)inset-inline-start\s*:\s*50%\s*;\s*\n(\s*)transform\s*:\s*translateX\(50%\)\s*translateY\(4px\)\s*;',
    r'\1left:50%;\n\2transform:translateX(-50%) translateY(4px);',
    content, flags=re.DOTALL
)

content = content.replace(
    "transform:translateX(50%) translateY(0);",
    "transform:translateX(-50%) translateY(0);"
)

content = re.sub(
    r'(\.cl-organ-bar-value-tag\{[^}]*?)inset-inline-start\s*:\s*50%\s*;\s*transform\s*:\s*translateX\(50%\)\s*;',
    r'\1left:50%; transform:translateX(-50%);',
    content, flags=re.DOTALL
)

content = re.sub(
    r'(\.cl-organ-bar-value-tag::after\{[^}]*?)inset-inline-start\s*:\s*50%\s*;\s*transform\s*:\s*translateX\(50%\)\s*;',
    r'\1left:50%; transform:translateX(-50%);',
    content, flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done.")