# RQQ CLI 使用手册

目标：让人和外部 LLM/自动化系统都能用稳定、短、可复制的命令完成米筐取数和业务表生成。

## 基本约定

开发环境统一使用：

```bash
uv run rqq ...
```

默认输出是 markdown（表格类结果用 GFM 表格，元数据用分节 + key-value），人和 LLM 都好读，调用时不用额外加格式参数。需要机器解析时再显式指定 `--format json`，需要表格落盘时用 `--format csv`。本手册里的示例仍带 `--format json`，只是为了展示可解析结构，不是必须。

写文件时用：

```bash
--output path/to/file.json
```

日期统一使用 ISO 格式：

```text
YYYY-MM-DD
```

A 股和指数代码使用 RQData `order_book_id`：

```text
000001.XSHE
600000.XSHG
000300.XSHG
```

基金插件常用基金代码不带交易所后缀，例如：

```text
000003
```

## 一次拿到全部参考

LLM / 自动化脚本的第一步：用 `rqq help`（别名 `rqq data help`）一次性拿到所有数据命令的用途、参数、必填项和默认值，省去逐个 `list` / `describe` 的往返。

```bash
uv run rqq help
uv run rqq help --format json
```

输出分四块：`commands`（命令清单 + 用法示例）、`datasets`（每个数据集的 function / required / optional / defaults）、`scenarios`、`business_datasets`。

## 命令选择

优先按这个决策树使用：

```text
不知道有哪些命令/参数             -> rqq help
想知道有什么数据                 -> rqq data list
想看某个数据怎么传参数             -> rqq data describe <dataset>
想取一个原子数据集                 -> rqq data get <dataset>
想生成一个业务拼装表               -> rqq data build <business-dataset>
想生成一个模块的多张原始表           -> rqq data generate <scenario>
想调用尚未封装的 rqdatac 函数        -> rqq data call <function>
```

`data get` 是 `data fetch` 的短别名。`data build` 是 `data business build` 的短别名。

## 探索命令

列出所有数据集：

```bash
uv run rqq data list --format json
```

按类别列出：

```bash
uv run rqq data list --category market --format json
uv run rqq data list --category financial --format json
uv run rqq data list --category fund --format json
uv run rqq data list --category consensus --format json
uv run rqq data list --category index --format json
uv run rqq data list --category news --format json
```

查看数据集参数：

```bash
uv run rqq data describe price --format json
uv run rqq data describe fund-holdings --format json
uv run rqq data describe consensus-price --format json
uv run rqq data describe index-components --format json
```

查看业务表：

```bash
uv run rqq data business list --format json
uv run rqq data business describe research-monitor-snapshot --format json
```

## 原子数据取数

行情：

```bash
uv run rqq data get price \
  --ids 000001.XSHE \
  --start 2024-01-02 \
  --end 2024-01-03 \
  --fields open,close,volume \
  --format json
```

财务 PIT：

```bash
uv run rqq data get financials-pit \
  --ids 000001.XSHE \
  --start-quarter 2023q1 \
  --end-quarter 2023q4 \
  --fields revenue,net_profit,gross_profit,total_rnd \
  --format json
```

因子：

```bash
uv run rqq data get factor \
  --ids 000001.XSHE \
  --factor gross_profit_margin_ttm,net_profit_margin_ttm,pe_ratio_ttm \
  --start 2024-01-02 \
  --end 2024-01-03 \
  --format json
```

公告和调研：

```bash
uv run rqq data get announcement --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31 --format json
uv run rqq data get investor-qa --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31 --format json
uv run rqq data get investor-ra --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31 --format json
```

资金流、陆股通、两融：

```bash
uv run rqq data get capital-flow --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03 --format json
uv run rqq data get stock-connect --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03 --format json
uv run rqq data get securities-margin --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03 --format json
```

基金：

```bash
uv run rqq data get fund-holdings --ids 000003 --date 2023-12-31 --format json
uv run rqq data get fund-stock-change --ids 000003 --start 2023-01-01 --end 2024-01-03 --format json
uv run rqq data get fund-asset-allocation --ids 000003 --date 2023-12-31 --format json
```

一致预期：

```bash
uv run rqq data get consensus-price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03 --format json
uv run rqq data get consensus-comp-indicators --ids 000001.XSHE --start 2024-01-02 --end 2024-01-31 --format json
uv run rqq data get consensus-indicator --ids 000001.XSHE --fiscal-year 2024 --format json
```

指数：

```bash
uv run rqq data get index-components --ids 000300.XSHG --date 2024-01-03 --format json
uv run rqq data get index-weights --ids 000300.XSHG --date 2024-01-03 --format json
uv run rqq data get index-indicator --ids 000300.XSHG --start 2024-01-02 --end 2024-01-03 --format json
```

新闻：

```bash
uv run rqq data get current-news --n 3 --channels a-stock --format json
```

## 业务表生成

业务表用于把多个原子数据源拼成一张稳定表。建议 LLM 优先用业务表，而不是自己手动拼多个接口。

列出业务表：

```bash
uv run rqq data business list --format json
```

生成公司质量快照：

```bash
uv run rqq data build company-quality-snapshot \
  --ids 000001.XSHE 600000.XSHG \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --start-quarter 2023q1 \
  --end-quarter 2023q4 \
  --output-dir outputs/business \
  --file-format csv \
  --format json
```

生成研究监控快照：

```bash
uv run rqq data build research-monitor-snapshot \
  --ids 000001.XSHE 600000.XSHG \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --output-dir outputs/business \
  --file-format csv \
  --format json
```

生成基金持仓快照：

```bash
uv run rqq data build fund-position-snapshot \
  --ids 000003 \
  --date 2023-12-31 \
  --start 2024-01-02 \
  --end 2024-01-03 \
  --output-dir outputs/business \
  --file-format csv \
  --format json
```

生成一致预期关注快照：

```bash
uv run rqq data build consensus-attention-snapshot \
  --ids 000001.XSHE \
  --start 2024-01-02 \
  --end 2024-01-31 \
  --fiscal-year 2024 \
  --output-dir outputs/business \
  --file-format csv \
  --format json
```

生成指数相对强弱输入表：

```bash
uv run rqq data build index-relative-strength-snapshot \
  --ids 000300.XSHG \
  --date 2024-01-03 \
  --start 2024-01-02 \
  --end 2024-01-03 \
  --output-dir outputs/business \
  --file-format csv \
  --format json
```

生成新闻事件快照：

```bash
uv run rqq data build event-news-snapshot \
  --n 3 \
  --channels a-stock \
  --output-dir outputs/business \
  --file-format csv \
  --format json
```

业务表输出规则：

- 标准输出返回 manifest。
- 主表写到 `outputs/business/<business-dataset>/<output_table>.<file-format>`。
- 缺数据组件写入 manifest 的 `skipped`。
- 加 `--strict` 时，组件缺参数会直接失败。
- 加 `--write-components` 时，同时写出标准化组件中间表。

## 场景原始数据生成

如果需要保留模块下的多张原始表，用 `data generate`：

```bash
uv run rqq data scenario list --format json
uv run rqq data scenario describe company-quality --format json
```

生成公司质量模块原始表：

```bash
uv run rqq data generate company-quality \
  --ids 000001.XSHE \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --start-quarter 2023q1 \
  --end-quarter 2023q4 \
  --output-dir outputs/data \
  --file-format csv \
  --format json
```

## 通用参数

常用参数：

```text
--ids                 股票/指数/基金代码，支持多个
--start               开始日期
--end                 结束日期
--date                单日日期
--fields              字段列表，逗号分隔
--factor              因子列表，逗号分隔
--start-quarter       起始财报季度，例如 2023q1
--end-quarter         结束财报季度，例如 2023q4
--fiscal-year         财年，例如 2024
--n                   数量，比如新闻条数
--channels            新闻频道，逗号分隔
--params              JSON 对象，传额外参数
--param KEY=VALUE     额外参数，可重复，VALUE 会尽量按 JSON 解析
--format json|csv|table
--output path
```

## 外部 LLM 调用规范

外部 LLM/自动化系统调用本 CLI 时，建议固定使用 JSON 输出：

```bash
uv run rqq data get <dataset> ... --format json
uv run rqq data build <business-dataset> ... --format json
```

调用前先看 schema：

```bash
uv run rqq data describe <dataset> --format json
uv run rqq data business describe <business-dataset> --format json
```

当不确定参数时，先 plan：

```bash
uv run rqq data business plan <business-dataset> ... --format json
```

错误处理：

- 参数或业务错误退出码为 `2`。
- 未预期异常退出码为 `1`。
- JSON 输出不包含已知 RQData warning。

## 安全注意

`uv run rqq data info` 和 `uv run rqq license info` 都会对 license 打码；但 license key 本身（存在 `~/.rqq/credentials`、或你贴进 `rqq license` 的）仍要保密，不要提交到仓库或发送给模型、日志系统或公开渠道。
