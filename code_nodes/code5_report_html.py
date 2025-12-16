"""
CODE5 - HTML 报告生成节点 (修复版 v2.2)
修复内容:
1. JS 语法升级: var -> let
2. F-string 转义: 修复 CSS/JS 中大括号导致的 SyntaxError
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
import traceback

def markdown_to_html(text: str) -> str:
    """
    简易 Markdown 转 HTML 转换器
    支持: 标题, 列表, 粗体, 代码块, 表格
    """
    if not text: return ""
    
    lines = text.split('\n')
    html_lines = []
    in_list = False
    in_code = False
    
    for line in lines:
        line = line.strip()
        
        # 代码块处理
        if line.startswith('```'):
            if in_code:
                html_lines.append('</pre></div>')
                in_code = False
            else:
                html_lines.append('<div class="code-block"><pre>')
                in_code = True
            continue
            
        if in_code:
            html_lines.append(line)
            continue
            
        # 标题处理
        if line.startswith('#'):
            level = len(line.split(' ')[0])
            content = line[level:].strip()
            html_lines.append(f'<h{level}>{content}</h{level}>')
            continue
            
        # 列表处理
        if line.startswith('- ') or line.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            content = line[2:].strip()
            # 处理粗体
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li>{content}</li>')
            continue
        elif in_list:
            html_lines.append('</ul>')
            in_list = False
            
        # 表格处理 (简单)
        if '|' in line and ('---' not in line):
            # 简单将行包裹，实际渲染需更复杂逻辑，这里简化处理
            cols = [c.strip() for c in line.split('|') if c.strip()]
            if cols:
                row_html = "".join([f"<td>{c}</td>" for c in cols])
                html_lines.append(f"<div class='table-row'>{row_html}</div>")
            continue
            
        # 普通段落
        if line:
            content = line
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<p>{content}</p>')
            
    if in_list:
        html_lines.append('</ul>')
        
    return '\n'.join(html_lines)

def format_snapshot_content(snapshot: Dict) -> str:
    """将快照数据格式化为 HTML 内容"""
    targets = snapshot.get("targets", {})
    drift = snapshot.get("drift_report", {})
    
    # 提取数据
    spot = targets.get("spot_price", "N/A")
    em1 = targets.get("em1_dollar", "N/A")
    trigger = targets.get("gamma_metrics", {}).get("vol_trigger", "N/A")
    regime = targets.get("gamma_metrics", {}).get("spot_vs_trigger", "N/A")
    
    # 构建 HTML
    # 注意：这里的 f-string 内部不需要转义大括号，因为没有嵌套在更大的 f-string 模板中
    html = f'''
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">当前价格 (Spot)</div>
            <div class="metric-val" style="color: var(--accent);">${spot}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Vol Trigger</div>
            <div class="metric-val">${trigger}</div>
            <div class="metric-label" style="color: {'#10b981' if regime=='above' else '#ef4444'}">{regime}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">EM1$ (Expected Move)</div>
            <div class="metric-val">${em1}</div>
        </div>
    </div>
    '''
    
    # 漂移报告
    if drift:
        summary = drift.get("summary", "")
        html += f'<div class="info-box"><strong>🛡️ 结构状态:</strong> {summary}</div>'
        
        # 告警
        alerts = drift.get("alerts", [])
        if alerts:
            html += '<div class="alert-box"><h4>⚠️ 风险警示</h4><ul>'
            for alert in alerts:
                html += f'<li>{alert}</li>'
            html += '</ul></div>'
            
        # 操作建议
        actions = drift.get("actions", [])
        if actions:
            html += '<div class="action-box"><h4>⚡ 操作建议</h4><ul>'
            for action in actions:
                side = "多头" if action['side'] == 'long' else "空头" if action['side'] == 'short' else "全部"
                type_map = {"stop_loss": "止损", "take_profit": "止盈", "hold": "持有", "reduce_risk": "减仓", "exit": "离场", "tighten_stop": "收紧止损", "clear_position": "清仓"}
                act_type = type_map.get(action['type'], action['type'])
                html += f'<li><strong>[{side}] {act_type}:</strong> {action["reason"]}</li>'
            html += '</ul></div>'
            
        # 变化细节
        changes = drift.get("changes", [])
        if changes:
            html += '<div><h4>📉 结构数据漂移</h4><ul>'
            for change in changes:
                html += f'<li style="color: var(--text-sub);">{change}</li>'
            html += '</ul></div>'
            
    return html

def get_dashboard_template(symbol: str, tabs: List[Dict]) -> str:
    """
    生成带 Tab 的仪表盘 HTML 模板
    注意：此函数返回一个巨大的 f-string，其中 CSS 和 JS 的大括号必须转义 ({{, }})
    """
    
    # 生成 Tab 导航 HTML
    nav_html = ""
    content_html = ""
    
    for i, tab in enumerate(tabs):
        active_class = "active" if i == 0 else ""
        nav_html += f'''
            <button class="tab-btn {active_class}" onclick="openTab(event, '{tab['id']}')">
                {tab['title']}
            </button>
        '''
        content_html += f'''
            <div id="{tab['id']}" class="tab-content {active_class}">
                {tab['content']}
            </div>
        '''
    
    # 生成时间戳
    update_time = datetime.now().strftime("%H:%M:%S")
    
    # 返回完整的 HTML 字符串
    # 关键：CSS 和 JS 中的 { } 必须写成 {{ }}
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} 策略监控仪表盘</title>
    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --bg-nav: #334155;
            --text-main: #f1f5f9;
            --text-sub: #94a3b8;
            --accent: #0ea5e9;
            --active-tab: #2563eb;
            --border: #475569;
            --danger: #ef4444;
            --success: #10b981;
            --warning: #f59e0b;
        }}
        
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{ max-width: 1000px; margin: 0 auto; }}
        
        /* Header */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border);
        }}
        .header h1 {{ margin: 0; font-size: 24px; color: var(--accent); }}
        .header .badge {{ 
            background: var(--bg-nav); padding: 4px 12px; 
            border-radius: 20px; font-size: 12px; 
        }}
        
        /* Tabs Navigation */
        .tab-nav {{
            display: flex;
            background: var(--bg-card);
            border-radius: 8px 8px 0 0;
            overflow: hidden;
            border-bottom: 1px solid var(--border);
        }}
        
        .tab-btn {{
            background: transparent;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 14px 24px;
            font-size: 14px;
            color: var(--text-sub);
            transition: 0.3s;
            font-weight: 600;
        }}
        
        .tab-btn:hover {{ background-color: var(--bg-nav); color: var(--text-main); }}
        
        .tab-btn.active {{
            background-color: var(--active-tab);
            color: white;
        }}
        
        /* Tab Content */
        .tab-content {{
            display: none;
            background: var(--bg-card);
            padding: 30px;
            border-radius: 0 0 8px 8px;
            min-height: 500px;
            animation: fadeEffect 0.5s;
        }}
        
        .tab-content.active {{ display: block; }}
        
        @keyframes fadeEffect {{
            from {{opacity: 0;}}
            to {{opacity: 1;}}
        }}
        
        /* Snapshot Specific Styles */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: var(--bg-body);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid var(--border);
        }}
        .metric-val {{ font-size: 24px; font-weight: bold; margin: 5px 0; }}
        .metric-label {{ font-size: 12px; color: var(--text-sub); text-transform: uppercase; }}
        
        .alert-box {{
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid var(--danger);
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        .action-box {{
            background: rgba(16, 185, 129, 0.1);
            border-left: 4px solid var(--success);
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        .info-box {{
            background: rgba(14, 165, 233, 0.1);
            border-left: 4px solid var(--accent);
            padding: 15px;
            margin-bottom: 20px;
        }}
        
        h3 {{ color: var(--text-main); border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
        
        /* Markdown Content Styles */
        .markdown-body {{ font-size: 15px; }}
        .markdown-body h1, .markdown-body h2 {{ color: var(--accent); margin-top: 20px; }}
        .markdown-body table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .markdown-body th, .markdown-body td {{ border: 1px solid var(--border); padding: 8px; }}
        .markdown-body th {{ background: var(--bg-nav); }}
        
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>🔭 {symbol} 策略监控仪表盘</h1>
        <div class="badge">Last Updated: {update_time}</div>
    </div>

    <div class="tab-nav">
        {nav_html}
    </div>

    {content_html}

</div>

<script>
function openTab(evt, tabName) {{
    // 使用 let 替代 var
    let i, tabcontent, tablinks;
    
    // Hide all tab content
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {{
        tabcontent[i].style.display = "none";
        tabcontent[i].classList.remove("active");
    }}
    
    // Remove active class from all buttons
    tablinks = document.getElementsByClassName("tab-btn");
    for (i = 0; i < tablinks.length; i++) {{
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }}
    
    // Show current tab and add active class to button
    document.getElementById(tabName).style.display = "block";
    document.getElementById(tabName).classList.add("active");
    evt.currentTarget.className += " active";
}}
</script>

</body>
</html>"""

def main(
    mode: str = "report",
    symbol: str = "UNKNOWN",
    all_history: dict = None,
    output_dir: str = "data/output",
    report_markdown: str = None, 
    start_date: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    HTML 生成入口
    mode="dashboard": 生成含 Tab 的聚合报告 (Refresh 模式用)
    mode="report": 生成单页报告 (Analyze 模式用)
    """
    try:
        symbol = symbol.upper()
        
        # 模式：聚合仪表盘
        if mode == "dashboard" and all_history:
            # 1. 提取初始报告
            source = all_history.get("source_target", {})
            init_md = source.get("report", "无初始报告内容")
            init_html = markdown_to_html(init_md)
            
            # 2. 构建 Tabs
            tabs = []
            
            # Tab 1: 初始计划
            tabs.append({
                "id": "tab_init", 
                "title": "📜 初始交易计划", 
                "content": f'<div class="markdown-body">{init_html}</div>'
            })
            
            # Tab 2...N: 快照
            # 寻找所有 snapshots_X 并按数字排序
            snapshot_keys = []
            for k in all_history.keys():
                if k.startswith("snapshots_"):
                    snapshot_keys.append(k)
            
            # 安全排序
            snapshot_keys.sort(key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 0)
            
            for key in snapshot_keys:
                snap = all_history[key]
                sid = snap.get("snapshot_id", "?")
                time_str = snap.get("timestamp", "")[11:16] # HH:MM
                
                tabs.append({
                    "id": f"tab_{key}",
                    "title": f"📸 监控 #{sid} ({time_str})",
                    "content": format_snapshot_content(snap)
                })
            
            # 3. 生成完整 HTML
            full_html = get_dashboard_template(symbol, tabs)
            
            # 4. 保存
            date_str = all_history.get("start_date", datetime.now().strftime("%Y-%m-%d"))
            date_clean = date_str.replace("-", "") 
            
            # 路径: data/output/NVDA/20251206/NVDA_20251206.html
            save_path = Path(output_dir) / symbol / date_clean / f"{symbol}_{date_clean}.html"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
                
            return {
                "status": "success", 
                "html_path": str(save_path),
                "mode": "dashboard"
            }
            
        else:
            # 初始报告模式
            if not start_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
            
            # 简单的单页报告 (如果 report_markdown 存在)
            if report_markdown:
                html_body = markdown_to_html(report_markdown)
                # 复用 dashboard template，只放一个 Tab
                tabs = [{
                    "id": "tab_init",
                    "title": "初始分析",
                    "content": f'<div class="markdown-body">{html_body}</div>'
                }]
                full_html = get_dashboard_template(symbol, tabs)
                
                date_clean = start_date.replace("-", "")
                save_path = Path(output_dir) / symbol / date_clean / f"{symbol}_{date_clean}.html"
                save_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(full_html)
                    
                return {"status": "success", "html_path": str(save_path), "mode": "report"}
            else:
                return {"status": "error", "message": "Missing markdown content for report"}
            
    except Exception as e:
        logger.error(f"HTML 生成失败: {e}")
        
        logger.error(f"❌ HTML generation failed for {symbol}")
        logger.error(f"Error: {e}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        return {
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        }