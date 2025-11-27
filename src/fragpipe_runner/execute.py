"""Module for executing FragPipe in headless mode."""

import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

LOGGER = logging.getLogger(__name__)


def run_fragpipe(
    fragpipe_root: pathlib.Path | str,
    workflow_path: pathlib.Path | str,
    manifest_path: pathlib.Path | str,
    output_dir: pathlib.Path | str,
    ram: int = 0,
    threads: int = -1,
    temp_dir: pathlib.Path | str | None = None,
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
        threads: The number of CPU threads for FragPipe to use. Set to -1 to let
            FragPipe decide (by default the number of cores - 1).
        temp_dir: Path to temporary directory to use for FragPipe output. If None,
            FragPipe output will be written directly to 'output_dir'. If provided,
            FragPipe output will first be written to the temporary directory, and then
            moved to 'output_dir' after FragPipe finishes. This can be useful to avoid
            crashes due to too long file paths on Windows systems. The temporary
            directory will be deleted after the output has been moved.
        logger: Logger for logging messages. If None, the module-level logger is used.

    Returns:
        True if FragPipe completed successfully, False otherwise

    Raises:
        FileNotFoundError: If the FragPipe executable file is not found.
    """

    if logger is None:
        logger = LOGGER

    if os.name == "nt":
        executable_name = "fragpipe.bat"
    elif os.name == "posix":
        executable_name = "fragpipe"
    else:
        raise OSError(f"Unsupported operating system: {os.name}")

    fragpipe_exec_path = pathlib.Path(fragpipe_root) / "bin" / executable_name
    if not fragpipe_exec_path.exists():
        raise FileNotFoundError(
            f"FragPipe executable file not found at {fragpipe_exec_path}. "
            "Please check the path."
        )

    final_output_path = pathlib.Path(output_dir)
    final_output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Running FragPipe with output directory '{final_output_path}'")

    if temp_dir is None:
        output_path = final_output_path
    else:
        temp_dir_path = pathlib.Path(temp_dir)
        temp_dir_existed = temp_dir_path.exists()
        if not temp_dir_existed:
            temp_dir_path.mkdir(parents=True, exist_ok=True)
        temp_output = tempfile.TemporaryDirectory(dir=temp_dir_path)
        output_path = pathlib.Path(temp_output.name)
        output_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using temporary directory '{output_path}' for FragPipe output.")

    cmd = [
        fragpipe_exec_path.as_posix(),
        "--headless",
        "--workflow",
        pathlib.Path(workflow_path).resolve().as_posix(),
        "--manifest",
        pathlib.Path(manifest_path).resolve().as_posix(),
        "--workdir",
        pathlib.Path(output_path).resolve().as_posix(),
        "--ram",
        str(ram),
    ]
    if threads > 0:
        cmd.extend(["--threads", str(threads)])

    # The redirected log file is never created in the temp output directory
    redirected_log_path = final_output_path / "fragpipe_stdout_redirect.log"
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
        execution_successful = True
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Error running FragPipe: {e}\nError output:\n{e.stderr}\n"
            f"A partial log file may be found at '{redirected_log_path}'"
        )
        execution_successful = False
    finally:
        if temp_dir is not None:
            try:
                _move_and_replace_folder_contents(output_path, final_output_path)
            except Exception as e:
                logger.error(f"Failed to move files from temp directory: {e}")
            temp_output.cleanup()
            if not temp_dir_existed:
                try:
                    temp_dir_path.rmdir()
                except OSError:
                    logger.debug(
                        f"Temporary directory '{temp_dir_path}' could not be removed "
                        "because it is not empty."
                    )

    # If a temp directory was used, check the log only after moving the files from temp
    latest_log_file = _find_latest_log_file(final_output_path)
    if latest_log_file is None:
        logger.debug(
            f"No FragPipe log file found in output directory '{final_output_path}'."
            " Using redirected log to manually create a log file."
        )
        time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        official_log_path = final_output_path / f"log_{time_stamp}.txt"
        redirected_log_path.rename(official_log_path)
    else:
        redirected_log_path.unlink()

    return execution_successful


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
        LOGGER.debug(
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
        LOGGER.warning(f"Raw directory {rawfile_dir} does not exist.")
        return
    if not rawfile_dir.is_dir():
        LOGGER.warning(f"Raw directory {rawfile_dir} is not a directory.")
        return

    temp_files: list[pathlib.Path] = []
    for pattern in temp_file_patterns:
        temp_files.extend(rawfile_dir.rglob(f"*{pattern}"))

    LOGGER.debug(
        f"Trying to remove {len(temp_files)} temporary FragPipe files in {rawfile_dir}."
    )
    if not temp_files:
        return

    for temp_file in temp_files:
        temp_file.unlink()
    LOGGER.info(f"Deleted {len(temp_files)} temporary FragPipe files in {rawfile_dir}.")


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


def _move_and_replace_folder_contents(
    source_dir: pathlib.Path | str,
    destination_dir: pathlib.Path | str,
) -> None:
    """Moves the source directory to the destination directory, replacing existing
    files and merging folders as needed.

    Args:
        source_dir: Path of the source directory.
        destination_dir: Path of the destination directory.
    """
    source_path = pathlib.Path(source_dir)
    destination_path = pathlib.Path(destination_dir)
    destination_path.mkdir(parents=True, exist_ok=True)

    for item_path in source_path.iterdir():
        dest_item_path = destination_path / item_path.name

        if item_path.is_dir() and dest_item_path.is_dir():
            _move_and_replace_folder_contents(item_path, dest_item_path)
            item_path.rmdir()
            continue

        if dest_item_path.exists():
            if dest_item_path.is_dir():
                shutil.rmtree(dest_item_path)
            else:
                dest_item_path.unlink()

        shutil.move(item_path, dest_item_path)
    source_path.rmdir()
