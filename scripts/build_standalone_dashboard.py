# -*- coding: utf-8 -*-
"""
风险仪表盘独立文件构建脚本
功能：将 risk-data.json 内嵌到 risk-dashboard.html 中，生成可独立运行的 HTML 文件
用法：python scripts/build_standalone_dashboard.py
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(BASE, 'public', 'risk-dashboard.html')
JSON_PATH = os.path.join(BASE, 'public', 'risk-data.json')
OUT_PATH = os.path.join(BASE, 'public', 'risk-dashboard-standalone.html')

# 读取源文件
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 把 JSON 内嵌为 JS 变量
json_str = json.dumps(data, ensure_ascii=False, indent=2)
embedded_line = f'const EMBEDDED_DATA = {json_str};'

# 替换占位行
if 'const EMBEDDED_DATA = null;' not in html:
    print('[ERROR] HTML placeholder "const EMBEDDED_DATA = null;" not found')
    sys.exit(1)

html = html.replace('const EMBEDDED_DATA = null;', embedded_line)

# 写入输出文件
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'[OK] Generated: {OUT_PATH}')
print(f'     Data date: {data["lastUpdated"]}')
print(f'     Companies: {len(data["companies"])}')
print(f'     File size: {os.path.getsize(OUT_PATH) / 1024:.1f} KB')
