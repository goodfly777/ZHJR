from pydantic import TypeAdapter
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from atguigu.domain.state import DialogueState
from atguigu.models.base import Base

DIALOGUE_STATE_ADAPTER = TypeAdapter(DialogueState)

class DialogueStateRecord(Base):
    """dialogue_states表的实体类"""

    __tablename__ = "dialogue_states"

    sender_id: Mapped[str] = mapped_column(String(255),
        primary_key=True,
    )
    state_json: Mapped[str] = mapped_column(Text, nullable=False)