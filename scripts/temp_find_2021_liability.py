"""查找2021年年报合并资产负债表负债/权益页"""
import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"d:\Project\investTemplate\07-分析输出\青岛港年报\青岛港：青岛港国际股份有限公司2021年年度报告.pdf"
doc = fitz.open(path)

# 搜索"负债合计"且不含"母公司"关键词
print("=== 搜索 负债合计 (合并报表) ===")
for pg in range(95, 115):
    text = doc[pg].get_text("text")
    if "负债合计" in text:
        # 检查是否为合并报表
        first300 = text[:500]
        if "母公司" in first300:
            label = "【母公司】"
        elif "合并" in first300:
            label = "【合并】"
        else:
            label = "【?】"

        # 找到负债合计所在行
        idx = text.find("负债合计")
        ctx = text[max(0,idx-200):min(len(text),idx+400)]

        # 检查负债合计的数值上下文
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == "负债合计":
                # 找到附近数字
                for j in range(i, min(i+5, len(lines))):
                    print(f"  p{pg+1} {label} 负债合计行: '{line.strip()}' → 数据行: '{lines[j].strip()[:80]}'")
                break
        else:
            # 没有精确匹配行
            # 找包含负债合计的行
            for i, line in enumerate(lines):
                if "负债合计" in line and "流动" not in line and "非流动" not in line:
                    print(f"  p{pg+1} {label} {line.strip()[:120]}")
                    break

# 搜索资产总计+负债合计同时在同页
print("\n=== 搜索 资产总计+负债合计 同页的页码 ===")
for pg in range(95, 115):
    text = doc[pg].get_text("text")
    if "资产总计" in text and "负债合计" in text:
        # 计算大概的总资产值
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == "资产总计":
                for j in range(i, min(i+5, len(lines))):
                    import re
                    nums = re.findall(r'[\d,]+\.?\d+', lines[j].strip())
                    for n in nums:
                        v = float(n.replace(',',''))
                        if v > 100_000_000:
                            yi = v / 100_000_000
                            print(f"  p{pg+1} 资产总计: {yi:.2f}亿")
                            break
                    break
            if line.strip() == "负债合计":
                for j in range(i, min(i+5, len(lines))):
                    nums = re.findall(r'[\d,]+\.?\d+', lines[j].strip())
                    for n in nums:
                        v = float(n.replace(',',''))
                        if v > 100_000_000:
                            yi = v / 100_000_000
                            print(f"  p{pg+1} 负债合计: {yi:.2f}亿")
                            break
                    break

# 打印103页内容开头
print("\n=== Page 103 开头 ===")
print(doc[102].get_text("text")[:1000])

doc.close()
