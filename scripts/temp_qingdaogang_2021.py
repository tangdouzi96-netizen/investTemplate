"""2021年年报专项提取 - 处理跨页BS和PL"""
import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"d:\Project\investTemplate\07-分析输出\青岛港年报\青岛港：青岛港国际股份有限公司2021年年度报告.pdf"
doc = fitz.open(path)

# BS: p101(资产前部), p102(资产后部), p105(负债), p106(负债尾+权益+PL前部)
# PL: p106(PL前部), p107(PL后部) — 需确认
# CF: p111, p112

print("=== BS Pages 101-102-105-106 ===")
for pg_num in [101, 102, 105, 106]:
    text = doc[pg_num-1].get_text("text")
    print(f"\n--- Page {pg_num} (前2000字符) ---")
    print(text[:2000])

print("\n\n=== PL 搜索 (查找 净利润/归母) ===")
# 全文档搜索净利润
for pg in range(doc.page_count):
    text = doc[pg].get_text("text")
    if ("归属于母公司" in text or "歸屬於母公司" in text) and "净利润" in text:
        # 确认是合并报表
        if "合并" in text[:500] or "母公司" not in text[:300]:
            idx = text.find("归属于母公司")
            if idx < 0:
                idx = text.find("歸屬於母公司")
            print(f"\np{pg+1}: ...{text[max(0,idx-200):idx+500]}...")
            break

# PL 完整dump
print("\n\n=== PL Page 106 + 107 完整 ===")
for pg_num in [106, 107]:
    text = doc[pg_num-1].get_text("text")
    print(f"\n--- Page {pg_num} ---")
    print(text)

# CF 完整dump
print("\n\n=== CF Page 111 + 112 完整 ===")
for pg_num in [111, 112]:
    text = doc[pg_num-1].get_text("text")
    print(f"\n--- Page {pg_num} ---")
    print(text[:6000])

# 搜索CAPEX
print("\n\n=== 搜索 CAPEX (购建固定) ===")
for pg in range(doc.page_count):
    text = doc[pg].get_text("text")
    if "购建固定" in text and "合并" in text[:500]:
        idx = text.find("购建固定")
        print(f"\np{pg+1}: {text[max(0,idx-100):idx+300]}")

doc.close()
