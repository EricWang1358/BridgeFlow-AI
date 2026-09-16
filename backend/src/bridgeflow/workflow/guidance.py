"""Role guidance derived from declarations, never inferred employee permissions."""
from typing import Any

from bridgeflow.workflow.catalogue import Catalogue


def for_stage(declared: Catalogue, stage_id: str) -> dict[str, Any]:
    stage = declared.stages[stage_id]
    return {
        "stage": stage_id, "title": stage.title, "department": stage.department,
        "owner_role": stage.owner_role, "catalogue_version": declared.version,
        "entry": "DSH Studio / 填报与流转 (Workflow)",
        "inputs": [{"template": name, "title": declared.templates[name].title,
                    "version": declared.templates[name].version,
                    "status": str(declared.templates[name].status)} for name in stage.inputs],
        "outputs": [{"template": name, "title": declared.templates[name].title,
                     "version": declared.templates[name].version,
                     "status": str(declared.templates[name].status)} for name in stage.outputs],
        "action": stage.action or "Not configured / 未配置",
        "destination": {"kind": declared.sink.kind,
                        "scope": "local_demo" if declared.sink.kind == "local_sqlite" else "unconfigured"},
        "steps": [
            "Read the approved template / 查看批准模板",
            "Provide information and answer missing-field questions / 填报并补充缺项",
            "Review displayed values before approving submission / 核对展示值后审批提交",
            "Check the target receipt and data_ready state / 检查目标回执与数据就绪状态",
            "Read the workflow board for the downstream state / 在流转看板查看下游状态",
        ],
        "success_evidence": ["artifact version", "submission receipt", "data_ready"],
        "status_entry": "workflow_board",
        "help": {"responsible_role": stage.owner_role, "contact": None, "status": "contact_not_configured"},
        "limitations": [
            "A declared role does not grant data access / 声明角色不授予数据权限",
            "A sent notification is not completed work / 通知已发送不等于业务完成",
            "Support contact requires company configuration / 求助联系人需公司配置",
        ],
    }
