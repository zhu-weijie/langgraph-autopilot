from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from . import models, schemas, database
from .agent.graph import create_agent_graph
from .agent.state import AppState

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="LangGraph Autopilot")


def run_agent_task(job_id: int, issue_url: str):
    db = next(database.get_db())
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return

    job.status = models.JobStatus.RUNNING
    db.commit()

    print(f"---STARTING AGENT FOR JOB {job_id}---")
    agent = create_agent_graph()
    initial_state = AppState(issue_url=issue_url)

    try:
        final_state = agent.invoke(initial_state)
        print("---AGENT RUN COMPLETED---", final_state)
        job.status = models.JobStatus.COMPLETED
    except Exception as e:
        print(f"---AGENT RUN FAILED: {e}---")
        job.status = models.JobStatus.FAILED
    finally:
        db.commit()
        db.close()


@app.post("/api/v1/jobs", response_model=schemas.Job, status_code=202)
def create_job(
    job_request: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    new_job = models.Job(issue_url=str(job_request.issue_url))
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    background_tasks.add_task(run_agent_task, new_job.id, str(new_job.issue_url))

    return new_job


@app.get("/api/v1/jobs/{job_id}", response_model=schemas.Job)
def get_job(job_id: int, db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
