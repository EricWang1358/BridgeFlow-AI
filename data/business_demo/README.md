# 业务演示测试组

由 `scripts/make_business_case.py` 生成，属于可见开发/演示数据，不是留出验收集。

分别导入 risk 或 balanced 下四份 CSV，月份选 2025-11，字典使用本目录 dictionary.yaml。

**本案例需要配套字典。** 本目录的 `dictionary.yaml` 声明了这些 CSV 的连接列、度量和研判契约。
从仓库根目录启动，先载入运行环境，再指定本案例的字典：

```bash
source ../.venv/bin/activate
source env.sh
export FIELD_DICTIONARY_PATH=data/business_demo/dictionary.yaml
python scripts/start_web.py --port 3082
```

此处不要加 `--demo`：该参数会改用 `data/mock_business/demo/dictionary.yaml`，对应的是内置示例笔记本的 XLSX 数据。
字典路径相对仓库根解析。

expected.json 是人工复核答案，不得作为模型输入。修改数据后应重新生成并核对。
该组覆盖同批四部门责任；不宣称真实客户科目、库存齐套、授信或报价验收。
