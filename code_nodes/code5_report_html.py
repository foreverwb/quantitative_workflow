"""
CODE5 - HTML 报告生成节点
职责：将 Agent8 生成的 Markdown 报告转化为简约大方的 HTML 页面
输出路径：data/output/{symbol}/{start_date}/{symbol}_{start_date}.html
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from loguru import logger


def markdown_to_html(markdown_text: str) -> str:
    """
    将 Markdown 转换为 HTML（轻量级实现）
    
    支持：
    - 标题 (# ## ### #### ##### ######)
    - 粗体 (**text**)
    - 斜体 (*text*)
    - 代码块 (```code```)
    - 行内代码 (`code`)
    - 表格
    - 列表 (- / 1.)
    - 分隔线 (---)
    - 链接 [text](url)
    - Emoji
    """
    html = markdown_text
    
    # 转义 HTML 特殊字符（但保留我们需要转换的 markdown 语法）
    # html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # 代码块（先处理，避免被其他规则影响）
    def code_block_replacer(match):
        lang = match.group(1) or ''
        code = match.group(2)
        # 转义代码块内的 HTML
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<pre class="code-block"><code class="language-{lang}">{code}</code></pre>'
    
    html = re.sub(r'```(\w*)\n(.*?)```', code_block_replacer, html, flags=re.DOTALL)
    
    # 行内代码
    html = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', html)
    
    # 标题
    html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # 粗体和斜体
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', html)
    
    # 分隔线
    html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)
    
    # 链接
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
    
    # 表格处理
    def table_replacer(match):
        table_text = match.group(0)
        lines = table_text.strip().split('\n')
        
        if len(lines) < 2:
            return table_text
        
        html_table = '<div class="table-container"><table>\n'
        
        # 表头
        header_cells = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
        html_table += '<thead><tr>'
        for cell in header_cells:
            html_table += f'<th>{cell}</th>'
        html_table += '</tr></thead>\n'
        
        # 表体（跳过分隔行）
        html_table += '<tbody>\n'
        for line in lines[2:]:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                html_table += '<tr>'
                for cell in cells:
                    html_table += f'<td>{cell}</td>'
                html_table += '</tr>\n'
        html_table += '</tbody></table></div>'
        
        return html_table
    
    # 匹配表格（以 | 开头的连续行）
    html = re.sub(r'(\|.+\|\n)+', table_replacer, html)
    
    # 无序列表
    def ul_replacer(match):
        items = match.group(0).strip().split('\n')
        html_list = '<ul>\n'
        for item in items:
            item_text = re.sub(r'^[\-\*]\s+', '', item.strip())
            if item_text:
                html_list += f'<li>{item_text}</li>\n'
        html_list += '</ul>'
        return html_list
    
    html = re.sub(r'(^[\-\*]\s+.+\n?)+', ul_replacer, html, flags=re.MULTILINE)
    
    # 有序列表
    def ol_replacer(match):
        items = match.group(0).strip().split('\n')
        html_list = '<ol>\n'
        for item in items:
            item_text = re.sub(r'^\d+\.\s+', '', item.strip())
            if item_text:
                html_list += f'<li>{item_text}</li>\n'
        html_list += '</ol>'
        return html_list
    
    html = re.sub(r'(^\d+\.\s+.+\n?)+', ol_replacer, html, flags=re.MULTILINE)
    
    # 复选框
    html = re.sub(r'\[ \]', '<input type="checkbox" disabled>', html)
    html = re.sub(r'\[x\]', '<input type="checkbox" checked disabled>', html, flags=re.IGNORECASE)
    
    # 段落（将连续的非标签文本包装在 <p> 中）
    lines = html.split('\n')
    result_lines = []
    in_paragraph = False
    
    for line in lines:
        stripped = line.strip()
        # 跳过已经是 HTML 标签的行
        if (stripped.startswith('<') and not stripped.startswith('<input')) or not stripped:
            if in_paragraph:
                result_lines.append('</p>')
                in_paragraph = False
            result_lines.append(line)
        else:
            if not in_paragraph:
                result_lines.append('<p>')
                in_paragraph = True
            result_lines.append(line)
    
    if in_paragraph:
        result_lines.append('</p>')
    
    html = '\n'.join(result_lines)
    
    return html


def get_html_template(symbol: str, content: str, generated_at: str) -> str:
    """
    生成完整的 HTML 页面模板
    
    风格：简约大方，专业金融风格
    """
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} 期权策略分析报告</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --primary-dark: #1d4ed8;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --text-primary: #1f2937;
            --text-secondary: #6b7280;
            --bg-primary: #ffffff;
            --bg-secondary: #f9fafb;
            --border-color: #e5e7eb;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-secondary);
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: var(--bg-primary);
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 40px;
        }}
        
        .header {{
            text-align: center;
            padding-bottom: 24px;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 32px;
        }}
        
        .header h1 {{
            font-size: 28px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 8px;
        }}
        
        .header .meta {{
            font-size: 14px;
            color: var(--text-secondary);
        }}
        
        h1 {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
            margin: 32px 0 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--primary-color);
        }}
        
        h2 {{
            font-size: 20px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 28px 0 14px;
            padding-left: 12px;
            border-left: 4px solid var(--primary-color);
        }}
        
        h3 {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 24px 0 12px;
        }}
        
        h4, h5, h6 {{
            font-size: 16px;
            font-weight: 600;
            color: var(--text-secondary);
            margin: 20px 0 10px;
        }}
        
        p {{
            margin: 12px 0;
            color: var(--text-primary);
        }}
        
        strong {{
            font-weight: 600;
            color: var(--text-primary);
        }}
        
        em {{
            font-style: italic;
        }}
        
        a {{
            color: var(--primary-color);
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .table-container {{
            overflow-x: auto;
            margin: 20px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        
        th {{
            background: var(--bg-secondary);
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
        }}
        
        tr:hover td {{
            background: var(--bg-secondary);
        }}
        
        ul, ol {{
            margin: 16px 0;
            padding-left: 24px;
        }}
        
        li {{
            margin: 8px 0;
            color: var(--text-primary);
        }}
        
        hr {{
            border: none;
            height: 1px;
            background: var(--border-color);
            margin: 32px 0;
        }}
        
        .code-block {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 16px 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
            margin: 16px 0;
        }}
        
        .inline-code {{
            background: var(--bg-secondary);
            color: var(--danger-color);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        input[type="checkbox"] {{
            margin-right: 8px;
            transform: scale(1.1);
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            text-align: center;
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        /* 响应式设计 */
        @media (max-width: 768px) {{
            body {{
                padding: 12px;
            }}
            
            .container {{
                padding: 24px;
            }}
            
            .header h1 {{
                font-size: 22px;
            }}
            
            h1 {{
                font-size: 20px;
            }}
            
            h2 {{
                font-size: 18px;
            }}
            
            table {{
                font-size: 12px;
            }}
            
            th, td {{
                padding: 8px 10px;
            }}
        }}
        
        /* 打印样式 */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
            
            .code-block {{
                background: #f5f5f5;
                color: #333;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {symbol} 期权策略分析报告</h1>
            <div class="meta">
                生成时间: {generated_at} | Powered by Swing Quant Workflow
            </div>
        </div>
        
        <div class="content">
            {content}
        </div>
        
        <div class="footer">
            <p>⚠️ 免责声明：本报告仅供参考，不构成投资建议。期权交易存在风险，请谨慎决策。</p>
            <p>© {datetime.now().year} Swing Quant Workflow</p>
        </div>
    </div>
</body>
</html>'''


def main(
    report_markdown: str,
    symbol: str,
    start_date: str = None,
    output_dir: str = "data/output",
    **env_vars
) -> Dict[str, Any]:
    """
    HTML 报告生成节点入口
    
    Args:
        report_markdown: Agent8 生成的 Markdown 报告
        symbol: 股票代码
        start_date: 分析开始日期（YYYYMMDD），默认今天
        output_dir: 输出目录根路径
        **env_vars: 环境变量
        
    Returns:
        {
            "status": "success" | "error",
            "html_path": str,  # HTML 文件路径
            "message": str
        }
    """
    try:
        # 参数验证
        if not symbol or symbol.upper() == "UNKNOWN":
            return {
                "status": "error",
                "html_path": None,
                "message": f"无效的 symbol: '{symbol}'"
            }
        
        symbol = symbol.upper()
        
        if not start_date:
            start_date = datetime.now().strftime("%Y%m%d")
        
        # 构造输出路径：data/output/{symbol}/{start_date}/{symbol}_{start_date}.html
        output_path = Path(output_dir) / symbol / start_date
        output_path.mkdir(parents=True, exist_ok=True)
        
        html_filename = f"{symbol}_{start_date}.html"
        html_filepath = output_path / html_filename
        
        # 转换 Markdown 到 HTML
        html_content = markdown_to_html(report_markdown)
        
        # 生成完整 HTML 页面
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_html = get_html_template(symbol, html_content, generated_at)
        
        # 写入文件
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        logger.success(f"✅ HTML 报告已生成: {html_filepath}")
        logger.info(f"   文件大小: {html_filepath.stat().st_size / 1024:.2f} KB")
        
        return {
            "status": "success",
            "html_path": str(html_filepath),
            "message": f"HTML 报告已生成: {html_filepath}"
        }
        
    except Exception as e:
        logger.error(f"❌ HTML 报告生成失败: {str(e)}")
        return {
            "status": "error",
            "html_path": None,
            "message": f"HTML 报告生成失败: {str(e)}"
        }