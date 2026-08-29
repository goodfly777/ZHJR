from atguigu.chitchat.responder import ChitchatResponder
from atguigu.domain.message import UserMessage, BotMessage
from atguigu.domain.state import DialogueState


class ChitchatHandler:
    def __init__(self, responder: ChitchatResponder):

        self.responder = responder

    async def handle(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:

        return await self.responder.respond(
            user_message,
            state.shared.current_session().turns
        )

