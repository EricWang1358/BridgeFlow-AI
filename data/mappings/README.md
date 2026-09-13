# 字段字典（Field Dictionary）

跨部门映射的**唯一事实来源**。内容来自 OA 导出的真实字段定义，不是猜出来的。

> 谁来写这个文件：人，事先。业务方 2026-09-07 定的边界是标准格式与初始字典纯人工预设，
> 原话是「这个东西没有知识库，LLM 做不出来的」。模型的职责是把上传件的列匹配到本文件已声明的字段
> 并给出证据，由人审核；不是产出本文件。完整约束见
> [`../../CLAUDE.md`](../../CLAUDE.md#字典由人预设模型只做匹配)。

## 为什么需要这个文件

`SKU-A1` 和 `RM-Alu-6061` 是「产品 ↔ 它消耗的原料」。这两个标识符**没有任何字符上的
关系**，也不应该有。实测把字符串相似度当候选生成手段，在真实样本上产出了**零条映射**
（[issue #24](https://github.com/EricWang1358/BridgeFlow-AI/issues/24)）。

这个关系只有两个地方知道：

1. 主数据与物料清单：明确写着 SKU-A1 用 RM-Alu-6061。填进本文件的 `relations`。
2. 数据本身的共现：市场部同一行里同时出现 `Acme Pte Ltd` 和 `SKU-A1`，这就是该部门在陈述
   「谁订了什么」。这种系统自己会识别，不需要在这里声明。

本文件负责第一种，第二种系统自己会做。

## 文件位置

默认 `data/mappings/field-dictionary.yaml`，可用环境变量覆盖：

```bash
FIELD_DICTIONARY_PATH=/absolute/path/to/field-dictionary.yaml
```

文件不存在时系统仍能运行：遗留 resolver 会退回列名关键词猜测（`sku`、`customer`、`material` 之类），
覆盖不全，且那只是为了让样本数据跑起来。当前默认入口在字典缺席时明确报 `needs_configuration`
并要求配置，不猜（见仓库根的 `CLAUDE.md`）。

## 格式

```yaml
# 哪个部门的哪一列，装的是哪一类实体。
# 一旦这一段有内容，系统就完全按它来，不再用列名猜测——
# 没有在这里声明的列会被忽略，而不是被猜。
columns:
  production:
    sku: sku                    # 列名: 实体类型
    line: capacity_unit
  procurement:
    material: raw_material
  finance:
    gl_account: gl_account
    customer: customer
  marketing:
    customer: customer
    product: sku                # 市场部管 SKU 叫 product

# 主数据声明的关系。这些是确定的，置信度 1.0，不经过模型。
relations:
  - source: sku:sku-a1
    target: raw_material:rm-alu-6061
    relation: consumes
    note: BOM 2025 版

  - source: sku:sku-a1
    target: gl_account:4000-sales-a1
    relation: books_to
    note: 财务科目对照表
```

### `columns` 段

| 字段 | 说明 |
| --- | --- |
| 一级键 | 部门：`production` / `procurement` / `finance` / `marketing` |
| 二级键 | **清洗后**的列名（小写下划线，见下） |
| 值 | 实体类型：`sku` / `raw_material` / `gl_account` / `capacity_unit` / `customer` |

**列名要填清洗后的形式。** Sanitizer 会把 `SKU ` → `sku`、`Unit Price` → `unit_price`、
`GL Account` → `gl_account`。填原始表头不会匹配上。

### `relations` 段

| 字段 | 说明 |
| --- | --- |
| `source` / `target` | 实体 id，格式 `{类型}:{标识符转小写连字符}` |
| `relation` | `consumes` / `books_to` / `produced_on` / `ordered_by` |
| `note` | 依据来源，会显示在下钻证据里。建议填：审批时一定有人问 |

实体 id 的构造规则：类型加冒号，再把标识符转小写、非字母数字一律换成连字符。
`SKU-A1` → `sku:sku-a1`，`4000-Sales/A1` → `gl_account:4000-sales-a1`，
`Acme Pte Ltd` → `customer:acme-pte-ltd`。

### `measures` / `rollups` / `derived` 段

`columns` 说的是「这一行讲的是谁」，这三段说的是「什么可以被算、怎么算」。
指标需要它们，而把列名写进 Python 就等于把客户的表结构写死——真实字段还在协商中
（`CLAUDE.md` 第八条硬约束）。

```yaml
measures:
  procurement:
    unit_price: unit_price          # 每一单位多少钱
    qty: purchase_quantity          # 买了几单位

rollups:
  purchase_quantity: sum            # 跨期合并方式：sum / average / period_end

derived:
  purchase_amount:
    product: [unit_price, purchase_quantity]   # 表里没有金额列时，金额由这两列算出来
```

三段各管一件事：

| 段 | 键 → 值 |
| --- | --- |
| `measures` | 清洗后列名 → 度量名 |
| `rollups` | 度量名 → `sum` / `average` / `period_end` |
| `derived` | 度量名 → `product: [度量, 度量]` |

- `measures` 声明这一列可以被算。度量名（`output_quantity`、`purchase_amount` 这些）是代码认识的词汇，
  列名不是。
- `rollups` 声明跨期怎么合并，以及同一格落进多行时怎么折叠。数量求和、单价取平均、库存取期末：
  选错了会得到一个看起来很合理的数字，所以它必须是声明出来的。这里没有缺省值：真撞上多行而此处没声明，
  Master Table 拒绝整张表并点名缺哪个度量。
- `derived` 声明表里没有、但由有的列算出来的度量。

#### 一条踩过的前车之鉴

不要把单价列声明成金额。`unit_price: purchase_amount` 曾在这份字典里待过，于是 `material_spend`
老老实实把一整列单价加起来当支出：2025-11 报出 13,540，而三张填了价的 PO 实际是 117,250
（数字与复现见 [`docs/00`](../../docs/00-status.md)）。被引用的三个单元格全都真实存在，公式也照声明执行了，
错在声明本身。

#### `derived` 的两条规矩

1. 表里已有金额列时不要写 `derived`。两条都可用时系统优先读客户自己写下的金额（那才是能签字的数），
   派生只是没有金额列时的路。
2. 一个度量只能对上一列。两列都声明成 `unit_price` 时 `material_spend` 会拒绝，而不是取先出现的那个。
   「哪一列才是单价」是字典该回答的问题。

缺价的采购行：`material_spend` 整条拒绝并点名那一行，因为少算一行就是把支出报小；
`material_price_change` 只把那一行同时移出分子与分母，比率仍然成立，公式里写明覆盖几行。
### `account_classes` 段

同一列金额里既有销售行也有成本行时，靠科目编码把它们分开。哪些编码算销售、哪些算销售成本是客户科目表决定的，
所以标记写在字典里，代码里没有任何科目关键词（#92）：

```yaml
account_classes:
  finance:
    sales: [sales, rev, 销售, 收入]
    cost_of_sales: [cogs, cos, cost, 成本]
```

- 只在字典声明的**实体列**（如科目编码）里找标记，客户名称等其他列不参与，避免「Cost Cutters Ltd」把销售行算成成本。
- 没有声明时，`sales`、`cost_of_sales`、`gross_margin` 一律拒绝，不从名称猜。
- 声明了分类的部门，金额列的简单合计是**净发生额**，`revenue` 指标会拒绝并提示改用 `sales` 与 `cost_of_sales`，不把净额当收入展示。
- 示例里的标记是演示用，真实口径由业务方在 #23 确认后替换。

## 待 OA 字段到位后要做的事

1. 用真实字段名填 `columns`，替换掉现在的关键词猜测；用真实科目表填 `account_classes`
2. 从物料清单和财务科目对照表导出 `relations`
3. 跑一遍 pipeline，确认 `links accepted` 不再是 0
4. 剩下的进 `unresolved` 的，人工确认一次，之后持久化成规则
   （[issue #3](https://github.com/EricWang1358/BridgeFlow-AI/issues/3)）

## 尚未实现

PRD FR 08 还要求映射带**生效月份、失效月份、分摊比例**。当前格式没有这三项——
分摊比例是报价成本计算的输入，OA 字段到位时需要一并确定，格式会相应扩展。