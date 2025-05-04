import re
import ast # For safely evaluating string representations of Python literals
from typing import List, Dict, Any, Type, Union, Optional
from urllib.parse import urlparse

from crewai.tools import BaseTool
from pydantic import BaseModel, Field # Use standard Pydantic (v2) for schema compatibility

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
    description: str = "Searches for jobs based on a query and returns a list of structured results (dictionaries containing 'link', 'title', 'snippet') pre-filtered to likely be direct job postings (excluding PDFs and known search result pages)."
    args_schema: Type[BaseModel] = SearchAndFilterSchema # type: ignore # Avoid mypy issue with Pydantic v1 BaseTool
    search_tool: BaseTool # The actual search tool (e.g., SerperDevTool) is passed in

    def _run(self, query: str) -> Union[List[Dict[str, Any]], str]:
        """
        Executes the search using the wrapped tool and filters the results.
        Attempts to parse structured output (list of dicts) from the search tool.
        Falls back to regex URL extraction if parsing fails.
        Returns a list of filtered result dictionaries or an error string.
        """
        raw_results: List[Dict[str, Any]] = []
        try:
            # SerperDevTool's run method returns a string by default.
            raw_results_output = self.search_tool.run(query)

            # Attempt to parse the string output as a Python literal (list of dicts)
            try:
                evaluated_output = ast.literal_eval(raw_results_output)
                if isinstance(evaluated_output, list):
                     # Assume it's the list of dicts we want
                     raw_results = [item for item in evaluated_output if isinstance(item, dict)]
                     print(f"SearchAndFilterTool: Successfully parsed structured results: {len(raw_results)} items.")
                else:
                    raise ValueError("Parsed output is not a list")
            except (ValueError, SyntaxError, TypeError) as e:
                print(f"SearchAndFilterTool: Could not parse output as list of dicts ({e}). Falling back to URL regex extraction.")
                # Fallback: Extract only URLs using regex
                urls = re.findall(r'https?://[^\s"]+', raw_results_output)
                # Create structure, acknowledge missing context (title/snippet will be missing or None)
                raw_results = [{'link': url, 'title': None, 'snippet': None} for url in urls]
                print(f"SearchAndFilterTool: Extracted {len(raw_results)} potential URLs via regex.")

        except Exception as e:
             print(f"Error during search tool execution: {e}")
             return f"Error during search tool execution: {e}"

        # Try filtering the results
        try:
            filtered_results = []
            for result in raw_results:
                link = result.get('link')
                if not link:
                    continue

                # 1. Exclude PDFs
                parsed_url = urlparse(link) # type: ignore # urlparse can take Optional[str]
                if parsed_url.path and parsed_url.path.lower().endswith(".pdf"):
                    print(f"Filtering out PDF: {link}")
                    continue

                # 2. Exclude known search result pages (case-insensitive)
                if any(re.search(pattern, link, re.IGNORECASE) for pattern in SEARCH_PAGE_PATTERNS):
                    print(f"Filtering out search page: {link}")
                    continue

                # Optional: Prioritize known job page patterns (could be added here if needed)
                # if not any(re.search(pattern, link) for pattern in JOB_PAGE_PATTERNS):
                #     continue # Be stricter: only allow known good patterns

                # If it passes filters, add the original result dictionary
                filtered_results.append(result)

            print(f"SearchAndFilterTool: Returning {len(filtered_results)} filtered results as a list.")
            # Return the actual list of dictionaries
            return filtered_results

        except Exception as e: # Catch errors during the filtering process
            print(f"Error during filtering in SearchAndFilterTool: {e}")
            # Return an error string if filtering fails
            return f"Error during filtering: {e}"
