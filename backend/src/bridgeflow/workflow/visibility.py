"""Browser read scope for declared workflows.

Owner decision 2026-09-24: department scope from Feishu knowledge bases applies only to
Feishu import and upload, so every signed-in employee sees every declared template, stage
and record. Kept as the single place the workflow pages ask, so a later rule has one home;
it still refuses what the catalogue does not declare.
"""
from bridgeflow.identity import UserIdentity
from bridgeflow.workflow.catalogue import Catalogue


class Visibility:
    def __init__(self, declared: Catalogue, user: UserIdentity | None):
        self.declared = declared

    def department(self, name: str) -> bool:
        return True

    def template(self, name: str) -> bool:
        return name in self.declared.templates

    def stage(self, name: str) -> bool:
        stage = self.declared.stages.get(name)
        return stage is not None and all(self.template(t) for t in (*stage.inputs, *stage.outputs))

    def all(self) -> bool:
        return True
