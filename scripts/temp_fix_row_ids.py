"""将溯源表中的 B/C/D/N 行号统一重编号为 A-prefix"""
import re

path = r"d:\Project\investTemplate\数据溯源\青岛港_06198_数据溯源表.md"
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 行号映射
remap = {}

# A-PL: A01-A14 (14 rows) → keep
# A-BS: B01-B24 → A15-A38
for i in range(1, 25):
    remap[f"B{i:02d}"] = f"A{i+14:02d}"

# A-CF: C01-C06 → A39-A44
for i in range(1, 7):
    remap[f"C{i:02d}"] = f"A{i+38:02d}"

# A-DIV: D01-D04 → A45-A48
for i in range(1, 5):
    remap[f"D{i:02d}"] = f"A{i+44:02d}"

# A-NOTE: N01-N03 → A49-A51
for i in range(1, 4):
    remap[f"N{i:02d}"] = f"A{i+48:02d}"

# B区: B01-B08 → A52-A59
for i in range(1, 9):
    remap[f"B{i:02d}"] = f"A{i+51:02d}"

# 替换: | B01 | → | A15 |
# 使用正则替换表格行首的编号
lines = text.split('\n')
new_lines = []
for line in lines:
    if line.lstrip().startswith('|'):
        cells = line.strip().strip('|').split('|')
        cells = [c.strip() for c in cells]
        if cells and cells[0] in remap:
            cells[0] = remap[cells[0]]
        line = '| ' + ' | '.join(cells) + ' |'
    new_lines.append(line)

result = '\n'.join(new_lines)

# 也替换纯文本中的编号引用（如 "C01/C02"）
for old, new in remap.items():
    # 只替换表格外的引用
    result = re.sub(rf'\bC01\b', 'A39', result)
    result = re.sub(rf'\bC02\b', 'A40', result)
    result = re.sub(rf'\bB01\b', 'A15', result)
    result = re.sub(rf'\bB04\b', 'A18', result)

with open(path, 'w', encoding='utf-8') as f:
    f.write(result)

print("✅ 行号重编号完成")
# 验证
with open(path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.lstrip().startswith('|') and re.match(r'^[|][ ]*[A-Z]\d{2}', line):
            print(f"  {line.strip()[:80]}")
