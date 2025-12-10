import asyncio
import json
import spade
from agent import ConsensusAgent

CONFIG = "graph.json"

async def main():
    with open(CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    n = cfg.get("n")
    adj = cfg["adj"]
    initial = cfg.get("initial_values", [0.0] * n)
    round_timeout = cfg.get("round_timeout", 0.8)
    rounds = cfg.get("rounds", 20)
    domain = cfg.get("domain", "localhost")
    pwd_prefix = cfg.get("password_prefix", "pass")
    start_delay = cfg.get("start_delay", 0.5)

    true_mean = sum(initial) / len(initial)

    agents = []
    labels = []
    for i in range(n):
        jid = f"agent{i+1}@{domain}"
        pwd = f"{pwd_prefix}{i+1}"
        a = ConsensusAgent(jid, pwd)
        a.value = float(initial[i])
        a.neighbors = []
        a.round_timeout = round_timeout
        a.rounds = rounds
        a.start_delay = start_delay
        for j in range(n):
            if adj[i][j]:
                a.neighbors.append(f"agent{j+1}@{domain}")
        a._out_messages = 0
        a._in_messages = 0
        a._arith_ops = 0
        a._finished_rounds = False
        a.shutdown = False
        a.label = f"agent{i+1}"

        max_deg = max(sum(row) for row in adj)
        a.weight = 1.0 / (max_deg + 1)
        
        labels.append(a.label)
        agents.append(a)

    for a in agents:
        await a.start(auto_register=True)
        await asyncio.sleep(0.02)

    waited = 0.0
    timeout_ready = max(3.0, start_delay + 2.0)
    while True:
        if all(getattr(a, "ready", False) for a in agents):
            break
        await asyncio.sleep(0.1)
        waited += 0.1
        if waited >= timeout_ready:
            print("Warning: not all agents reported ready within timeout; continuing anyway.")
            break
    await asyncio.sleep(0.1)

    w_iter = 4
    w_agent = 10
    w_true = 10
    w_mae = 10
    line = "|"
    line += f"{'':^{w_iter}}|"
    for lbl in labels:
        line += f"{lbl:^{w_agent}}|"
    line += f"{'true_mean':^{w_true}}|"
    line += f"{'mae':^{w_mae}}|"
    print(line)
    sep = "|"
    sep += "-" * w_iter + "|"
    sep += ("".join([("-" * w_agent + "|") for _ in labels]))
    sep += "-" * w_true + "|"
    sep += "-" * w_mae + "|"
    print(sep)

    for t in range(1, rounds + 1):
        await asyncio.sleep(round_timeout + 0.02)
        snapshot = [agents[i].value for i in range(n)]
        mae = sum(abs(v - true_mean) for v in snapshot) / n

        row = "|"
        row += f"{str(t):^{w_iter}}|"
        for v in snapshot:
            cell = f"{v:>{w_agent - 1}.6f}"
            row += f" {cell}|"
        tm_cell = f"{true_mean:>{w_true - 1}.6f}"
        mae_cell = f"{mae:>{w_mae - 1}.6f}"
        row += f" {tm_cell}| {mae_cell}|"
        print(row)

    await asyncio.sleep(0.3)

    for a in agents:
        a.shutdown = True

    await asyncio.sleep(0.2)

    for a in agents:
        if a.is_alive():
            await a.stop()

    print("\nRun finished. All agents stopped.")


if __name__ == "__main__":
    spade.run(main())
