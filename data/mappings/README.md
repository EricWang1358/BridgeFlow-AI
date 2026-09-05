# 字段字典（Field Dictionary）

跨部门映射的**唯一事实来源**。内容来自 OA 导出的真实字段定义，不是猜出来的。

## 为什么需要这个文件

`SKU-A1` 和 `RM-Alu-6061` 是「产品 ↔ 它消耗的原料」。这两个标识符**没有任何字符上的
关系**，也不应该有。实测把字符串相似度当候选生成手段，在真实样本上产出了**零条映射**
（[issue #24](https://github.com/EricWang1358/BridgeFlow-AI/issues/24)）。

这个关系只有两个地方知道：

1. **主数据 / 物料清单** —— 明确写着 SKU-A1 用 RM-Alu-6061。填进本文件的 `relations`。
2. **数据本身的共现** —— 市场部同一行里同时出现 `Acme Pte Ltd` 和 `SKU-A1`，
   这就是该部门在陈述「谁订了什么」。系统自动识别，不需要在这里声明。

本文件负责第一种。第二种系统自己会做。

## 文件位置

默认 `data/mappings/field-dictionary.yaml`，可用环境变量覆盖：

```bash
FIELD_DICTIONARY_PATH=/absolute/path/to/field-dictionary.yaml
```

**文件不存在时系统仍能运行** —— 会退回到列名猜测（`sku`、`customer`、`material` 之类
的关键词），只是覆盖不全。这是为了让样本数据跑得起来，不是长期方案。

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
| `note` | 依据来源，会显示在下钻证据里。**建议填**，审批时有人会问 |

实体 id 的构造规则：类型加冒号，再把标识符转小写、非字母数字一律换成连字符。
`SKU-A1` → `sku:sku-a1`，`4000-Sales/A1` → `gl_account:4000-sales-a1`，
`Acme Pte Ltd` → `customer:acme-pte-ltd`。

## 待 OA 字段到位后要做的事

1. 用真实字段名填 `columns`，替换掉现在的关键词猜测
2. 从物料清单和财务科目对照表导出 `relations`
3. 跑一遍 pipeline，确认 `links accepted` 不再是 0
4. 剩下的进 `unresolved` 的，人工确认一次，之后持久化成规则
   （[issue #3](https://github.com/EricWang1358/BridgeFlow-AI/issues/3)）

## 尚未实现

PRD FR 08 还要求映射带**生效月份、失效月份、分摊比例**。当前格式没有这三项——
分摊比例是报价成本计算的输入，OA 字段到位时需要一并确定，格式会相应扩展。
