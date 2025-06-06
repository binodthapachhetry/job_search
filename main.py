import json
import os
from textwrap import dedent

import os
from textwrap import dedent

from crewai import Crew, Process, LLM
from crewai_tools import FileReadTool, SerperDevTool, SpiderTool
from dotenv import load_dotenv # Used to load environment variables
from pydantic import ValidationError

from custom_tools import SearchAndFilterTool # Import the new custom tool
from agents_factory import AgentsFactory
from models.models import JobResults
from tasks_factory import TasksFactory

load_dotenv()


class JobSearchCrew:
    def __init__(self, query: str):
        self.query = query

    def run(self):
        # Define the LLM AI Agents will utilize
        llm = LLM(
            model="gemini/gemini-2.0-flash-exp",
            temperature=0,
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            verbose=True
            )

        # Intialize all tools needed
        resume_file_read_tool = FileReadTool(file_path="data/sample_resume.txt")
        # Instantiate the base search tool
        base_search_tool = SerperDevTool(n_results=50)
        # Instantiate the custom tool, wrapping the base search tool
        search_and_filter_tool = SearchAndFilterTool(search_tool=base_search_tool)

        # Instantiate SpiderTool - uses Firecrawl service. Requires FIRECRAWL_API_KEY in .env
        # It handles JS rendering and returns cleaner content (often Markdown).
        scrape_tool = SpiderTool(
            # Default mode is 'scrape', which is suitable here. No CSS selector needed.
        )

        # Create the Agents
        agent_factory = AgentsFactory("configs/agents.yml")
        job_search_expert_agent = agent_factory.create_agent(
            "job_search_expert", tools=[search_and_filter_tool, scrape_tool], llm=llm # Use FILTERED search and spider tools
        )
        # job_filtering_expert_agent = agent_factory.create_agent(
        #     "job_filtering_expert", tools=None, llm=llm # No tools needed, just context analysis
        # )
        job_rating_expert_agent = agent_factory.create_agent(
            "job_rating_expert", tools=[resume_file_read_tool], llm=llm
        )
        # company_rating_expert_agent = agent_factory.create_agent(
        #     "company_rating_expert", tools=[search_tool], llm=llm
        # )
        summarization_expert_agent = agent_factory.create_agent(
            "summarization_expert", tools=None, llm=llm
        )

        # Response model schema
        response_schema = json.dumps(JobResults.model_json_schema(), indent=2)

        # Create the Tasks
        tasks_factory = TasksFactory("configs/tasks.yml")
        job_search_task = tasks_factory.create_task(
            "job_search", job_search_expert_agent, query=self.query
        )
        # filter_jobs_task = tasks_factory.create_task(
        #     "filter_jobs", job_filtering_expert_agent, query=self.query # Pass query for relevance check
        # )
        job_rating_task = tasks_factory.create_task(
            "job_rating", job_rating_expert_agent
        )
        # evaluate_company_task = tasks_factory.create_task(
        #     "evaluate_company",
        #     company_rating_expert_agent,
        #     output_schema=response_schema,
        # )
        structure_results_task = tasks_factory.create_task(
            "structure_results",
            summarization_expert_agent,
            output_schema=response_schema,
        )

        # Assemble the Crew
        crew = Crew(
            agents=[
                job_search_expert_agent,
                # job_filtering_expert_agent, # Added filtering agent
                job_rating_expert_agent,
                # company_rating_expert_agent,
                summarization_expert_agent,
            ],
            tasks=[
                job_search_task,
                # filter_jobs_task, # Added filtering task
                job_rating_task,
                # evaluate_company_task,
                structure_results_task,
            ],
            verbose=1,
            process=Process.sequential,
        )

        result = crew.kickoff()
        return result


if __name__ == "__main__":
    print("## Welcome to Job Search Crew")
    print("-------------------------------")
    query = input(
        dedent("""
      Provide the list of characteristics for the job you are looking for: 
    """)
    )

    crew = JobSearchCrew(query)
    result = crew.run()

    print("Validating final result..")
    try:
        validated_result = JobResults.model_validate_json(result)
    except ValidationError as e:
        print(e.json())
        print("Data output validation error, trying again...")

    print("\n\n########################")
    print("## VALIDATED RESULT ")
    print("########################\n")
    print(result)
