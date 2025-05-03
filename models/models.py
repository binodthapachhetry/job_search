from typing import List, Optional

from pydantic import BaseModel


class Job(BaseModel):
    id: Optional[str]
    location: Optional[str]
    title: Optional[str] 
    company: Optional[str]
    description: Optional[str]
    responsibilities: Optional[str] # Added field
    requirements: Optional[str] # Added field
    jobProvider: Optional[str]
    url: Optional[str]
    rating: Optional[int] 
    rating_description: Optional[str] 
    company_rating: Optional[int] 
    company_rating_description: Optional[str]  

    
class JobResults(BaseModel): 
    jobs: Optional[List[Job]]
