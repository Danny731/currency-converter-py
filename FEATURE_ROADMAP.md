# 货币转换器 — 功能扩展路线图

> 本文档面向后续接手开发的 agent。每个任务都包含背景、改动范围、验收标准和工作量评估，可独立认领。
> 工作量记号：S = 半天内，M = 1-2 天，L = 较大需设计。

## 一、项目现状速览

技术栈：Python 3.10+ / CustomTkinter GUI / uv 管理 / Frankfurter 免费汇率 API（每日更新）。

分层架构（改动时请严格遵守）：

| 层 | 目录 | 职责 | 约束 |
|---|---|---|---|
| 核心逻辑 | `core/` | 货币枚举、转换/交叉汇率、记账本、汇率服务 | 纯逻辑，禁止依赖 UI；`converter.py`/`currency.py`/`tally.py` 必须保持可单测 |
| 持久化 | `storage/` | rates.json / tallybook.json 读写 | IO 失败返回布尔/降级值，不向上层抛异常 |
| 界面 | `ui/` | 两个页面 + 主窗口 | 网络回调用 `widget.after(0, ...)` 切回 UI 线程 |

已支持币种（`core/currency.py` 的 `Currency` 枚举，共 8 个）：CNY USD GBP EUR AUD CAD JPY SGD。

现有功能：
- 转换页（`ui/converter_page.py`）：选源币种 + 输入金额 → 一次性算出对所有币种的金额（表格）。
- 记账页（`ui/tally_page.py`）：混合币种逐笔记账，按目标币种汇总；增/删/清空，自动持久化。
- 记账页当前表格已展示备注列（`note`）；此前待办里提到的“备注列没展示”已过期，后续 F4 只需补时间列和编辑能力。
- 汇率：启动用内置 mock 汇率兜底 → 后台拉 Frankfurter 实时汇率 → 缓存本地供离线复用。

测试：`tests/` 下 39 个用例（pytest），目前只覆盖 `core/`。

## 二、给 agent 的开发约定

1. **保持分层**：新逻辑优先放 `core/` 并补单测；UI 只做展示和事件绑定。
2. **网络只走后台线程**：仿照 `core/rate_service.py` 的 worker 模式，回调切回 UI 线程。
3. **币种增减只改一处**：`core/currency.py` 的 `_SUPPORTED`，其余代码都从这里派生。
4. **持久化要向后兼容**：改 JSON schema 时给旧文件留迁移/降级路径（参考 `storage/*.load()` 的容错写法）。
5. **每个功能配测试**：能进 `core/` 的逻辑必须有 pytest 用例。
6. **本地运行**：`uv run python main.py`；测试 `uv run pytest`。

## 三、功能清单

### P0 — 体验短板，优先做

**F1. 汇率状态条打磨（S，注意：不是新建功能）**
- 现状：**左下角状态条已经存在**（`ui/main_window.py` 的 `self._status`），且已显示「来源 + 日期」三种情况：
  - 实时：`Live rates loaded (source: Frankfurter API, date: 2026-06-30)`（`_apply_rates`，约 121 行）
  - 缓存：`... using saved offline rates (date: X)`（`_on_fetch_failed`，约 133 行）
  - 兜底：`... using mock rates`（约 138 行）
- **不要重复造一个新状态条**。只需在现有文案上打磨两点：
  1. 日期补「距今 X 天」——汇率每天更新，`(3 天前)` 比裸 ISO 日期更直观。距今天数自己算（`datetime.date.today()` 减 `last_update_date`）。
  2. 保持英文文案，与当前应用语言风格统一；多语言/i18n 可作为后续独立功能，不在 F1 中实现。
- 涉及：`ui/main_window.py`（`_initial_status_text` / `_apply_rates` / `_on_fetch_failed` 三处文案）。
- 验收：实时显示 `Live rates · 2026-06-30 (today)`；缓存显示 `Offline cache · 3 days ago`；无缓存显示 `Built-in reference rates`。原有三分支逻辑不变，只改展示。

**F2. 金额格式化（S）**
- 现状：`CurrencyConverter.format_result` 统一保留小数，JPY 这类无小数币种显示不自然，大额无千分位。
- 做法：按币种区分小数位（JPY 0 位，其余 2 位），加千分位分隔符。放进 `core/converter.py` 并补单测。
- 涉及：`core/converter.py`、`tests/test_converter.py`。
- 验收：`12345.6 JPY` → `12,346`；`1234567.89 USD` → `1,234,567.89`。

**F3. 一键互换币种（S）**
- 现状：转换页只能从「源币种」单向看全表，想反查要手动改选项。
- 做法：转换页加「⇄ 互换」按钮（或在记账页源/目标间互换），点后交换并重算。
- 涉及：`ui/converter_page.py`。
- 验收：点击后源币种与当前关注的目标对调，结果即时刷新。

### P1 — 实用增强

**F4. 记账记录可编辑 + 显示时间列（M）**
- 现状：`TallyEntry` 已存 `created_at` 和 `note`；当前记账页表格已展示备注列，但还没展示时间，且只能删不能改。
- 做法：表格增加「时间」列；支持双击某行编辑金额/备注后重算并持久化。
- 涉及：`ui/tally_page.py`，必要时给 `core/tally.py` 加 `update_entry(index, ...)` 并补单测。
- 验收：编辑后总额、持久化文件同步更新；时间列显示 `created_at`。

**F5. 记账导出 CSV（S-M）**
- 现状：数据只在 `tallybook.json`，无法导入 Excel/表格。
- 做法：记账页加「导出 CSV」按钮，弹文件保存框，写 UTF-8 BOM（保证 Excel 正确显示中文）。
- 涉及：`storage/` 新增 `csv_export.py`（纯函数，可单测）+ `ui/tally_page.py` 接按钮。
- 验收：导出含金额/币种/折算额/备注/时间表头；中文备注在 Excel 不乱码。

**F6. 设置面板 + 偏好持久化（M）**
- 现状：外观模式、默认币种、小数位都写死在代码里，每次启动重置。
- 做法：新增 `storage/settings.py`（读写 `settings.json`）；设置项含主题(System/Light/Dark)、默认源/目标币种、小数位。启动时加载。
- 涉及：新文件 + `ui/main_window.py` + 两个页面读默认值。
- 验收：改设置重启后保持；`settings.json` 损坏时降级到默认值不崩。

### P2 — 较大改动 / 进阶

**F7. 动态币种列表（L，改动面最大）**
- 现状：`core/currency.py` 是固定 8 币种枚举，Frankfurter 实际支持 30+ 种。
- 做法：把币种从硬编码枚举改为可配置集合（可从 API 的 `/currencies` 端点拉全量，或在设置里勾选）。需重构所有依赖 `Currency` 枚举的地方。
- 涉及：`core/currency.py`（核心重构）、`core/converter.py`、`storage/*`、所有 UI。
- 注意：**必须保证旧 `tallybook.json`/`rates.json` 兼容**；先写迁移测试再动手。这是风险最高的一项,建议单独开分支。
- 验收：新增币种能正常换算/记账;旧数据文件照常加载。

**F8. 历史汇率趋势图（M-L）**
- 现状：只有当日汇率。Frankfurter 提供 `/v1/{start}..{end}` 时间序列端点。
- 做法：选定币种对，拉近 30/90 天序列，用图表展示。轻量可用 `matplotlib` 内嵌 Tk，或纯 Canvas 画折线。
- 涉及：`core/rate_service.py` 加历史拉取方法（后台线程）+ 新 UI 页/弹窗。
- 验收：选 USD→CNY 显示近 30 天折线；断网时提示而非崩溃。

**F9. 转换历史记录（S-M）**
- 现状：转换页算完即弃，无法回看刚才算过什么。
- 做法：每次转换记一条（源币种/金额/时间），侧栏或弹窗可回看、可清空，最多保留近 100 条。
- 涉及：`ui/converter_page.py`，可选持久化到 `storage/`。
- 验收：连续转换后能看到历史列表；清空生效。

## 四、工程化建议（非功能，但建议穿插着做）

- **CI**：加 `.github/workflows/test.yml`,push/PR 自动跑 `uv run pytest`。小工作量、收益高。
- **Lint/格式化**：引入 `ruff`(检查 + 格式化),加进 dev 依赖组和 CI。
- **类型检查**：`mypy` 或 `pyright`，代码已大量用类型注解，接入成本低。
- **storage schema 版本号**：在 `tallybook.json`/`rates.json`/未来的 `settings.json` 里加 `"version": 1` 字段，为 F7 等未来迁移留接口。建议在做 F6 时顺手加上。

## 六、明确不做（避免重复提）

- **频繁刷新汇率按钮**：已与产品方确认不做。Frankfurter 是免费 API、汇率每天才更新一次,没有高频刷新需求。新 agent 不要再加这个。

## 五、任务认领模板

接手某项功能时,建议按此自检:
1. 读本文件「三、开发约定」+ 对应功能的「涉及/验收」。
2. 业务逻辑放 `core/` 并补 `tests/`,UI 只做装配。
3. 改了存储格式 → 确认旧文件能加载(写兼容测试)。
4. 完成后 `uv run pytest` 全绿,`uv run python main.py` 手动跑通主流程。
5. 网络操作必须在后台线程,回调用 `widget.after(0, ...)` 回主线程。
