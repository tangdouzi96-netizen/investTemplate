"""
从巨潮资讯网下载中国平安(601318)年度报告 PDF。
"""

import os
import re
import time
import requests
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置区
# ============================================================
COMPANY_NAME = "中国平安"
STOCK_CODE = "601318"
YEARS = [2021, 2022, 2023, 2024, 2025]

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "07-分析输出" / "中国平安" / "年报"

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


def search_annual_reports() -> dict[int, dict]:
    """
    搜索公司年度报告，返回 {年份: {title, url, date}} 字典。
    """
    params = {
        "searchkey": f"{COMPANY_NAME} 年度报告",
        "sdate": f"{min(YEARS)}-01-01",
        "edate": f"{max(YEARS) + 1}-06-30",
        "isfulltext": "false",
        "sortName": "pubdate",
        "sortType": "desc",
        "pageNum": 1,
    }

    print(f"正在搜索：{COMPANY_NAME} 年度报告 ...")
    resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    announcements = data.get("announcements") or []
    total = data.get("totalAnnouncement", 0)
    print(f"共找到 {total} 条公告，逐个筛选年报...")

    # 筛选：A股年报标题多样，用宽松的正则
    results: dict[int, dict] = {}
    # 匹配各种年报标题格式
    pattern = re.compile(r"(\d{4})\s*年\s*年\s*(?:度)?\s*报[告報]")
    exclude_keywords = ["摘要", "补充", "澄清", "修订", "更正", "通知", "通函",
                        "信函", "委任", "登记股东", "非登记股东", "表格", "申请",
                        "已审", "H股", "季度", "半年度", "半", "三季", "一季",
                        "二季", "四季", "月报"]

    for ann in announcements:
        title = ann.get("announcementTitle", "")
        clean_title = re.sub(r"<[^>]+>", "", title)

        # 必须包含"中国平安"或601318代码相关
        if COMPANY_NAME not in clean_title and STOCK_CODE not in clean_title:
            continue

        match = pattern.search(clean_title)
        if not match:
            continue

        year = int(match.group(1))
        if year not in YEARS:
            continue

        if any(kw in clean_title for kw in exclude_keywords):
            continue

        t = ann.get("announcementTime", 0)
        date_str = datetime.fromtimestamp(t / 1000).strftime("%Y-%m-%d") if isinstance(t, (int, float)) else str(t)[:10]

        pdf_path = ann.get("adjunctUrl", "")
        results[year] = {
            "title": clean_title,
            "date": date_str,
            "url": DOWNLOAD_BASE + pdf_path,
        }

    return results


def download_pdf(year: int, info: dict, output_dir: Path) -> bool:
    """下载单个年报 PDF。"""
    filename = f"{COMPANY_NAME}_{STOCK_CODE}_{year}年年报_{info['date']}.pdf"
    filepath = output_dir / filename

    if filepath.exists():
        print(f"  [{year}年] 已存在，跳过 → {filename}")
        return True

    print(f"  [{year}年] 下载中 ... {info['url'][:80]}...")
    resp = requests.get(info["url"], headers=HEADERS, timeout=120)
    resp.raise_for_status()

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(resp.content)

    size_mb = len(resp.content) / (1024 * 1024)
    print(f"  [{year}年] 完成 {size_mb:.1f}MB → {filepath}")
    return True


def main():
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"输出目录：{output_dir}")
    print(f"目标年份：{', '.join(str(y) for y in YEARS)}")
    print("-" * 50)

    # Step 1: 搜索
    reports = search_annual_reports()

    # Step 2: 报告搜索结果
    found_years = set(reports.keys())
    missing_years = set(YEARS) - found_years

    print(f"\n匹配到年报：{len(reports)} 份")
    for y in sorted(found_years):
        r = reports[y]
        print(f"  {y}年 → {r['title'][:80]}")
        print(f"       发布日期: {r['date']}")

    if missing_years:
        print(f"\n未找到的年份：{', '.join(str(y) for y in sorted(missing_years))}")

    if not reports:
        print("\n未找到任何年报，请检查公司名称和搜索参数。")
        return

    # Step 3: 逐一下载
    print(f"\n开始下载 ({REQUEST_INTERVAL}秒间隔)...")
    success = 0
    for year in sorted(reports):
        download_pdf(year, reports[year], output_dir)
        success += 1
        if year != sorted(reports)[-1]:
            time.sleep(REQUEST_INTERVAL)

    print(f"\n完成！成功 {success}/{len(reports)} 份")
    print(f"文件位置：{output_dir}")


if __name__ == "__main__":
    main()
