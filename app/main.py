from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from . import models, schemas, database
from .agent.graph import create_agent_graph
from .agent.state import AppState

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="LangGraph Autopilot")


def run_agent_task(job_id: int):
    """
    This function now runs with only the job_id.
    It's responsible for the entire lifecycle of the job.
    """
    print(f"---AGENT TASK STARTED FOR JOB {job_id}---")
    db = next(database.get_db())

    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        print(f"[ERROR] Job {job_id} could not be found to start agent. Exiting.")
        db.close()
        return

    job.status = models.JobStatus.RUNNING
    db.commit()

    agent = create_agent_graph()
    initial_state = AppState(issue_url=job.issue_url)

    final_state = None
    try:
        final_state = agent.invoke(initial_state)
        print("---AGENT RUN COMPLETED---")
        print("Final Agent State:")
        import json

        print(json.dumps(final_state, indent=2))
        job.status = models.JobStatus.COMPLETED
    except Exception as e:
        print(f"---AGENT RUN FAILED: {e}---")
        job.status = models.JobStatus.FAILED
    finally:
        db.commit()
        db.close()


@app.post("/api/v1/jobs", response_model=schemas.JobAccepted, status_code=202)
def create_job(
    job_request: schemas.JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
):
    """
    This endpoint now does three things simply:
    1. Creates the Job record in the DB with a "pending" status.
    2. Schedules the background task, passing it the new job's ID.
    3. Returns immediately.
    """
    new_job = models.Job(issue_url=str(job_request.issue_url))
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    background_tasks.add_task(run_agent_task, new_job.id)

    return {"message": "Job accepted", "job_id": new_job.id}


@app.get("/api/v1/jobs/{job_id}", response_model=schemas.Job)
def get_job(job_id: int, db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
