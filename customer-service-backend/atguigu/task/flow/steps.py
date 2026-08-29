from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atguigu.task.flow.links import FlowStepLink, StaticLink, ConditionalLink, FallbackLink
from atguigu.task.response.models import ResponseTemplate


@dataclass
class SlotValidation:
    condition: str
    failure_template: ResponseTemplate

class FlowStepType(Enum):
    START = "start"
    ACTION = "action"
    RESPONSE = "response"
    COLLECT = "collect"
    END = "end"


@dataclass
class FlowStep:
    id: str
    type: FlowStepType
    next: list[FlowStepLink] = field(default_factory=list)
    description: str = "" # 扩展字段

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "FlowStep":
        # 判断当前的step是什么类型
        step_type = step_data["type"]
        # 根据类型获取类名
        step_class = STEP_TYPE_TO_CLASS[step_type]
        # 将方法的调用分发给子类类型
        return step_class.from_dict(step_data)


    @staticmethod
    def build_fields(step_data: dict[str, Any]) -> dict[str, Any]:

        """处理所有的FlowStep子类的共同属性"""
        return {
            "id": step_data["id"],
            "type": FlowStepType(step_data["type"]),
            "description": step_data.get("description"),
            "next": FlowStep.build_links(step_data["next"])
        }

    @classmethod
    def build_links(cls, next_data: str | list) -> list[FlowStepLink]:
        if isinstance(next_data, str):
            return [StaticLink(target=next_data)]

        links: list[FlowStepLink] = []
        for link_data in next_data:
            if "if" in link_data:
                links.append(ConditionalLink(
                    target=link_data["then"],
                    condition=link_data["if"]
                ))
            else:
                links.append(FallbackLink(target=link_data["else"]))

        return links

@dataclass
class StartFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.build_fields(step_data))

@dataclass
class ActionFlowStep(FlowStep):
    action: str = ""
    args: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ActionFlowStep":
        return cls(
            **FlowStep.build_fields(step_data),
            action=step_data["action"],
            args=step_data.get("args", {}),
        )


@dataclass
class ResponseFlowStep(FlowStep):
    template: ResponseTemplate = field(default_factory=ResponseTemplate)

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ResponseFlowStep":
        return cls(
            **FlowStep.build_fields(step_data),
            template = ResponseTemplate.from_dict(step_data["template"])
        )


@dataclass
class CollectSlotStep(FlowStep):
    slot_name: str = ""
    template: ResponseTemplate = field(default_factory=ResponseTemplate)
    validation: SlotValidation | None = None


    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "CollectSlotStep":

        validation = None
        if "validation" in step_data:
            validation_data = step_data["validation"]
            validation = SlotValidation(
                condition=validation_data["condition"],
                failure_template=ResponseTemplate.from_dict(validation_data["failure_template"]),
            )

        return cls(
            **FlowStep.build_fields(step_data),
            slot_name=step_data["slot_name"],
            template=ResponseTemplate.from_dict(step_data["template"]),
            validation=validation,
        )


@dataclass
class EndFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.build_fields(step_data))

STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "collect": CollectSlotStep,
    "action": ActionFlowStep,
    "response": ResponseFlowStep,
    "end": EndFlowStep,
}