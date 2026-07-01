# rqsdk_quant

> 面向米筐 RQData 的量化数据 CLI —— 一个稳定的 `rqq` 命令入口，让人和外部 LLM/自动化系统都能稳定取数。**每个命令对应一次原子 RQData 调用**，按官方模块组织；不做数据聚合。因子、回测、交易为后续。

## 特性

- **统一入口 `rqq`** —— ~200 个原子数据集，镜像整个 RQData API，按官方模块组织；目录由 rqdatac 签名自动生成，加新接口只加一行、不写函数。
- **LLM 友好** —— 默认 markdown 输出；`rqq help` 一次性吐出全部命令、数据集、参数和必填项；报错清晰、退出码一致，便于自我纠正。
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
rqq help                             # 一次拿到所有命令 / 数据集 / 参数 / 必填 / 示例
rqq data list                        # 列数据集（--category 过滤）
rqq data describe price              # 看某数据集的参数说明 + 可运行示例
rqq data list --category fund-mod    # 看某个模块下的数据集
rqq data get price --ids 000001.XSHE --start 2024-01-02 --end 2024-01-03
```

默认输出 **markdown**（人和 LLM 都好读）；需要机器解析或落盘时用 `--format json` / `--format csv`，`-o FILE` 写文件。

**完整数据集与参数参考：`rqq help`**（离线、由 rqdatac 签名自动生成，始终最新）。

## 覆盖

~200 个原子数据集（`rqq data get <name>`），镜像整个 RQData API，按官方模块组织。`rqq data list --category <slug>` 列某模块，`rqq help` 一次拿全。

```text
generic-api       跨品种通用     price / current-snapshot / ticks / trading-dates / id-convert / instruments …
stock-mod         A股           financials-pit / shares / dividend / capital-flow / stock-connect / securities-margin /
                                announcement / investor-ra / industry / abnormal-stocks(-detail) …
futures-mod       期货           futures-dominant / futures-basis / futures-member-rank / dominant-future …
options-mod       期权           options-contracts / options-greeks / options-indicators …
indices-mod       指数/场内基金   index-components / index-weights(-ex) / index-indicator / etf-* …
fund-mod          基金           fund-nav / fund-holdings / fund-asset-allocation / fund-manager / fund-ratings …（40 个）
convertible-mod   可转债         convertible-instruments / convertible-conversion-price / convertible-call-info …（19 个）
risk-factors-mod  风险因子       factor / factor-names / factor-exposure / style-factor-exposure / stock-beta …
spot-goods        现货           spot-benchmark-price
repo              货币市场       interbank-offered-rate / econ-fixing-repo-rate …
macro-economy     宏观经济       econ-money-supply / econ-reserve-ratio / exchange-rate …
alternative-data  另类数据       consensus-price / consensus-indicator / current-news / concept …
```

港股、米筐特色指数通过在现有数据集上传 `--market hk` / 特定指数代码获取，暂无独立条目。未封装的 rqdatac 函数可用 `rqq data call <fn> --kwargs '<json>'` 兜底。

## 给 LLM / 自动化用

这个 CLI 就是为 LLM 调用设计的：默认 markdown 输出、`rqq help` 一次拿全 schema、报错可自纠。让模型**开局先跑 `rqq help`**，再用 `rqq data describe <dataset>` 确认参数即可。

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

- `rqq help` —— 全部数据集、参数、必填项（一次拿全，始终最新）
- [AGENT.md](AGENT.md) —— 架构与贡献说明

## 免责声明

仅用于数据获取与量化研究流程，不构成任何投资建议。
