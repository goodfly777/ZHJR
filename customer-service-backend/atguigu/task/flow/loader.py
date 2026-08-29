from pathlib import Path
from typing import Any

import yaml

from atguigu.task.flow.models import FlowCatalog, FlowSlot, Flow
from atguigu.task.flow.steps import FlowStep, CollectSlotStep


class FlowLoader:

    def load_many(self, paths: list[Path]) -> FlowCatalog:
        flows: dict[str, Flow] = {}
        slots: dict[str, FlowSlot] = {}

        for path in paths:
            catalog = self.load(path)
            flows.update(catalog.flows)
            slots.update(catalog.slots)

        return FlowCatalog(
            flows=flows,
            slots=slots
        )


    def load(self, path: Path) -> FlowCatalog:

        # 读取path路径下的配置文件
        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        slots: dict[str, FlowSlot] = self._load_slots(data.get("slots", {}))
        flows: dict[str, Flow] = self._load_flows(data.get("flows", {}), slots)
        
        return FlowCatalog(
            flows=flows,
            slots=slots
        )

    def _load_slots(self, slots_data: dict[str, dict]) -> dict[str, FlowSlot]:

        return {
            name: FlowSlot(name = name, **slot_data)
            for name, slot_data in slots_data.items()
        }

    def _load_flows(self, flows_data: dict[str, dict], slots: dict[str, FlowSlot]) -> dict[str, Flow]:

        return {
            flow_id: self._load_flow(flow_id, flow_data, slots)
            for flow_id, flow_data in flows_data.items()
        }

    def _load_flow(
            self,
            flow_id: str,
            flow_data: dict[str, Any],
            slots: dict[str, FlowSlot]
    ):

        steps = [
            FlowStep.from_dict(step_data)
            for step_data in flow_data["steps"]
        ]

        flow_slots = [
            slots[step.slot_name]
            for step in steps
            if isinstance(step, CollectSlotStep)
        ]

        return Flow(
            id = flow_id,
            description= flow_data.get("description", ""),
            name = flow_data["name"],
            steps = steps,
            slots = flow_slots
        )


if __name__ == '__main__':

    loader = FlowLoader()
    path1 = Path(__file__).parents[3] / 'flow_config' / 'user_flows.yml'
    # path2 = Path(__file__).parents[3] / 'flow_config' / 'other_flows.yml'

    flow_catalog = loader.load_many([path1])
    print(flow_catalog)