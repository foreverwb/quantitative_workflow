"""
Refresh 命令处理器
处理盘中快照刷新
支持两种模式：
1. 图片文件夹模式 (-f)：从图片提取数据
2. 输入文件模式 (-i)：从JSON文件读取数据
"""

import sys
from pathlib import Path
from typing import Dict, Any
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .base import BaseCommand


class RefreshCommand(BaseCommand):
    """Refresh 命令处理器"""
    
    def execute(
        self,
        symbol: str,
        folder: str = None,
        input_file: str = None,
        cache: str = None,
        **kwargs  # 接收 market_params, dyn_params
    ) -> Dict[str, Any]:
        """
        执行刷新快照
        
        Args:
            symbol: 股票代码
            folder: 数据文件夹路径 (与 input_file 互斥)
            input_file: 输入JSON文件路径 (与 folder 互斥)
            cache: 缓存文件名（必需）
            **kwargs: 额外参数
                - market_params: 市场参数 (vix, ivr, iv30, hv20)
                - dyn_params: 动态参数 (dyn_strikes, scenario, ...)
                
        Returns:
            执行结果字典
        """
        # 提取市场参数
        market_params = kwargs.get('market_params')
        dyn_params = kwargs.get('dyn_params')
        
        # ============= 1. 参数验证 =============
        
        # 1.1 验证股票代码
        is_valid, result = self.validate_symbol(symbol)
        if not is_valid:
            self.print_error(result)
            sys.exit(1)
        
        # 1.2 验证缓存文件（必需）
        if not cache:
            self.print_error("refresh 模式必须指定 --cache 参数")
            self._print_usage_hint(symbol)
            sys.exit(1)
        
        is_valid, error_msg, cache_info = self.validate_cache_file(cache, symbol)
        if not is_valid:
            self.print_error("缓存文件验证失败")
            self.console.print(f"[red]   {error_msg}[/red]")
            self._print_troubleshooting(symbol, cache)
            sys.exit(1)
        
        # 1.3 验证 source_target 完整性
        if not cache_info["has_source_target"]:
            self.print_error("缓存文件缺少初始分析数据 (source_target)")
            self._print_source_target_missing(cache_info, symbol, cache)
            sys.exit(1)
        
        # 1.4 显示缓存信息
        self._print_cache_info(cache_info)
        
        # ============= 2. 根据模式执行 =============
        
        if input_file:
            # 输入文件模式
            return self._execute_input_file_mode(
                symbol=symbol,
                input_file=input_file,
                cache=cache,
                market_params=market_params,
                dyn_params=dyn_params
            )
        else:
            # 图片文件夹模式
            return self._execute_folder_mode(
                symbol=symbol,
                folder=folder,
                cache=cache,
                market_params=market_params,
                dyn_params=dyn_params
            )
    
    def _execute_folder_mode(
        self,
        symbol: str,
        folder: str,
        cache: str,
        market_params: Dict,
        dyn_params: Dict
    ) -> Dict[str, Any]:
        """图片文件夹模式"""
        # 验证文件夹
        folder_path = Path(folder)
        is_valid, msg = self.validate_folder(folder_path)
        if not is_valid:
            self.print_error(msg)
            sys.exit(1)
        
        # 打印标题
        self.console.print(Panel.fit(
            f"[bold cyan]📸 盘中快照: {symbol.upper()}[/bold cyan]\n"
            f"[dim]模式: 图片文件夹 | Agent3 + 计算引擎[/dim]",
            border_style="cyan"
        ))
        
        self.console.print(f"[dim]📊 {msg}[/dim]")
        
        # 执行刷新
        engine = self.create_engine(cache_file=cache)
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("正在刷新数据...", total=None)
                
                result = engine.run(
                    symbol=symbol.upper(),
                    data_folder=folder_path,
                    mode="refresh",
                    market_params=market_params,
                    dyn_params=dyn_params
                )
                
                progress.update(task, completed=True)
            
            return self._handle_result(result, symbol)
        
        except Exception as e:
            self.print_error(str(e))
            sys.exit(1)
    
    def _execute_input_file_mode(
        self,
        symbol: str,
        input_file: str,
        cache: str,
        market_params: Dict,
        dyn_params: Dict
    ) -> Dict[str, Any]:
        """输入文件模式"""
        from code_nodes.code_input_calc import InputFileCalculator
        from core.workflow import CacheManager
        from core.workflow.drift_engine import DriftEngine
        from code_nodes.code5_report_html import main as html_gen_main
        
        # 验证输入文件
        input_path = Path(input_file)
        if not input_path.exists():
            self.print_error(f"输入文件不存在: {input_file}")
            sys.exit(1)
        
        # 打印标题
        self.console.print(Panel.fit(
            f"[bold cyan]📸 盘中快照: {symbol.upper()}[/bold cyan]\n"
            f"[dim]模式: 输入文件 | 计算引擎[/dim]",
            border_style="cyan"
        ))
        
        self.console.print(f"[dim]📄 输入文件: {input_file}[/dim]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("正在处理输入文件...", total=None)
                
                # Step 1: 加载并计算 cluster_strength_ratio
                calculator = InputFileCalculator(input_file)
                calculator.load()
                calc_result = calculator.calculate()
                
                progress.update(task, description="提取目标数据...")
                
                # Step 2: 从 spec.targets 提取已计算好的数据
                # 输入文件的 spec.targets 已包含完整的目标数据结构
                full_data = calculator.data
                spec_targets = full_data.get("spec", {}).get("targets", {})
                
                if not spec_targets:
                    self.print_error("输入文件缺少 spec.targets 数据")
                    sys.exit(1)
                
                # 确保 cluster_strength_ratio 已更新到 spec_targets
                if "gamma_metrics" not in spec_targets:
                    spec_targets["gamma_metrics"] = {}
                spec_targets["gamma_metrics"]["cluster_strength_ratio"] = calc_result["cluster_strength_ratio"]
                
                # 补充计算 em1_dollar (如果不存在)
                if not spec_targets.get("em1_dollar"):
                    spot_price = spec_targets.get("spot_price")
                    atm_iv = spec_targets.get("atm_iv", {})
                    iv30 = atm_iv.get("iv_30d") or atm_iv.get("iv30") or market_params.get("iv30")
                    
                    if spot_price and iv30:
                        import math
                        # 简化计算: em1_dollar ≈ spot * iv30% / sqrt(52) (周度)
                        em1_dollar = spot_price * (float(iv30) / 100) / math.sqrt(52)
                        spec_targets["em1_dollar"] = round(em1_dollar, 2)
                        self.console.print(f"[dim]   EM1$: ${spec_targets['em1_dollar']} (计算值)[/dim]")
                
                # 构建 calculated_result (与 field_calculator 输出格式一致)
                calculated_result = {
                    "data_status": "ready",
                    "targets": spec_targets,
                    # 保留元数据
                    "metadata": full_data.get("metadata", {}),
                }
                
                # 打印关键数据
                spot_price = spec_targets.get("spot_price", "N/A")
                gamma_metrics = spec_targets.get("gamma_metrics", {})
                vol_trigger = gamma_metrics.get("vol_trigger", "N/A")
                
                self.console.print(f"[dim]   Spot: ${spot_price}, Vol Trigger: ${vol_trigger}[/dim]")
                self.console.print(f"[dim]   cluster_strength_ratio: {calc_result['cluster_strength_ratio']} ({calc_result['tier']})[/dim]")
                
                progress.update(task, description="分析结构漂移...")
                
                # Step 3: 加载基准数据并分析漂移
                cache_manager = CacheManager()
                last_snapshot = cache_manager.load_latest_greeks_snapshot(symbol)
                if not last_snapshot:
                    full_analysis = cache_manager.load_analysis(symbol)
                    last_snapshot = full_analysis.get("source_target", {}) if full_analysis else {}
                
                drift_engine = DriftEngine()
                drift_report = drift_engine.analyze(last_snapshot, calculated_result)
                
                progress.update(task, description="保存快照...")
                
                # Step 4: 保存快照
                calculated_result["drift_report"] = drift_report
                snapshot_result = cache_manager.save_greeks_snapshot(
                    symbol=symbol,
                    data=calculated_result,
                    note=f"监控: {drift_report.get('summary', '')}",
                    is_initial=False,
                    cache_file_name=cache
                )
                
                progress.update(task, description="生成报告...")
                
                # Step 5: 生成聚合 Dashboard HTML
                all_history = cache_manager.get_all_snapshots(symbol)
                html_result = html_gen_main(
                    mode="dashboard",
                    symbol=symbol,
                    all_history=all_history,
                    output_dir="data/output"
                )
                
                progress.update(task, completed=True)
            
            # 显示漂移报告
            self._print_drift_dashboard(drift_report)
            
            if html_result.get("status") == "success":
                from utils.console_printer import print_report_link
                print_report_link(html_result['html_path'], symbol)
            
            return {
                "status": "success",
                "snapshot": snapshot_result.get("snapshot"),
                "drift_report": drift_report
            }
        
        except Exception as e:
            import traceback
            self.print_error(f"处理失败: {str(e)}")
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)
    
    def _print_drift_dashboard(self, report: Dict):
        """打印漂移分析仪表盘"""
        from rich.table import Table
        
        print("\n")
        self.console.print(Panel(
            f"[bold]🛡️ 监控建议 (Drift Engine)[/bold]\n"
            f"状态: {report['summary']}",
            style="cyan", border_style="cyan"
        ))
        
        if report.get("actions"):
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
        
        if report.get("alerts"):
            self.console.print("\n[bold red]风险警示:[/bold red]")
            for alert in report["alerts"]:
                self.console.print(f"  • {alert}")
        print("\n")
    
    # ============= 私有辅助方法 =============
    
    def _print_usage_hint(self, symbol: str):
        """打印使用提示"""
        self.console.print(f"\n[yellow]💡 提示:[/yellow]")
        self.console.print(f"[cyan]   python app.py refresh {symbol.upper()} -f <folder> --cache {symbol.upper()}_20251129.json[/cyan]")
        self.console.print(f"[cyan]   python app.py refresh {symbol.upper()} -i <input.json> --cache {symbol.upper()}_20251129.json[/cyan]")
        self.console.print(f"\n[dim]提示: 可用的缓存文件位于 data/output/{symbol.upper()}/ 目录下[/dim]")
    
    def _print_troubleshooting(self, symbol: str, cache: str):
        """打印故障排查信息"""
        self.console.print(f"\n[yellow]💡 提示:[/yellow]")
        self.console.print(f"[yellow]   1. 确保文件名格式正确: {{SYMBOL}}_{{YYYYMMDD}}.json[/yellow]")
        self.console.print(f"[yellow]   2. 确保文件存在于: data/output/{symbol.upper()}/[/yellow]")
        self.console.print(f"[yellow]   3. 使用 'python app.py analyze -s {symbol.upper()} -f <folder>' 先创建初始分析[/yellow]")
    
    def _print_source_target_missing(self, cache_info: Dict, symbol: str, cache: str):
        """打印 source_target 缺失信息"""
        self.console.print(f"\n[yellow]⚠️ 当前缓存状态:[/yellow]")
        self.console.print(f"[yellow]   • 文件: {cache}[/yellow]")
        self.console.print(f"[yellow]   • 快照数量: {cache_info['snapshot_count']}[/yellow]")
        self.console.print(f"[yellow]   • source_target: null[/yellow]")
        
        self.console.print(f"\n[yellow]💡 解决方案:[/yellow]")
        self.console.print(f"[yellow]   必须先执行完整分析以生成 source_target:[/yellow]")
        self.console.print(f"[cyan]   python app.py analyze -s {symbol.upper()} -f <初始数据文件夹> --cache {cache}[/cyan]")
        
        self.console.print(f"\n[dim]   说明: refresh 模式用于盘中更新，必须在完整分析后使用[/dim]")
    
    def _print_cache_info(self, cache_info: Dict):
        """打印缓存验证信息"""
        self.console.print(f"\n[green]✅ 缓存文件验证通过[/green]")
        self.console.print(f"[dim]   股票代码: {cache_info['symbol']}[/dim]")
        self.console.print(f"[dim]   分析日期: {cache_info['start_date']}[/dim]")
        self.console.print(f"[dim]   已有快照: {cache_info['snapshot_count']} 个[/dim]")
        self.console.print(f"[dim]   source_target: 完整[/dim]")
    
    def _handle_result(self, result: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """处理刷新结果"""
        status = result.get("status")
        
        if status != "success":
            self.print_error(f"刷新失败: {result.get('message', '未知错误')}")
            return result
        
        # 显示成功信息
        self.console.print("\n[green]✅ 快照已保存![/green]\n")
        
        # 提取快照摘要
        snapshot = result.get("snapshot", {})
        
        self.console.print(Panel(
            self._format_snapshot_summary(snapshot),
            title="📊 快照摘要",
            border_style="green"
        ))
        
        # 显示变化
        changes = snapshot.get("changes")
        if changes:
            self.console.print("\n[yellow]📈 数据变化:[/yellow]")
            for field, change in changes.items():
                emoji = self._get_change_emoji(change.get("change_pct", 0))
                pct_str = f" ({change['change_pct']:+.2f}%)" if "change_pct" in change else ""
                self.console.print(f"  {emoji} {field}: {change['old']} → {change['new']}{pct_str}")
        else:
            self.console.print("\n[dim]ℹ️ 首次快照，无历史对比[/dim]")
        
        # 提示查看历史
        self.console.print(f"\n[dim]💡 查看历史快照: python app.py history -s {symbol.upper()}[/dim]")
        
        return result
    
    def _format_snapshot_summary(self, snapshot: Dict) -> str:
        """格式化快照摘要"""
        snapshot_id = snapshot.get("snapshot_id", "N/A")
        timestamp = snapshot.get("timestamp", "")[:19]
        
        # 提取 targets 数据
        targets = snapshot.get("targets", {})
        spot_price = targets.get("spot_price", "N/A")
        em1_dollar = targets.get("em1_dollar", "N/A")
        
        gamma_metrics = targets.get("gamma_metrics", {})
        vol_trigger = gamma_metrics.get("vol_trigger", "N/A")
        spot_vs_trigger = gamma_metrics.get("spot_vs_trigger", "N/A")
        
        return (
            f"[bold]快照 #{snapshot_id}[/bold]\n"
            f"时间: {timestamp}\n"
            f"现价: ${spot_price}\n"
            f"EM1$: ${em1_dollar}\n"
            f"Vol Trigger: ${vol_trigger}\n"
            f"状态: {spot_vs_trigger}"
        )
    
    def _get_change_emoji(self, change_pct: float) -> str:
        """根据变化百分比返回表情符号"""
        if change_pct > 0:
            return "🔺"
        elif change_pct < 0:
            return "🔻"
        else:
            return "➡️"