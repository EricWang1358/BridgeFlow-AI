# BridgeFlow 业务设计 Demo

从这里开始：[说明页](index.html) · [完整文件清单](files.json) · [六步演示与启动命令](../docs/17-business-mvp-acceptance.md)。
在浏览器打开 `index.html` 能看说明与证据；真正的交互演示用启动器打印的 DSH 认证地址。

正常案例可以演示，异常路径的收尾还没做完。上台前先看
[链路审计与未完成项](../docs/19-chain-audit.md)：报告通过不等于整条业务流程已完成。

这是制造企业 **2025-11** 的公开合成案例。两个场景各有四部门 CSV，标准答案由独立显式算术生成。
核对点是每份 `report.json` 里的 `manager_decision`，不是模型最后一段话说得好不好。

## 六步

1. 看 [dictionary.yaml](data/dictionary.yaml)：单位、成本正数约定、公式、关注阈值、责任人。
   启动私有服务时 `FIELD_DICTIONARY_PATH` 指向它；上传 CSV 不会修改字典。
2. 在「导入与数据」或右上角「部门文件」选取 [risk](data/risk) 的四份 CSV，业务月份填 `2025-11`，
   记下返回的 `batch_id`。
3. 发送下面第一句，观察轨迹里的四次原生 Spawn 与顶栏四个子代理。
4. 打开「对话｜轨迹｜**业务状态**」的新页签，点风险节点筛选，再打开报告核对公式、来源与责任人。
5. 用 [balanced](data/balanced) 的四份 CSV 导入新批次再研判；旧批次与指定报告仍能重开。
   回到正常范围不代表获准执行业务动作。
6. 用第二句演示原生审批：拒绝时填一条理由。拒绝、取消、超时都不写映射，批准一次才写入。
   生产默认等待 300 秒，自动测试 5 秒，界面显示的是实际配置。

两句粘贴话术（只替换批次编号）：

> 请研判 2025-11 批次 <batch_id>：先 review_context，同一响应调用四次官方 subagent，
> 分别派 production/procurement/finance/marketing，再 review_finalize。
> 缺部门或校验失败如实标 partial，不重试，不执行业务动作。

> 请仅调用一次 confirm_mapping：source="sku:demo-review"，target="customer:demo"，
> relation="ordered_by"，accepted=true，evidence="合成案例的关系待负责人核对"，period="2025-11"。
> 等待原生审批；若拒绝，说明未写入并转述操作者理由，不重试。

## 核对点

| 场景 | 报告应该说明 | 谁负责 |
| --- | --- | --- |
| risk | 工时负荷 110%、剩余 −10 小时；采购支出 760 SGD、偏差 8.5714%；毛利 −10%、加权应收账期 47.1429 天；订单缺口 30、请求账期 50 天 | 运营协调排产；采购解释预算差；财务复核利润与信用；销售据批准结果沟通 |
| balanced | 工时负荷 80%、剩余 20 小时；支出 700 SGD、偏差 0%；毛利 33.3333%、应收账期 30 天；订单差额 −20、请求账期 30 天 | 仍按部门责任复核，没有自动调价、排产或授信 |
| step-limit | 财务没有有效判断，整单 partial，不能代签；可向原队长提交人工复核意见 | 财务负责人补齐判断，业务负责人协调；无需强制重跑四人 |
| approval | 同一请求的 asked/decided ID 对齐；拒绝理由回到 agent；只有 allowed-once 写映射 | 当前 DSH 认证会话的操作者 |

[expected.json](data/expected.json) 只供测试程序与人工核对，禁止上传或喂给模型。
样本封顶只限制来源展示条数，所有符合规则的行都参与计算；引用次数可能包含同一单元格的多次参与。

`evidence/` 链接到仓库里由 `--keep 2` 管理的证据，不复制第三份截图：每场景的 `manifest.json`
指向最新运行，`runs/` 最多保存最近两轮。历史截图不是实时运行。`session-audit.json` 只投影对应的
队长与四个子会话，省略完整提示词、推理轨迹与凭证。文件清单可以用
`python3 scripts/build_demo_walkthrough.py` 重建。

## English summary

Upload the four department CSVs for November 2025, run the captain request, inspect
Chat | Trajectory | Business state, and compare the saved report's `manager_decision` with the answer
key. Interface labels follow the native DSH language setting; the business contract text and model
explanations keep their declared language. Never feed `expected.json` to the model. Reports propose
actions; department owners authorise decisions.

从空笔记本开始的产品操作见 [笔记本演示故事](notebook.md)，包含示例导入、来源预览、用途切换与保存恢复。
