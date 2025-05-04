import re
from typing import List, Dict, Any, Type, Union
from urllib.parse import urlparse

from crewai_tools import BaseTool
from pydantic.v1 import BaseModel, Field # Use pydantic.v1 for BaseTool compatibility

# Define known patterns for search result pages (add more as needed)
SEARCH_PAGE_PATTERNS = [
    r"indeed\.com/q-",
    r"linkedin\.com/jobs/search",
    r"glassdoor\.com/Job/jobs\.htm", # Example for Glassdoor search
    # Add other patterns like ziprecruiter.com/jobs-search, etc.
]

# Define patterns for likely direct job pages (optional, for prioritization if needed)
# JOB_PAGE_PATTERNS = [
#     r"indeed\.com/viewjob",
#     r"linkedin\.com/jobs/view/",
#     r"greenhouse\.io/",
#     r"lever\.co/",
# ]

class SearchAndFilterSchema(BaseModel):
    query: str = Field(description="The search query for finding jobs.")

class SearchAndFilterTool(BaseTool):
    name: str = "Filtered Job Search"
    description: str = "Searches for jobs based on a query and returns a list of structured results (including URLs) pre-filtered to likely be direct job postings (excluding PDFs and known search result pages)."
    args_schema: Type[BaseModel] = SearchAndFilterSchema
    search_tool: BaseTool # The actual search tool (e.g., SerperDevTool) is passed in

    def _run(self, query: str) -> Union[List[Dict[str, Any]], str]:
        """
        Executes the search using the wrapped tool and filters the results.
        Returns a list of filtered result dictionaries or an error string.
        """
        try:
            # SerperDevTool's run method returns a string by default.
            # We need to process this string if it contains structured data (like JSON)
            # or extract links if it's just text.
            raw_results_output = self.search_tool.run(query)

            # Attempt to parse if it looks like JSON, otherwise treat as text
            # Note: SerperDevTool often returns a string representation of a list of dicts.
            # A more robust approach might involve trying json.loads or ast.literal_eval
            # For simplicity here, we'll rely on regex extraction if it's not easily parsed.
            # Let's assume for now the agent using this tool gets the structured list.
            # If the underlying tool *always* returns a string, the agent calling *this*
            # tool needs to handle that string output. Let's refine the description.
            # Re-adjusting: Let's assume the tool *can* return structured data if available,
            # but we must handle the string case from SerperDevTool.

            # SerperDevTool returns a string. We need to extract links and potentially other info.
            # A simple regex for URLs:
            urls = re.findall(r'https?://[^\s"]+', raw_results_output)
            # Create a basic structure for filtering
            raw_results = [{'link': url} for url in urls] # We lose title/snippet here

            print(f"SearchAndFilterTool: Found {len(raw_results)} potential URLs in raw output.")

            filtered_results = []
            for result in raw_results:
                link = result.get('link')
                if not link:
                    continue

                # 1. Exclude PDFs
                parsed_url = urlparse(link)
                if parsed_url.path.lower().endswith(".pdf"):
                    print(f"Filtering out PDF: {link}")
                    continue

                # 2. Exclude known search result pages
                if any(re.search(pattern, link, re.IGNORECASE) for pattern in SEARCH_PAGE_PATTERNS):
                    print(f"Filtering out search page: {link}")
                    continue

                # Optional: Prioritize known job page patterns (could be added here if needed)
                # if not any(re.search(pattern, link) for pattern in JOB_PAGE_PATTERNS):
                #     continue # Be stricter: only allow known good patterns

                # If it passes filters, add the original structure (just the link in this case)
                filtered_results.append(result)

            print(f"SearchAndFilterTool: Returning {len(filtered_results)} filtered results.")
            # Return the filtered list of dicts (currently just {'link': url})
            # The agent using this will get this list.
            # We might need to adjust the expected output format later if more context is needed.
            # Returning a string representation might be safer for CrewAI processing.
            return str(filtered_results) # Return as string for compatibility

        except Exception as e:
            print(f"Error in SearchAndFilterTool: {e}")
            return f"Error during search and filtering: {e}"
