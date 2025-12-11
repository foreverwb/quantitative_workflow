"""
Refresh 模式处理器 (重构版 v3.0)
架构：控制器 (Controller) 模式
职责：
1. 编排流程：扫描 -> 解析 -> 计算 -> 加载历史 -> 分析差异 -> 保存 -> 报告
2. 依赖注入：调用 DriftEngine 处理核心逻辑
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from rich.panel import Panel
from rich.table import Table
from loguru import logger

from .full_analysis import FullAnalysisMode
from code_nodes.field_calculator import main as calculator_main
from code_nodes.code5_report_html import main as html_gen_main
# 引入新引擎
from core.workflow.drift_engine import DriftEngine

class RefreshMode(FullAnalysisMode):
    """刷新快照模式控制器"""
    
    def __init__(self, engine):
        super().__init__(engine)
        self.drift_engine = DriftEngine() # 初始化引擎
    
    def execute(
        self, 
        symbol: str, 
        data_folder: Path,
        state: Dict[str, Any],
        market_params: Dict = None,
        dyn_params: Dict = None
    ) -> Dict[str, Any]:
        logger.info(f"📸 [Refresh] 开始监控 {symbol} (Engine: v3.0)")
        
        try:
            # 1. 扫描与解析 (I/O)
            images = self.scan_images(data_folder)
            if not images:
                return {"status": "error", "message": "未找到图片"}
            
            logger.info("🔍 解析最新图表数据...")
            agent3_result = self._run_agent3(symbol, images)
            
            # 2. 计算衍生数据
            calculated_result = self._run_calculator_for_refresh(agent3_result, symbol)
            if calculated_result.get("data_status") != "ready":
                return {"status": "error", "message": "数据不完整，无法监控"}
            
            # 3. 加载基准数据 (Rolling Comparison)
            last_snapshot = self.cache_manager.load_latest_greeks_snapshot(symbol)
            if not last_snapshot:
                full_analysis = self.cache_manager.load_analysis(symbol)
                last_snapshot = full_analysis.get("source_target", {}) if full_analysis else {}

            # 4. [核心] 调用引擎分析差异
            drift_report = self.drift_engine.analyze(last_snapshot, calculated_result)
            
            # 5. 保存快照
            calculated_result["drift_report"] = drift_report
            snapshot_result = self.cache_manager.save_greeks_snapshot(
                symbol=symbol,
                data=calculated_result,
                note=f"监控: {drift_report.get('summary', '')}",
                is_initial=False,
                cache_file_name=self.engine.cache_file
            )
            
            # 6. 生成聚合 Dashboard HTML
            all_history = self.cache_manager.get_all_snapshots(symbol)
            html_result = html_gen_main(
                mode="dashboard",
                symbol=symbol,
                all_history=all_history,
                output_dir="data/output"
            )
            
            # 7. 终端展示
            self._print_monitoring_dashboard(drift_report)
            if html_result.get("status") == "success":
                logger.success(f"📄 监控仪表盘已更新: {html_result['html_path']}")
            
            return {
                "status": "success", 
                "snapshot": snapshot_result.get("snapshot"),
                "drift_report": drift_report
            }
            
        except Exception as e:
            logger.exception("Refresh 流程异常")
            return {"status": "error", "message": str(e)}

    def _print_monitoring_dashboard(self, report: Dict):
        """打印控制台仪表盘 (UI Logic)"""
        print("\n")
        self.console.print(Panel(
            f"[bold]🛡️ 监控建议 (Drift Engine)[/bold]\n"
            f"状态: {report['summary']}",
            style="cyan", border_style="cyan"
        ))
        
        if report["actions"]:
            table = Table(title="操作指令", show_header=True, header_style="bold magenta")
            table.add_column("方向", style="dim", width=8)
            table.add_column("动作", style="bold", width=12)
            table.add_column("触发逻辑")
            
            for action in report["actions"]:
                color = "red" if action['type'] in ['stop_loss', 'exit', 'clear_position', 'tighten_stop'] else "green" if action['type'] == 'take_profit' else "yellow"
                table.add_row(
                    action['side'].upper(),
                    f"[{color}]{action['type'].upper()}[/{color}]",
                    action['reason']
                )
            self.console.print(table)
        else:
            self.console.print("[dim]   未触发关键风控阈值，维持原策略[/dim]")
        
        if report["alerts"]:
            self.console.print("\n[bold red]风险警示:[/bold red]")
            for alert in report["alerts"]:
                self.console.print(f"  • {alert}")
        print("\n")

    def _run_calculator_for_refresh(self, agent3_result: Dict, symbol: str) -> Dict:
        """调用计算节点"""
        calculator_input = {"result": agent3_result}
        try:
            result = self.agent_executor.execute_code_node(
                node_name="Calculator",
                func=calculator_main,
                description="计算 Refresh 衍生字段",
                aggregated_data=calculator_input,
                symbol=symbol,
                **self.env_vars
            )
            return result
        except Exception as e:
            return {"data_status": "error", "error_message": str(e)}