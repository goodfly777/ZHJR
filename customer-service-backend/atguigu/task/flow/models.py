from dataclasses import dataclass, field

from atguigu.task.flow.steps import FlowStep, FlowStepType


@dataclass
class FlowSlot:
    name: str
    type: str = "any"
    label: str = ""
    description: str = ""

@dataclass
class Flow:
    id: str
    description: str = ""
    steps: list[FlowStep] = field(default_factory=list)
    slots: list[FlowSlot] = field(default_factory=list)
    name: str | None = None


    def get_start_step(self):
        """找到当前流程的start步骤"""
        for step in self.steps:
            if step.type is FlowStepType.START:
                return step
        raise Exception("No start step found")

    def get_step(self, step_id: str) -> FlowStep:
        """根据step_id获取步骤对象"""
        for step in self.steps:
            if step.id == step_id:
                return step
        raise Exception("No step found")


@dataclass
class FlowCatalog:
    flows: dict[str, Flow] = field(default_factory=dict)
    slots: dict[str, FlowSlot] = field(default_factory=dict)


    def get_flow(self, flow_id: str) -> Flow:
        """根据flow_id获取flow对象"""
        return self.flows[flow_id]


