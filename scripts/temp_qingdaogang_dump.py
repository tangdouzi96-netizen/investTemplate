"""青岛港 - 逐页 dump 合并三大报表 + 关键附注"""
import fitz, os, sys
sys.stdout.reconfigure(encoding='utf-8')

base = r"d:\Project\investTemplate\07-分析输出\青岛港年报"
out_dir = r"d:\Project\investTemplate\scripts\temp_qingdaogang_dumps"
os.makedirs(out_dir, exist_ok=True)

# 各年年报路径 + 合并报表页码（从上一步确认）
years_config = {
    2025: {
        "path": os.path.join(base, "青岛港：2025年度报告.pdf"),
        "bs_pages": [101, 102],
        "pl_page": 105,
        "cf_pages": [108, 109],
        "note_pages": list(range(56, 210)),  # 附注范围（宽）
    },
    2024: {
        "path": os.path.join(base, "青岛港：2024年度报告.pdf"),
        "bs_pages": [113, 114],
        "pl_page": 117,
        "cf_pages": [120, 121],
        "note_pages": list(range(67, 210)),
    },
    2023: {
        "path": os.path.join(base, "青岛港：2023年度报告.pdf"),
        "bs_pages": [111, 112],
        "pl_page": 115,
        "cf_pages": [118, 119],
        "note_pages": list(range(66, 210)),
    },
    2022: {
        "path": os.path.join(base, "青岛港：2022年度报告.pdf"),
        "bs_pages": [116, 117],
        "pl_page": 120,
        "cf_pages": [123, 124],
        "note_pages": list(range(65, 210)),
    },
    2021: {
        "path": os.path.join(base, "青岛港：青岛港国际股份有限公司2021年年度报告.pdf"),
        "bs_pages": [101, 102],
        "pl_page": 106,
        "cf_page": 111,
        "cf_pages": [111],
        "note_pages": list(range(94, 210)),
    },
}

for year in sorted(years_config.keys(), reverse=True):
    cfg = years_config[year]
    if not os.path.exists(cfg["path"]):
        print(f"❌ {year}: 文件不存在")
        continue

    doc = fitz.open(cfg["path"])
    out_file = os.path.join(out_dir, f"{year}_dump.txt")

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"{'='*80}\n")
        f.write(f"青岛港 {year}年年报 · 合并报表 dump\n")
        f.write(f"{'='*80}\n\n")

        # BS 页
        for pg_num in cfg.get("bs_pages", []):
            text = doc[pg_num - 1].get_text("text")
            f.write(f"\n{'─'*80}\n")
            f.write(f"📄 BS 第{pg_num}页 (PDF页码)\n")
            f.write(f"{'─'*80}\n")
            f.write(text[:8000])  # 限长
            f.write("\n")

        # PL 页
        if isinstance(cfg.get("pl_page"), int):
            text = doc[cfg["pl_page"] - 1].get_text("text")
            f.write(f"\n{'─'*80}\n")
            f.write(f"📄 PL 第{cfg['pl_page']}页\n")
            f.write(f"{'─'*80}\n")
            f.write(text[:8000])
            f.write("\n")

        # CF 页
        for pg_num in cfg.get("cf_pages", []):
            text = doc[pg_num - 1].get_text("text")
            f.write(f"\n{'─'*80}\n")
            f.write(f"📄 CF 第{pg_num}页\n")
            f.write(f"{'─'*80}\n")
            f.write(text[:8000])
            f.write("\n")

    print(f"✅ {year} → {out_file}")
    doc.close()

print("\n完成！dump 文件在:", out_dir)
