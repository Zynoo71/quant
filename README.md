# rqsdk_quant

> 面向米筐 RQSDK/RQData 的量化数据 CLI —— 一个稳定的 `rqq` 命令入口，让人和外部 LLM/自动化系统都能稳定地取数、聚合、生成业务表。当前覆盖数据层；因子、回测、交易为后续。

## 特性

- **统一入口 `rqq`** —— ~60 个数据集 + 7 个研究场景 + 7 张业务拼装宽表，全是声明式注册，加新接口只加一条数据、不写函数。
- **LLM 友好** —— 默认 markdown 输出；`rqq help` 一次性吐出全部命令、参数、必填项和默认值；报错清晰、退出码一致，便于自我纠正。
- **原生 license** —— `rqq license` 贴 key 即用，存 `~/.rqq`，不碰环境变量、即时生效、三系统一致。
- **干净安装** —— 纯 wheel，一行装；零依赖核心 + 可选 `data` extra。

## 安装

### 一键（其他电脑，含取数）

Linux / macOS：

```bash
curl -fsSL https://raw.githubusercontent.com/Zynoo71/quant/main/install.sh | sh
```

Windows（PowerShell）：

```powershell
irm https://raw.githubusercontent.com/Zynoo71/quant/main/install.ps1 | iex
```

脚本自动装 uv + 合适的 Python + 全局 `rqq` 命令。装完**新开一个终端**让 `rqq` 上 PATH。

### 手动 / 开发模式

```bash
# 没有 uv 先装：curl -LsSf https://astral.sh/uv/install.sh | sh （Windows 见上面的 ps1）

# A) 全局命令（含取数）
uv tool install "rqsdk-quant[data] @ git+https://github.com/Zynoo71/quant.git"

# B) 仓库开发模式（改代码即时生效）
git clone https://github.com/Zynoo71/quant.git && cd quant && uv sync --extra data
```

只跑元数据、不取数：省掉 `[data]` / `--extra data` 即可（核心零运行依赖）。`data` extra 是 rqdatac + pandas，全 wheel，干净安装、无需任何 build 参数。

## 配置 License

```bash
rqq license -l "你的license_key"     # 或 rqq license 交互粘贴；账号密码 "账号:密码" 也行
rqq license info                     # 查看（已打码）/ rqq license clear 清除
```

会先验证再存到 `~/.rqq/credentials`（权限 600），取数时自动读取并传给 `rqdatac.init()`，**只需 data extra、不碰环境变量、设完即时生效、不用重启终端**。已配过 `RQDATAC2_CONF` 环境变量的也会被识别。

## 快速开始

```bash
rqq help                             # 一次拿到所有命令 / 数据集 / 参数 / 必填 / 默认值
rqq data list                        # 列数据集（--category 过滤）
rqq data describe price              # 看某数据集的参数
rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
rqq data build research-monitor-snapshot --ids 000001.XSHE --start 2024-01-01 --end 2024-01-31
```

默认输出 **markdown**（人和 LLM 都好读）；需要机器解析或落盘时用 `--format json` / `--format csv`，`-o FILE` 写文件。

**完整命令手册见 [docs/cli-usage.md](docs/cli-usage.md)。**

## 覆盖

**原子数据集**（`rqq data get <name>`，14 类）：

```text
master    instruments / instrument / id-convert
calendar  trading-dates / previous-trading-date / next-trading-date
market    price / current-snapshot / current-minute / ticks
factor    factor-names / factor
financial financials-pit / current-performance / performance-forecast / forecast-report-date
equity    shares / dividend / split / turnover-rate / st / suspended / holder-number / main-shareholder
industry  instrument-industry / industry / industry-mapping
event     announcement / investor-qa / investor-ra
money-flow capital-flow / stock-connect / securities-margin / block-trade / abnormal-stocks(-detail)
etf       etf-daily-units / etf-components / etf-cash-components
fund      fund-instruments / fund-daily-units / fund-holdings / fund-stock-change / fund-asset/industry-allocation / fund-nav / fund-benchmark
consensus consensus-price / consensus-comp-indicators / consensus-indicator / consensus-market-estimate / consensus-industry-rating / consensus-industries
index     index-components / index-weights(-ex) / index-indicator / index-factor-exposure
news      current-news
```

**研究场景**（`rqq data generate <name>`，把一个模块需要的多张原始表一次生成）：
`base-universe` · `company-quality` · `institution-attention` · `capital-confirmation` · `price-trend` · `risk-crowding` · `daily-monitor`

**业务拼装宽表**（`rqq data build <name>`，多源合并成稳定表）：
`company-quality-snapshot` · `capital-confirmation-snapshot` · `research-monitor-snapshot` · `fund-position-snapshot` · `consensus-attention-snapshot` · `index-relative-strength-snapshot` · `event-news-snapshot`

生成/拼装结果写入 `outputs/`，并附 `manifest.json` 记录参数、文件、跳过步骤和需外部补充的数据（`external_inputs`）。

## 给 LLM / 自动化用

这个 CLI 就是为 LLM 调用设计的：默认 markdown 输出、`rqq help` 一次拿全 schema、报错可自纠。让模型**开局先跑 `rqq help`**，再 `describe` / `plan` 确认参数即可。

仓库自带一个 Claude skill：`.claude/skills/rqq-data/`。

- 在本仓库用 Claude Code：**自动生效**（项目级 skill）。
- 全局启用：`cp -r .claude/skills/rqq-data ~/.claude/skills/`。
- 其他 LLM/harness：直接把 `.claude/skills/rqq-data/SKILL.md` 当 system 指令喂进去。

## 卸载

```bash
# uv tool 装的（全局 / 一键）
uv tool uninstall rqsdk-quant
rm -rf ~/.rqq                        # license 配置；Windows: Remove-Item -Recurse -Force $HOME\.rqq

# 仓库 / 开发模式装的：删目录即可
rm -rf quant ~/.rqq
```

（可选）这台机器不再用 uv：`uv python uninstall --all && uv cache clean && uv self uninstall`。

## 文档

- [docs/cli-usage.md](docs/cli-usage.md) —— 完整 CLI 手册
- [docs/data-source-coverage.md](docs/data-source-coverage.md) —— 数据源与 API 覆盖检查
- [AGENT.md](AGENT.md) —— 架构与贡献说明

## 免责声明

仅用于数据获取与量化研究流程，不构成任何投资建议。
