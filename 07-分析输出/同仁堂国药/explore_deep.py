"""
深度探索同仁堂国药年报 - 找到所有财务报表页面
"""
import fitz, re, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

BASE = "D:/Project/investTemplate/07-分析输出/同仁堂国药/年报"

for year in [2021, 2022, 2023, 2024, 2025]:
    files = glob.glob(f"{BASE}/同仁堂国药_03613_{year}年年报_*")
    if not files:
        continue

    doc = fitz.open(files[0])
    print(f"\n{'='*60}")
    print(f"📊 {year} ({doc.page_count}页) - {files[0].split('/')[-1][:50]}")

    found = {}
    # 搜索全文档
    for pg in range(doc.page_count):
        text = doc[pg].get_text("text")

        # 港股财务报表标志词
        checks = {
            '综合损益表': ['综合损益表'],
            '综合财务状况表': ['综合财务状况表', '财务状况表', '综合财政状况表'],
            '综合现金流量表': ['综合现金流量表', '现金流量表'],
            '综合全面收益表': ['综合全面收益表', '综合收益表'],
            '权益变动表': ['权益变动表'],
            '财务报表附注': ['财务报表附注'],
            '分部报告': ['分部资料', '经营分部', '分部信息'],
        }

        for label, keywords in checks.items():
            if label in found:
                continue
            for kw in keywords:
                if kw in text and '母公司' not in text[:200]:
                    found[label] = pg + 1
                    break

    # 打印找到的财务报表页面
    for label in ['综合损益表', '综合全面收益表', '综合财务状况表', '综合现金流量表', '权益变动表', '财务报表附注', '分部报告']:
        if label in found:
            pg = found[label]
            text = doc[pg-1].get_text("text")
            # 提取前200字符显示
            preview = text[:200].replace('\n', ' | ')
            print(f"  ✅ {label}: p{pg} | {preview}")

    # 如果没找到财务状况表，尝试搜索BS特征词
    if '综合财务状况表' not in found:
        for pg in range(doc.page_count):
            text = doc[pg].get_text("text")
            if '资产' in text and '负债' in text and '权益' in text and '非流动' in text:
                if pg+1 not in found.values():
                    found['疑财务状况表'] = pg + 1
                    print(f"  ⚠️ 疑似BS: p{pg+1} | {text[:200].replace(chr(10),' | ')}")
                    break

    # 如果没找到现金流量表，尝试搜索CF特征词
    if '综合现金流量表' not in found:
        for pg in range(doc.page_count):
            text = doc[pg].get_text("text")
            if '经营活动' in text and '投资活动' in text and '筹资活动' in text and '现金' in text:
                if pg+1 not in found.values():
                    found['疑现金流量表'] = pg + 1
                    print(f"  ⚠️ 疑似CF: p{pg+1} | {text[:200].replace(chr(10),' | ')}")
                    break

    doc.close()

print("\n✅ 探索完成")
