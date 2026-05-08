from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from scripts.env_config import env, load_dotenv


load_dotenv()

# Bonus C: script sync thủ công Bedrock Knowledge Base sau khi markdown docs được update trên S3.
DEFAULT_PROFILE = None if os.getenv("AWS_EXECUTION_ENV") else env("AWS_PROFILE")
DEFAULT_REGION = env("AWS_REGION", "us-east-1")
DEFAULT_KB_ID = env("BEDROCK_KB_ID", required=True)
DEFAULT_DATA_SOURCE_ID = env("BEDROCK_DATA_SOURCE_ID", required=True)
POLL_SECONDS = int(os.getenv("KB_SYNC_POLL_SECONDS", "5"))
TIMEOUT_SECONDS = int(os.getenv("KB_SYNC_TIMEOUT_SECONDS", "600"))
TERMINAL_STATUSES = {"COMPLETE", "FAILED", "STOPPED"}


def bedrock_agent_client():
    # Dùng profile local khi chạy máy cá nhân; khi deploy Lambda/ECS thì dùng IAM role runtime.
    session = (
        boto3.Session(profile_name=DEFAULT_PROFILE, region_name=DEFAULT_REGION)
        if DEFAULT_PROFILE
        else boto3.Session(region_name=DEFAULT_REGION)
    )
    return session.client("bedrock-agent")


def latest_running_job(client) -> str | None:
    # Nếu AWS đang có ingestion job chạy, dùng lại job đó thay vì tạo job trùng.
    response = client.list_ingestion_jobs(
        knowledgeBaseId=DEFAULT_KB_ID,
        dataSourceId=DEFAULT_DATA_SOURCE_ID,
        maxResults=10,
    )
    for job in response.get("ingestionJobSummaries", []):
        if job.get("status") in {"STARTING", "IN_PROGRESS"}:
            return job["ingestionJobId"]
    return None


def start_or_reuse_ingestion_job(client) -> tuple[str, bool]:
    # StartIngestionJob là thao tác chính cho Bonus C; ConflictException nghĩa là job đang chạy.
    try:
        response = client.start_ingestion_job(
            knowledgeBaseId=DEFAULT_KB_ID,
            dataSourceId=DEFAULT_DATA_SOURCE_ID,
            description=f"Manual W4 Bonus C sync - {datetime.now(timezone.utc).isoformat()}",
        )
        return response["ingestionJob"]["ingestionJobId"], True
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "ConflictException":
            raise
        running_job_id = latest_running_job(client)
        if not running_job_id:
            raise
        return running_job_id, False


def get_job(client, job_id: str) -> dict:
    # Poll trạng thái ingestion job để screenshot chứng minh sync đã COMPLETE.
    return client.get_ingestion_job(
        knowledgeBaseId=DEFAULT_KB_ID,
        dataSourceId=DEFAULT_DATA_SOURCE_ID,
        ingestionJobId=job_id,
    )["ingestionJob"]


def main() -> int:
    # In ra đầy đủ KB ID, Data Source ID và status để dùng trực tiếp làm evidence.
    print("Bonus C — Bedrock Knowledge Base Sync")
    print(f"Profile: {DEFAULT_PROFILE or 'default/runtime'}")
    print(f"Region: {DEFAULT_REGION}")
    print(f"Knowledge Base ID: {DEFAULT_KB_ID}")
    print(f"Data Source ID: {DEFAULT_DATA_SOURCE_ID}")
    print("Action: StartIngestionJob")

    client = bedrock_agent_client()
    job_id, started_new = start_or_reuse_ingestion_job(client)
    print(f"Ingestion Job ID: {job_id}")
    print(f"Job source: {'new job started' if started_new else 'existing running job reused'}")

    deadline = time.monotonic() + TIMEOUT_SECONDS
    while True:
        job = get_job(client, job_id)
        status = job["status"]
        started_at = job.get("startedAt")
        updated_at = job.get("updatedAt")
        stats = job.get("statistics", {})
        print(
            "Status: "
            f"{status} | startedAt={started_at} | updatedAt={updated_at} | statistics={stats}"
        )

        if status in TERMINAL_STATUSES:
            if status == "COMPLETE":
                print("Result: COMPLETE — Knowledge Base sync finished successfully.")
                return 0
            print(f"Result: {status} — Knowledge Base sync did not complete successfully.")
            failure_reasons = job.get("failureReasons") or []
            if failure_reasons:
                print("Failure reasons:")
                for reason in failure_reasons:
                    print(f"- {reason}")
            return 1

        if time.monotonic() >= deadline:
            print(f"Result: TIMEOUT after {TIMEOUT_SECONDS}s waiting for ingestion job.")
            return 2

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
