"""2021年年报 - 补提缺失科目"""
import fitz, sys, re
sys.stdout.reconfigure(encoding='utf-8')

path = r"d:\Project\investTemplate\07-分析输出\青岛港年报\青岛港：青岛港国际股份有限公司2021年年度报告.pdf"
doc = fitz.open(path)

# BS page 104 (equity continuation)
print("=== Page 104 (BS equity continuation) ===")
text_104 = doc[103].get_text("text")
print(text_104[:3000])

# PL page 107 (find 归母净利润)
print("\n\n=== Page 107 (PL bottom) ===")
text_107 = doc[106].get_text("text")
# Search for 归属
lines_107 = text_107.split('\n')
for i, line in enumerate(lines_107):
    if "归属" in line or "归母" in line or "净利润" in line or "净利潤" in line:
        ctx_start = max(0, i-1)
        ctx_end = min(len(lines_107), i+6)
        print(f"  [{i}] " + " | ".join(lines_107[ctx_start:ctx_end]))
        print()

# CF page 112 (find CAPEX)
print("\n\n=== Page 112 (CF bottom) - search for CAPEX ===")
text_112 = doc[111].get_text("text")
lines_112 = text_112.split('\n')
for i, line in enumerate(lines_112):
    if "购建" in line or "購建" in line or "固定" in line:
        ctx_start = max(0, i-1)
        ctx_end = min(len(lines_112), i+6)
        print(f"  [{i}] " + " | ".join(lines_112[ctx_start:ctx_end]))
        print()

# Also search page 111 for CAPEX
print("\n=== Page 111 (CF top) - search for CAPEX ===")
text_111 = doc[110].get_text("text")
lines_111 = text_111.split('\n')
for i, line in enumerate(lines_111):
    if "购建" in line or "購建" in line:
        ctx_start = max(0, i-1)
        ctx_end = min(len(lines_111), i+6)
        print(f"  [{i}] " + " | ".join(lines_111[ctx_start:ctx_end]))
        print()

# Search for 投资收益 (对联营/合营) in PL
print("\n=== Search PL for 投资收益 对联营 ===")
for pg in [105, 106]:  # p106-107 (0-indexed)
    text = doc[pg].get_text("text")
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if ("联营" in line or "聯營" in line or "合营" in line or "合營" in line) and ("投资" in line or "投資" in line):
            ctx_start = max(0, i-1)
            ctx_end = min(len(lines), i+5)
            print(f"  p{pg+1}[{i}] " + " | ".join(lines[ctx_start:ctx_end]))
            print()

doc.close()
