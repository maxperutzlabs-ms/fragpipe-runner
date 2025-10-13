import logging
import pathlib

logger = logging.getLogger(__name__)


def prepare_workflow_from_template(
    workflow_template: pathlib.Path | str,
    workflow_output: pathlib.Path | str,
    database_path: pathlib.Path | str,
):
    """Prepare a FragPipe workflow file from a template by updating the database path.

    Args:
        workflow_template: Path to the template workflow file.
        workflow_output: Path to save the updated workflow file.
        database_path: Path to the FASTA database file to set in the workflow.
    """
    normalized_db_path = _resolve_path(database_path)
    updated_workflow = []
    database_path_found = False

    logger.info(f"Updating database entry in workflow template '{workflow_template}'.")

    with open(workflow_template) as template_file:
        for line in template_file.readlines():
            if line.startswith("database.db-path="):
                logger.debug(
                    f"Replacing line: {line.strip()} with "
                    f"database.db-path={normalized_db_path}"
                )

                updated_workflow.append(f"database.db-path={normalized_db_path}\n")
                database_path_found = True
            else:
                updated_workflow.append(line)

    if not database_path_found:
        logger.debug(
            "No existing database.db-path found, adding line: "
            f"database.db-path={normalized_db_path}"
        )
        updated_workflow.append(f"\ndatabase.db-path={normalized_db_path}")

    with open(workflow_output, "w") as workflow_file:
        workflow_file.write("".join(updated_workflow))


def _resolve_path(path: pathlib.Path | str) -> str:
    return pathlib.Path(path).resolve().as_posix()
