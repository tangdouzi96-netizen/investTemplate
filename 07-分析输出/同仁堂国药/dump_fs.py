"""搜各年年报审计报告页 → 定位后续财务报表 → dump"""
import fitz, sys, glob, json
sys.stdout.reconfigure(encoding='utf-8')

BASE = "D:/Project/investTemplate/07-分析输出/同仁堂国药/年报"

for year in [2021, 2022, 2023]:
    files = glob.glob(f'{BASE}/同仁堂国药_03613_{year}年年报_*')
    if not files: continue
    doc = fitz.open(files[0])
    print(f'\n=== {year} ===')

    auditor_pg = None
    for pg in range(doc.page_count):
        text = doc[pg-1].get_text('text')
        if '獨立核數師報告' in text or 'INDEPENDENT AUDITOR' in text:
            auditor_pg = pg
            # Check if it's the actual report start (not TOC)
            if 'OPINION' in text or '意見' in text:
                print(f'  Auditor report at PDF p{pg+1}')
                break

    if auditor_pg is None:
        print(f'  Auditor report not found, searching...')
        for pg in range(40, doc.page_count):
            text = doc[pg-1].get_text('text')
            if 'OPINION' in text and 'consolidated financial statements' in text.lower():
                auditor_pg = pg
                print(f'  Auditor report (fallback) at PDF p{pg+1}')
                break

    if auditor_pg:
        # Dump the auditor report and 20 following pages
        with open(f'fs_{year}_dump.txt', 'w', encoding='utf-8') as f:
            for pg in range(auditor_pg, min(doc.page_count, auditor_pg + 25)):
                text = doc[pg-1].get_text('text')
                f.write(f'\n{"="*60}\nPDF p{pg+1}\n{"="*60}\n')
                f.write(text[:2000])
                f.write('\n')
        print(f'  Dumped {auditor_pg+1} to {min(doc.page_count, auditor_pg+25)}')
    else:
        # Last resort: dump page 80+
        print(f'  Fallback: dumping pages 80-130')
        with open(f'fs_{year}_dump.txt', 'w', encoding='utf-8') as f:
            for pg in range(80, min(doc.page_count, 130)):
                text = doc[pg-1].get_text('text')
                f.write(f'\n{"="*60}\nPDF p{pg+1}\n{"="*60}\n')
                f.write(text[:2000])
                f.write('\n')

    doc.close()

print('\nDone')
