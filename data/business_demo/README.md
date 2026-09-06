# 业务演示测试组

由 `scripts/make_business_case.py` 生成，属于可见开发/演示数据，不是留出验收集。

分别导入 risk 或 balanced 下四份 CSV，月份选 2025-11，字典使用本目录 dictionary.yaml。

**字典不是可选项。** 只有本目录这份声明了 finance 的可连接列（project）与 business_review 契约；
默认字典两样都没有，用它导入会得到 needs_configuration，研判起不来（第 1 步过、第 2 步不可能）。
用 `python3 scripts/start_web.py --demo` 启动，或导出 FIELD_DICTIONARY_PATH=data/business_demo/dictionary.yaml
（路径相对仓库根解析，不是相对你所在的目录）。

expected.json 是人工复核答案，不得作为模型输入。修改数据后应重新生成并核对。
该组覆盖同批四部门责任；不宣称真实客户科目、库存齐套、授信或报价验收。
