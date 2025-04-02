from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from tools.custom_tool import PublisherTool, ReadTemplateTool


@CrewBase
class AutowxGzh:
    """AutowxGzh crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, use_template=False):
        self.use_template = use_template

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            verbose=True,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            verbose=True,
        )

    @agent
    def auditor(self) -> Agent:
        return Agent(
            config=self.agents_config["auditor"],
            verbose=True,
        )

    @agent
    def designer(self) -> Agent:
        return Agent(
            config=self.agents_config["designer"],
            verbose=True,
        )

    @agent
    def templater(self) -> Agent:
        return Agent(
            config=self.agents_config["templater"],
            tools=[ReadTemplateTool()],
            verbose=True,
        )

    @agent
    def publisher(self) -> Agent:
        return Agent(
            config=self.agents_config["publisher"],
            tools=[PublisherTool()],
            verbose=True,
        )

    @task
    def analyze_topic(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_topic"],
        )

    @task
    def write_content(self) -> Task:
        return Task(
            config=self.tasks_config["write_content"],
        )

    @task
    def audit_content(self) -> Task:
        return Task(
            config=self.tasks_config["audit_content"],
        )

    @task
    def design_content(self) -> Task:
        return Task(
            config=self.tasks_config["design_content"],
            output_file="tmp_article.html",
        )

    @task
    def template_content(self) -> Task:
        return Task(
            config=self.tasks_config["template_content"],
            output_file="tmp_article.html",
        )

    @task
    def publish_task(self) -> Task:
        return Task(
            config=self.tasks_config["publish_task"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AutowxGzh crew"""

        if self.use_template:
            no_use_agent = "微信排版专家"
            no_use_task = "design_content"
        else:
            no_use_agent = "模板选择和填充专家"
            no_use_task = "template_content"

        self.agents = [agent for agent in self.agents if agent.role != no_use_agent]
        self.tasks = [task for task in self.tasks if task.name != no_use_task]

        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
