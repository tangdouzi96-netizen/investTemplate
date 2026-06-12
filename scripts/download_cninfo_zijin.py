"""
从巨潮资讯网下载紫金矿业近5年（2021-2025）年度报告 PDF。

紫金矿业：A股 601899.SH / H股 02899.HK
巨潮 API 免费公开，无需注册/登录/API Key。
"""

import re
import time
import requests
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置区
# ============================================================
COMPANY_NAME = "紫金矿业"
STOCK_CODE = "601899"          # A股代码（主）
YEARS = [2021, 2022, 2023, 2024, 2025]

# 输出目录
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "07-分析输出" / "紫金矿业" / "年报"

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
    自动翻页，确保不遗漏靠后的结果。
    """
    print(f"正在搜索：{COMPANY_NAME} 年度报告 ...")

    all_announcements = []
    page_num = 1
    total = 0

    while True:
        params = {
            "searchkey": f"{COMPANY_NAME} 年度报告",
            "sdate": f"{min(YEARS)}-01-01",
            "edate": f"{max(YEARS) + 1}-06-30",
            "isfulltext": "false",
            "sortName": "pubdate",
            "sortType": "desc",
            "pageNum": page_num,
        }

        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        announcements = data.get("announcements") or []
        total = data.get("totalAnnouncement", 0)
        all_announcements.extend(announcements)

        page_size = len(announcements)
        fetched = len(all_announcements)
        print(f"  第{page_num}页: {page_size}条 (已取{fetched}/{total})")

        if fetched >= total or page_size == 0:
            break

        page_num += 1
        time.sleep(0.3)  # 翻页间隔，避免请求过快

    print(f"共找到 {total} 条公告，已全部获取，逐个筛选年报...")

    # 标题匹配模式（兼容多种格式）
    patterns = [
        re.compile(r"紫金矿业集团股份有限公司(\d{4})年年度报告"),
        re.compile(r"紫金矿业[：:]\s*(\d{4})年年度报告"),
        re.compile(r"紫金矿业[：:]\s*(\d{4})年年报"),
        re.compile(r"紫金矿业\s+(\d{4})年年度报告"),
    ]

    exclude_keywords = [
        "摘要", "半年度", "半年", "季度", "H股", "月报",
        "补充", "澄清", "修订", "更正", "通知", "通函",
        "信函", "委任", "登记股东", "非登记股东", "表格",
        "申请", "环境", "社会及管治", "ESG", "企业社会责任",
        "监管", "问询", "回覆", "回复", "说明", "专项",
        "调研", "调研活动", "投资者关系",
    ]

    results: dict[int, dict] = {}

    for ann in all_announcements:
        title = ann.get("announcementTitle", "")
        clean_title = re.sub(r"<[^>]+>", "", title)

        # 排除关键词
        if any(kw in clean_title for kw in exclude_keywords):
            continue

        # 匹配年份
        matched_year = None
        for pat in patterns:
            m = pat.search(clean_title)
            if m:
                matched_year = int(m.group(1))
                break

        if matched_year is None or matched_year not in YEARS:
            continue

        # 同一年份优先保留含"集团股份有限公司"的完整版
        if matched_year in results:
            existing_is_full = "集团股份有限公司" in results[matched_year]["title"]
            new_is_full = "集团股份有限公司" in clean_title
            if existing_is_full and not new_is_full:
                continue

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


def download_pdf(year: int, info: dict, output_dir: Path) -> bool:
    """下载单个年报 PDF。"""
    filename = f"{COMPANY_NAME}_{STOCK_CODE}_{year}年年报_{info['date']}.pdf"
    filepath = output_dir / filename

    if filepath.exists():
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"  [{year}年] 已存在，跳过 → {filename} ({size_mb:.1f}MB)")
        return True

    print(f"  [{year}年] 下载中 ... {info['url'][:80]}...")
    try:
        resp = requests.get(info["url"], headers=HEADERS, timeout=180)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [{year}年] 下载失败: {e}")
        return False

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(resp.content)

    size_mb = len(resp.content) / (1024 * 1024)
    print(f"  [{year}年] 完成 {size_mb:.1f}MB → {filepath.name}")
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
        print(f"  {y}年 → {r['title'][:100]}")
        print(f"       发布日期: {r['date']}")

    if missing_years:
        print(f"\n未找到的年份：{', '.join(str(y) for y in sorted(missing_years))}")
        for y in sorted(missing_years):
            if y == max(YEARS):
                print(f"  {y}年：年报通常次年4月披露，可能尚未发布或需其他渠道")

    if not reports:
        print("\n未找到任何年报，请检查公司名称或搜索参数。")
        return

    # Step 3: 逐一下载
    print(f"\n开始下载 ({REQUEST_INTERVAL}秒间隔)...")
    success = 0
    for year in sorted(reports):
        ok = download_pdf(year, reports[year], output_dir)
        if ok:
            success += 1
        if year != sorted(reports)[-1]:
            time.sleep(REQUEST_INTERVAL)

    print(f"\n完成！成功 {success}/{len(reports)} 份")
    print(f"文件位置：{output_dir}")


if __name__ == "__main__":
    main()
