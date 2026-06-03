"""
探索同仁堂国药(03613.HK)港股年报结构
港股vsA股差异：IFRS格式、科目名不同、单位通常是千元/百万元
"""
import fitz, re, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "D:/Project/investTemplate/07-分析输出/同仁堂国药/年报"

for year in [2021, 2022, 2023, 2024, 2025]:
    fn = f"同仁堂国药_03613_{year}年年报_{year+1}-04-"
    import glob
    files = glob.glob(f"{BASE}/同仁堂国药_03613_{year}年年报_*")
    if not files:
        print(f"❌ {year} 未找到")
        continue

    pdf_path = files[0]
    doc = fitz.open(pdf_path)
    print(f"\n{'='*60}")
    print(f"📊 {year} ({doc.page_count}页)")

    # 搜索关键财务报表标志
    found = {}
    for pg in range(min(doc.page_count, 100)):  # 前100页足够
        text = doc[pg].get_text("text")

        # 港股常用报表名
        checks = {
            '综合损益表': ['收入', '收益', '损益'],
            '综合财务状况表': ['财务状况表', '资产', '负债'],
            '综合现金流量表': ['现金流量表', '经营活动'],
            '综合收益表': ['全面收益', '其他综合收益'],
            '主要财务数据': ['摘要', '概览', '财务摘要', '财务概要'],
            '分部': ['分部', '经营分部'],
            '每股盈利': ['每股盈利', '每股收益'],
        }

        for label, keywords in checks.items():
            if label in found:
                continue
            if all(kw in text for kw in keywords[:1]):
                if label not in found:
                    found[label] = pg + 1

    for label, pg_num in found.items():
        print(f"  {label}: p{pg_num}")

    # 检查前几页看单位
    for pg in range(min(10, doc.page_count)):
        text = doc[pg].get_text("text")
        if '千港元' in text or '千元' in text or '百万元' in text or '万元' in text:
            unit_line = [l.strip() for l in text.split('\n') if '千港元' in l or '千元' in l or '百万元' in l or '万元' in l]
            if unit_line:
                print(f"  单位(p{pg+1}): {unit_line[0][:100]}")
                break

    doc.close()

print("\n✅ 探索完成")
