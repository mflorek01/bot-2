from agent.agent_loop import AgentConfig, AutomationAgent


def main():
    agent = AutomationAgent(config=AgentConfig(log_dir="logs", step_budget=20))
    agent.memory.goal = "Example goal: open an application window and click OK."
    agent.run()


if __name__ == "__main__":
    main()
