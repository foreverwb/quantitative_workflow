# Swing Quant Local - 美股期权量化分析系统

从 Dify Workflow 转换的本地独立运行程序，支持单标的分析和批量处理。

## ✨ 新增功能

### 1. 📁 批量分析（文件夹上传）
支持一次性分析 10+ 个标的，自动按股票代码分组处理。

### 2. 🎛️ 灵活模型配置
完全兼容 Dify 模型配置界面，支持：
- 模型显示名称
- API Key 和 Endpoint
- 上下文长度和最大 token
- 模型能力开关（Vision、Structured Output、Function Calling 等）
- 不同 Agent 使用不同模型

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 API Key
编辑 `config.yaml`:
```yaml
llm:
  provider: "openai"
  api_key: "sk-your-api-key"
  base_url: "https://api.openai.com/v1"

models:
  data_validator: "gpt-4o"    # 需要 Vision 能力
  technical: "gpt-4o"         # 需要 Vision 能力
  scenario: "gpt-4o"
```

### 3. 运行示例

#### 🎯 单标的分析
```bash
# 生成命令清单
python main.py "AAPL"

# 完整分析（上传数据）
python main.py "AAPL数据分析" --files chart1.png chart2.png
```

#### 📦 批量分析（推荐）
```bash
# 方式 1: 上传整个文件夹
python main.py "批量分析" --folder data/charts/

# 方式 2: 使用通配符
python main.py "批量分析" --files data/*.png

# 方式 3: 指定输出目录
python main.py "批量分析" --folder data/ --output-dir reports/2025-01/
```

#### 文件命名规范
批量分析会自动从文件名提取股票代码，支持以下格式：
- `AAPL_gexr_7d.png`
- `NVDA-skew-14d.png`
- `TSLA_data_20250115.png`
- `QQQ_net_gamma.png`

确保文件名包含大写股票代码（1-5个字母）。

## 📊 批量分析输出

批量分析会生成：
1. **汇总报告** (`reports/batch_summary.md`):
   - 成功/失败统计
   - 所有标的推荐策略对比表
   - 失败标的列表

2. **个股详细报告** (`reports/AAPL_report.md`, `reports/NVDA_report.md` ...):
   - 每个成功标的的完整分析报告

示例输出：
```
=== 批量分析完成 ===
总标的数: 12
成功: 10 | 失败: 2
失败标的: XYZ, ABC

汇总报告: reports/batch_summary.md
  - AAPL: reports/AAPL_report.md
  - NVDA: reports/NVDA_report.md
  - TSLA: reports/TSLA_report.md
  ...
```

## 🎛️ 模型配置详解

### 基础配置
```yaml
llm:
  provider: "openai"              # 提供商
  api_key: "your-key"             # API Key
  base_url: "https://api.openai.com/v1"  # API Endpoint
```

### 模型选择（各 Agent 独立配置）
```yaml
models:
  router: "gpt-4o-mini"           # 路由判断（简单任务）
  data_validator: "gpt-4o"        # 数据校验（需 Vision）
  technical: "gpt-4o"             # 技术分析（需 Vision）
  scenario: "gpt-4o"              # 剧本分析
  strategy: "gpt-4o"              # 策略生成
  comparison: "gpt-4o"            # 策略对比
  report: "gpt-4o"                # 报告生成
```

### 模型参数
```yaml
model_params:
  temperature: 0.5                # 创造性 (0-1)
  max_tokens: 4096                # 最大输出 token
  context_length: 4096            # 上下文长度
  top_p: 1.0
  frequency_penalty: 0.0
  presence_penalty: 0.0
```

### 模型能力开关
```yaml
model_capabilities:
  vision_support: true            # Vision 支持
  structured_output: true         # 结构化输出
  function_calling: "tool_call"   # 工具调用模式
  stream_function_calling: true   # 流式工具调用
  agent_thought: false            # Agent Thought（链式思考）
```

### 支持的提供商
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`
- **Anthropic**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
- **DeepSeek**: `deepseek-chat`, `deepseek-coder`
- **自定义**: 任何兼容 OpenAI API 的服务

### 混合使用示例
```yaml
# 成本优化策略：重要任务用大模型，简单任务用小模型
models:
  router: "gpt-4o-mini"           # 简单路由
  command_gen: "gpt-4o-mini"      # 命令生成
  data_validator: "gpt-4o"        # 数据校验（复杂）
  technical: "gpt-4o"             # 技术分析（复杂）
  scenario: "claude-3-opus"       # 剧本推演（高级推理）
  strategy: "gpt-4o"              # 策略生成
  comparison: "gpt-4o"            # 策略对比
  report: "gpt-4o-mini"           # 报告生成
```

## 项目结构

```
swing_quant_local/
├── main.py                    # 主程序入口（支持批量分析）
├── config.py                  # 配置管理（增强模型配置）
├── config.yaml                # 用户配置文件（Dify 风格）
├── agents/                    # Agent 实现
│   ├── router.py
│   ├── command_generator.py
│   ├── data_validator.py
│   ├── technical_analyzer.py
│   ├── scenario_analyzer.py
│   ├── strategy_generator.py
│   ├── comparison.py
│   └── report_generator.py
├── calculators/               # 计算引擎
│   ├── event_detector.py
│   ├── scoring_engine.py
│   ├── strategy_calculator.py
│   └── ranking_engine.py
├── models/
│   └── llm_client.py         # LLM 调用封装
├── utils/
│   ├── logger.py
│   └── file_handler.py
├── logs/                      # 日志目录
├── reports/                   # 报告输出目录
│   ├── batch_summary.md      # 批量汇总报告
│   ├── AAPL_report.md        # 个股报告
│   └── ...
└── requirements.txt
```

## 功能特性

1. **事件检测**: 自动检测 FOMC、OPEX、财报等重大事件
2. **数据校验**: 验证上传数据完整性，生成补齐指引
3. **技术面分析**: 解析图表，计算技术指标评分
4. **四维评分**: Gamma Regime、破墙可能、方向一致、IV动态
5. **剧本分析**: 智能推演市场剧本和概率
6. **策略生成**: 自动生成保守/均衡/进取三种策略
7. **策略对比**: 计算 EV、RAR、Pw，智能排序推荐
8. **报告生成**: 输出完整 Markdown 分析报告
9. **📁 批量处理**: 一次性分析 10+ 个标的
10. **🎛️ 灵活配置**: 完全兼容 Dify 模型配置界面

## 高级配置

### 批量分析优化
```yaml
batch_analysis:
  max_workers: 3                  # 并行处理数量
  retry_attempts: 2               # 失败重试次数
  timeout_per_symbol: 300         # 单标的超时（秒）
  generate_individual_reports: true
  continue_on_error: true         # 失败时继续处理其他标的
```

### 成本优化
```yaml
# 使用小模型处理简单任务
models:
  router: "gpt-4o-mini"           # $0.15/1M tokens
  command_gen: "gpt-4o-mini"      # $0.15/1M tokens
  data_validator: "gpt-4o"        # $2.5/1M tokens（需要 Vision）
  scenario: "gpt-4o"              # $2.5/1M tokens（需要高级推理）
  report: "gpt-4o-mini"           # $0.15/1M tokens

# 预计成本：单标的约 $0.05-0.15，批量分析 10 个约 $0.50-1.50
```

## 调试模式

```bash
# 启用详细日志
python main.py "TSLA" --files data.png 2>&1 | tee debug.log

# 查看日志文件
tail -f logs/swing_quant.log
```

## 注意事项

1. **API 成本**: 每次完整分析会调用多个 LLM，注意 token 消耗
2. **图片质量**: 确保上传的图表清晰，包含所有必需信息
3. **Vision 能力**: `gpt-4o-mini` 不支持 Vision，数据校验和技术分析必须用 `gpt-4o`
4. **批量分析**: 建议使用 `max_workers=3` 避免 API 限流
5. **文件命名**: 批量分析要求文件名包含股票代码

## 故障排除

### Vision 模型错误
```
Error: This model does not support vision
```
**解决**: 将 `data_validator` 和 `technical` 改为 `gpt-4o`

### API 限流
```
Error: Rate limit exceeded
```
**解决**: 降低 `batch_analysis.max_workers` 或增加延迟

### 文件未识别
```
Warning: 无法从文件名提取股票代码
```