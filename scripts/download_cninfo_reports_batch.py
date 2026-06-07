"""
从巨潮资讯网批量下载三家公司2021-2025年度报告 PDF：
  - 招商银行 (600036.SH)
  - 保利物业 (06049.HK)
  - 中海物业 (02669.HK)
"""

import re
import time
import requests
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置区
# ============================================================
COMPANIES = [
    {
        "name": "招商银行",
        "code": "600036",
        "market": "A股",
        "search_key": "招商银行 年度报告",
        # "招商银行：年度报告2025" or "招商银行：招商银行股份有限公司2025年度报告"
        "title_patterns": [
            re.compile(r"股份有限公司(\d{4})年度报告"),   # full format (preferred)
            re.compile(r"年度报告(\d{4})"),              # simple format (fallback)
        ],
        "exclude": ["摘要", "半年度", "半", "季度", "H股", "月报", "补充"],
        "output_subdir": "招商银行",
    },
    {
        "name": "保利物业",
        "code": "06049",
        "market": "H股",
        "search_key": "保利物业 年度报告",
        # "保利物业：2025年度报告"
        "title_patterns": [
            re.compile(r"保利物业[：:]\s*(\d{4})年度报告"),
        ],
        "exclude": ["(1)", "(2)", "补充", "摘要"],
        "output_subdir": "保利物业",
    },
    {
        "name": "中海物业",
        "code": "02669",
        "market": "H股",
        "search_key": "中海物业 年报",
        # "中海物业：2025年年报"
        "title_patterns": [
            re.compile(r"中海物业[：:]\s*(\d{4})年年报"),
        ],
        "exclude": ["补充"],
        "output_subdir": "中海物业",
    },
]

YEARS = [2021, 2022, 2023, 2024, 2025]
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_BASE = BASE_DIR / "07-分析输出"

SEARCH_URL = "http://www.cninfo.com.cn/new/fulltextSearch/full"
DOWNLOAD_BASE = "https://static.cninfo.com.cn/"
REQUEST_INTERVAL = 1.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "http://www.cninfo.com.cn/",
}


def search_annual_reports(cfg: dict) -> dict:
    """搜索公司年度报告，返回 {年份: {title, date, url}} 字典。"""
    params = {
        "searchkey": cfg["search_key"],
        "sdate": f"{min(YEARS)}-01-01",
        "edate": f"{max(YEARS) + 1}-06-30",
        "isfulltext": "false",
        "sortName": "pubdate",
        "sortType": "desc",
        "pageNum": 1,
    }

    print(f"  Searching: '{cfg['search_key']}' ...")
    resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    announcements = data.get("announcements") or []
    print(f"  Found {data.get('totalAnnouncement', 0)} announcements, filtering...")

    results: dict = {}
    exclude_kw = cfg["exclude"]
    patterns = cfg["title_patterns"]

    for ann in announcements:
        title = ann.get("announcementTitle", "")
        clean_title = re.sub(r"<[^>]+>", "", title)

        # Exclusion check (before pattern matching)
        if any(kw in clean_title for kw in exclude_kw):
            continue

        # Try each pattern (first match wins — order matters)
        matched_year = None
        for pat in patterns:
            m = pat.search(clean_title)
            if m:
                matched_year = int(m.group(1))
                break

        if matched_year is None or matched_year not in YEARS:
            continue

        # Prefer full-format reports over simple-format for same year
        if matched_year in results:
            existing_is_full = "股份有限公司" in results[matched_year]["title"]
            new_is_full = "股份有限公司" in clean_title
            if existing_is_full and not new_is_full:
                continue  # Keep existing full-format

        t = ann.get("announcementTime", 0)
        if isinstance(t, (int, float)):
            date_str = datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d")
        else:
            date_str = str(t)[:10]

        pdf_path = ann.get("adjunctUrl", "")
        if not pdf_path:
            continue

        results[matched_year] = {
            "title": clean_title,
            "date": date_str,
            "url": DOWNLOAD_BASE + pdf_path,
        }

    return results


def download_pdf(cfg: dict, year: int, info: dict, output_dir: Path) -> bool:
    """下载单个年报 PDF。"""
    filename = f"{cfg['name']}_{cfg['code']}_{year}年年报_{info['date']}.pdf"
    filepath = output_dir / filename

    if filepath.exists():
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"    [{year}] Already exists ({size_mb:.1f}MB), skip -> {filename}")
        return True

    print(f"    [{year}] Downloading ... {info['url'][:80]}...")
    try:
        resp = requests.get(info["url"], headers=HEADERS, timeout=180)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [{year}] Download FAILED: {e}")
        return False

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(resp.content)

    size_mb = len(resp.content) / (1024 * 1024)
    print(f"    [{year}] Done {size_mb:.1f}MB -> {filepath.name}")
    return True


def process_company(cfg: dict):
    """处理单个公司的搜索+下载全流程。"""
    name = cfg["name"]
    code = cfg["code"]
    output_dir = OUTPUT_BASE / cfg["output_subdir"]

    print(f"\n{'='*60}")
    print(f"  {name} ({code}) -- target years {', '.join(str(y) for y in YEARS)}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Search
    reports = search_annual_reports(cfg)

    found_years = set(reports.keys())
    missing_years = set(YEARS) - found_years

    print(f"\n  Matched annual reports: {len(reports)}")
    for y in sorted(found_years):
        r = reports[y]
        print(f"    {y} -> {r['title'][:100]}")
        print(f"         Published: {r['date']}")

    if missing_years:
        print(f"\n  [!] Missing years: {', '.join(str(y) for y in sorted(missing_years))}")

    if not reports:
        print(f"\n  [X] No annual reports found. Check search parameters.")
        return 0, len(YEARS)

    # Step 2: Download
    print(f"\n  Downloading ...")
    success = 0
    for year in sorted(reports):
        ok = download_pdf(cfg, year, reports[year], output_dir)
        if ok:
            success += 1
        if year != sorted(reports)[-1]:
            time.sleep(REQUEST_INTERVAL)

    print(f"\n  [OK] {name} done! Success {success}/{len(reports)}")
    return success, len(missing_years)


def main():
    print("=" * 60)
    print("  CNINFO Annual Report Batch Download")
    print(f"  Target years: {', '.join(str(y) for y in YEARS)}")
    print(f"  Companies: {len(COMPANIES)}")
    print("=" * 60)

    total_success = 0
    total_missing = 0

    for i, cfg in enumerate(COMPANIES):
        s, m = process_company(cfg)
        total_success += s
        total_missing += m
        if i < len(COMPANIES) - 1:
            time.sleep(REQUEST_INTERVAL * 2)

    print(f"\n{'='*60}")
    print(f"  ALL DONE!")
    print(f"  Total success: {total_success} / target: {len(COMPANIES) * len(YEARS)}")
    if total_missing > 0:
        print(f"  Missing: {total_missing} (manual supplement needed)")
    print(f"  Files location: {OUTPUT_BASE}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
