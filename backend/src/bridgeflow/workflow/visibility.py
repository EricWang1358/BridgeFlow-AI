"""Browser read scope for declared workflows; absent grants reveal nothing."""
from bridgeflow.access import workflow_departments_for
from bridgeflow.identity import UserIdentity
from bridgeflow.workflow.catalogue import Catalogue


class Visibility:
    def __init__(self, declared: Catalogue, user: UserIdentity | None):
        self.declared = declared
        self.allowed = None if user is None else workflow_departments_for(user.sub)

    def department(self, name: str) -> bool:
        return self.allowed is None or name in self.allowed

    def template(self, name: str) -> bool:
        template = self.declared.templates.get(name)
        return template is not None and self.department(template.department)

    def stage(self, name: str) -> bool:
        stage = self.declared.stages.get(name)
        return (stage is not None and self.department(stage.department)
                and all(self.template(t) for t in (*stage.inputs, *stage.outputs)))

    def all(self) -> bool:
        return (all(self.template(t) for t in self.declared.templates)
                and all(self.stage(s) for s in self.declared.stages))
