"""
从巨潮资讯网下载康方生物近5年（2021-2025）年度报告 PDF。

康方生物：港股 09926.HK
巨潮 API 免费公开，无需注册/登录/API Key。

标题格式：康方生物：2025 年报 / 康方生物－B：2021 年报
"""

import re
import time
import requests
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置区
# ============================================================
COMPANY_NAME = "康方生物"
STOCK_CODE = "09926"          # 港股代码
YEARS = [2021, 2022, 2023, 2024, 2025]

# 输出目录
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "07-分析输出" / "康方生物" / "年报"

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
    一次搜索取回所有结果，避免对每个年份分别请求。
    """
    params = {
        "searchkey": "康方生物 年报",
        "sdate": f"{min(YEARS) - 1}-01-01",
        "edate": f"{max(YEARS) + 1}-06-30",
        "isfulltext": "false",
        "sortName": "pubdate",
        "sortType": "desc",
        "pageNum": 1,
    }

    print(f"正在搜索：{COMPANY_NAME} 年报 ...")
    resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    announcements = data.get("announcements") or []
    total = data.get("totalAnnouncement", 0)
    print(f"共找到 {total} 条公告，逐个筛选年报...")

    # 标题匹配模式
    # 康方生物年报标题有多种格式：
    #   后期：康方生物：2025 年报
    #   早期：康方生物-Ｂ：2021 年报（全角Ｂ U+FF22）
    # 统一用宽松匹配：康方生物后任意字符直到四位年份+年报
    patterns = [
        re.compile(r"康方生物.*?(\d{4})\s*年报"),
        re.compile(r"康方生物\s+(\d{4})\s*年[度]?报[告]?"),
    ]

    # 排除：通知函、通函、非登记持有人等非年报公告
    exclude_keywords = [
        "通知函", "通知信函", "通函",
        "登记股东", "非登记持有人",
        "申请表格", "委任表格",
        "补充", "澄清", "修订", "更正",
        "环境、社会及管治", "ESG",
    ]

    results: dict[int, dict] = {}

    for ann in announcements:
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

        # 同一年份优先保留不含"-B"的（更新版通常去掉B标记）
        if matched_year in results:
            existing_has_b = "－B" in results[matched_year]["title"] or "-B" in results[matched_year]["title"]
            new_has_b = "－B" in clean_title or "-B" in clean_title
            if existing_has_b and not new_has_b:
                # 替换为无B标记版本
                pass
            elif not existing_has_b and new_has_b:
                continue  # 保留现有无B版本

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
