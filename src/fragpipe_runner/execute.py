import logging
import os
import pathlib
import subprocess
import time

logger = logging.getLogger(__name__)


def run_fragpipe(
    fragpipe_root: pathlib.Path | str,
    workflow_path: pathlib.Path | str,
    manifest_path: pathlib.Path | str,
    output_dir: pathlib.Path | str,
    ram: int = 0,
    threads: int = -1,
    logger: logging.Logger | None = None,
) -> bool:
    """Run FragPipe in headless mode with the specified parameters.

    If FragPipe fails to create a log file, a log file will be created manually using
    the redirected stdout.

    Tested with FragPipe v23.

    Args:
        fragpipe_root: Path to FragPipe installation directory
        workflow_path: Path to workflow file
        manifest_path: Path to manifest file
        output_dir: Path to analysis output directory
        ram: The maximum allowed memory size for FragPipe to use (in GB). Set to 0 to
            let FragPipe decide.
        threads: The number of CPU threads for FragPipe to use. Set it -1 to let
            FragPipe decide.
        logger: Logger for logging messages. If None, a default logger will be used.

    Returns:
        True if FragPipe completed successfully, False otherwise
    """

    if logger is None:
        logger = logging.getLogger(__name__)

    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    redirected_log_path = output_dir / "fragpipe_stdout_redirect.log"

    if os.name == "nt":
        executable_name = "fragpipe.bat"
    elif os.name == "posix":
        executable_name = "fragpipe"
    else:
        raise OSError(f"Unsupported operating system: {os.name}")

    fragpipe_exec_path = pathlib.Path(fragpipe_root) / "bin" / executable_name
    if not fragpipe_exec_path.exists():
        raise Exception(
            f"FragPipe executable file not found at {fragpipe_exec_path}. "
            "Please check the path."
        )

    cmd = [
        fragpipe_exec_path.as_posix(),
        "--headless",
        "--workflow",
        pathlib.Path(workflow_path).resolve().as_posix(),
        "--manifest",
        pathlib.Path(manifest_path).resolve().as_posix(),
        "--workdir",
        pathlib.Path(output_dir).resolve().as_posix(),
        "--ram",
        str(ram),
        "--threads",
        str(threads),
    ]
    logger.info(f"Running FragPipe with output directory '{output_dir}'")

    try:
        start_time = time.time()
        with open(redirected_log_path, "w") as redirected_log_file:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=redirected_log_file,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
            )
        duration = (time.time() - start_time) / 60
        logger.info(f"FragPipe completed successfully in {duration:.2f} minutes.")
        if result.stderr:
            logger.debug(f"FragPipe stderr output:\n{result.stderr}")

        latest_log_file = _find_latest_log_file(output_dir)
        if latest_log_file is None:
            logger.debug(
                f"No FragPipe log file found in '{output_dir}'. Using redirected log "
                "to manually create a log file."
            )
            time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            official_log_path = output_dir / f"log_{time_stamp}.txt"
            redirected_log_path.rename(official_log_path)
        else:
            redirected_log_path.unlink()
        return True
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Error running FragPipe: {e}\nError output:\n{e.stderr}\n"
            f"A partial log file may be found at '{redirected_log_path}'"
        )
        return False


def search_results_exist(output_dir: pathlib.Path | str) -> bool:
    """Check if FragPipe search results exist in the specified output directory.

    Checks for the presence of a FragPipe log file or a combined_protein.tsv file.

    Args:
        output_dir: Path to FragPipe output directory

    Returns:
        True if search results exist, False otherwise
    """
    output_dir = pathlib.Path(output_dir)
    combined_protein_file = output_dir / "combined_protein.tsv"
    if not output_dir.exists() or not output_dir.is_dir():
        return False

    if _find_latest_log_file(output_dir) is not None:
        return True
    elif combined_protein_file.exists():
        logger.debug(
            f"FragPipe search results found in '{output_dir}', but no log file found."
        )
        return True
    else:
        return False


def clean_up_rawfile_directory(rawfile_dir: pathlib.Path):
    """Clean up FragPipe temporary files in the specified rawfile directory.

    Removes temporary files with extensions such as '.mzBIN' and '_uncalibrated.mzML'.

    Args:
        rawfile_dir: The rawfile directory to clean up.
    """
    temp_file_patterns = [
        ".mzBIN",
        "_uncalibrated.mzML",
    ]
    if not rawfile_dir.exists():
        logger.warning(f"Raw directory {rawfile_dir} does not exist.")
        return
    if not rawfile_dir.is_dir():
        logger.warning(f"Raw directory {rawfile_dir} is not a directory.")
        return

    temp_files: list[pathlib.Path] = []
    for pattern in temp_file_patterns:
        temp_files.extend(rawfile_dir.rglob(f"*{pattern}"))

    logger.debug(
        f"Trying to remove {len(temp_files)} temporary FragPipe files in {rawfile_dir}."
    )
    if not temp_files:
        return

    for temp_file in temp_files:
        temp_file.unlink()
    logger.info(f"Deleted {len(temp_files)} temporary FragPipe files in {rawfile_dir}.")


def _find_latest_log_file(output_dir: pathlib.Path) -> pathlib.Path | None:
    """Find the latest FragPipe log file in the specified output directory.

    Args:
        output_dir: Path to FragPipe output directory

    Returns:
        Path to the latest log file, or None if no log files are found
    """
    log_files = [f for f in output_dir.glob("log_*.txt") if len(f.name) == 27]
    if log_files:
        return sorted(log_files, reverse=True)[0]
    return None
