from pydantic import BaseModel, HttpUrl
from typing import Optional
from .models import JobStatus


class JobCreate(BaseModel):
    issue_url: HttpUrl


class Job(BaseModel):
    id: int
    issue_url: HttpUrl
    status: JobStatus
    pull_request_url: Optional[str] = None

    class Config:
        from_attributes = True
