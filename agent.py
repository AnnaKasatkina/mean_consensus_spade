import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

class ConsensusAgent(Agent):
    class ConsensusBehav(CyclicBehaviour):
        async def on_start(self):
            self.counter = 0
            # self.weight = getattr(self.agent, "weight", 1/7)
            self.weight = 1/7
            start_delay = getattr(self.agent, "start_delay", 0.5)
            if start_delay > 0:
                await asyncio.sleep(start_delay)

            self.idle = False

        async def run(self):
            ag = self.agent

            if not self.idle:
                # 1) Отправляем своё значение
                for neighbor in getattr(ag, "neighbors", []):
                    m = Message(to=neighbor)
                    m.set_metadata("performative", "inform")
                    m.set_metadata("type", "value")
                    m.body = str(ag.value)
                    await self.send(m)
                    ag._out_messages = getattr(ag, "_out_messages", 0) + 1

                # 2) Приём входящих сообщений
                timeout = getattr(ag, "round_timeout", 0.5)
                start = asyncio.get_event_loop().time()
                received_vals = []
                while True:
                    remaining = timeout - (asyncio.get_event_loop().time() - start)
                    if remaining <= 0:
                        break
                    msg = await self.receive(timeout=remaining)
                    if msg is None:
                        break
                    try:
                        if msg.metadata and msg.get_metadata("type") == "value":
                            received_vals.append(float(msg.body))
                            ag._in_messages = getattr(ag, "_in_messages", 0) + 1
                    except Exception:
                        pass

                # 3) Обновление значения
                deg = len(received_vals)
                if deg > 0:
                    sum_neighbors = sum(received_vals)
                    new_x = ag.value + self.weight * (sum_neighbors - deg * ag.value)
                    ag._arith_ops = getattr(ag, "_arith_ops", 0) + max(0, deg) + 2
                    ag.value = new_x

                self.counter += 1

                if self.counter >= getattr(ag, "rounds", 0):
                    self.idle = True
                    ag._finished_rounds = True
                    return

                await asyncio.sleep(0.01)

            else:
                while not getattr(ag, "shutdown", False):
                    msg = await self.receive(timeout=0.5)
                return

        async def on_end(self):
            return

    async def setup(self):
        template = Template()
        template.set_metadata("performative", "inform")
        template.set_metadata("type", "value")

        beh = self.ConsensusBehav()
        self.add_behaviour(beh, template)

        self.ready = True
