# Module to help connect to databricks
from loguru import logger
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Task, PythonWheelTask
from databricks.sdk.service.compute import Library, State
from serra.aws import upload_file_to_bucket, write_json_s3
from serra.utils import get_path_to_user_configs_folder
from serra.config import (
    DATABRICKS_HOST, 
    DATABRICKS_TOKEN, 
    DATABRICKS_CLUSTER_ID,
    PATH_TO_WHEEL,
    S3_WHEEL_PATH
)

# Global Client setup
w = WorkspaceClient(
  host  = DATABRICKS_HOST,
  token = DATABRICKS_TOKEN
)

def upload_wheel_to_bucket():
    # TODO: Add code to recreate wheel
    logger.info(f"Uploading wheel from {PATH_TO_WHEEL} to AWS")
    upload_file_to_bucket(PATH_TO_WHEEL)

def create_job(config_name):
    """Use like this: submit_job("StripeExample")
    """

    # Upload the config file to aws
    logger.info("Uploading config to AWS")
    config_path = f"{get_path_to_user_configs_folder()}/{config_name}.yml"
    upload_file_to_bucket(config_path)
    
    # Create the job on databricks
    logger.info("Creating databricks job")
    job_name = config_name

    j = w.jobs.create(
        name=job_name,
        tasks = [
            Task(
                description = "Basic new job",
                existing_cluster_id = DATABRICKS_CLUSTER_ID,
                python_wheel_task=PythonWheelTask(entry_point="serra_databricks",
                                                package_name="serra",
                                                parameters=[config_name]),
                libraries=[Library(whl=S3_WHEEL_PATH)],
                task_key="my-task"
            )
    ]
    )
    logger.info(f"View job at {w.config.host}/#job/{j.job_id}")
    return j

def restart_server():
    logger.info("Restarting cluster")
    w.clusters.ensure_cluster_is_running(DATABRICKS_CLUSTER_ID)

    logger.info("Uninstalling packages")
    w.libraries.uninstall(cluster_id=DATABRICKS_CLUSTER_ID,
                          libraries=[Library(whl=S3_WHEEL_PATH)])
    
    current_cluster_state = w.clusters.get(DATABRICKS_CLUSTER_ID).state

    if current_cluster_state != State.TERMINATED:
        w.clusters.restart_and_wait(DATABRICKS_CLUSTER_ID)
    
    w.clusters.ensure_cluster_is_running(DATABRICKS_CLUSTER_ID)

    logger.info("Finished restarting")