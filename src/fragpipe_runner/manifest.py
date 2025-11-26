import logging
import pathlib

import pandas as pd

logger = logging.getLogger(__name__)


def sdrf_to_manifest(
    sdrf_filepath: pathlib.Path | str,
    data_type: str,
    manifest_filepath: pathlib.Path | str | None = None,
    manifest_filename: str = "manifest.fp-manifest",
    experiment_field: str = "comment[data file]",
    replicate_field: str = "characteristics[biological replicate]",
) -> None:
    """Convert an SDRF file to a FragPipe-compatible '.fp-manifest' file.

    Format of the tab-separated FragPipe manifest file:
    rawfile path | experiment name | bio replicate | data type

    Args:
        sdrf_filepath: Path to the SDRF file.
        data_type: Acquisition data type, one of "DDA", "DDA+", "DIA", "DIA-Quant",
            "DIA-Lib" or "GPF-DIA".
        manifest_filepath: Filepath to save the FragPipe manifest file. If None, saves
            to the same directory as the SDRF file using the 'manifest_filename'.
        manifest_filename: Filename to use for the created manifest if
            'manifest_filepath' is None. Default is "manifest.fp-manifest".
        experiment_field: Name of the SDRF column to use for the experiment information.
        replicate_field: Name of the SDRF column to use for the replicate information.
    """
    supported_data_types = ["DDA", "DDA+", "DIA", "DIA-Quant", "DIA-Lib", "GPF-DIA"]

    logger.info(f"Converting SDRF file '{sdrf_filepath}' to FragPipe manifest.")
    if data_type not in supported_data_types:
        raise ValueError(
            f"Unsupported acquisition type: {data_type}. "
            f"Supported types are: {supported_data_types}."
        )
    if manifest_filepath is None:
        manifest_filepath = pathlib.Path(sdrf_filepath).parent / manifest_filename
        logger.debug(f"No 'manifest_filepath' provided, using '{manifest_filepath}'")

    sdrf_table = pd.read_csv(sdrf_filepath, sep="\t")
    manifest = sdrf_table[
        [
            "comment[data file]",
            experiment_field,
            replicate_field,
        ]
    ].drop_duplicates()
    manifest["data type"] = data_type

    logger.info(f"Writing FragPipe manifest to '{manifest_filepath}'")
    manifest.to_csv(manifest_filepath, sep="\t", index=False, header=False)


def update_rawfile_paths_in_manifest(
    manifest_filepath: pathlib.Path | str,
    rawfile_directory: pathlib.Path | str | None = None,
) -> pd.DataFrame:
    """Update the rawfile paths in a FragPipe manifest file.

    Args:
        manifest_filepath: Path to the FragPipe manifest file.
        rawfile_directory: Directory where the rawfiles are located. If None, uses the
            directory of the manifest file.
    """
    logger.info(f"Updating rawfile paths in manifest '{manifest_filepath}'")
    if rawfile_directory is None:
        rawfile_directory = pathlib.Path(manifest_filepath).parent
        logger.debug(
            "No 'rawfile_directory' provided, using manifest "
            f"directory {rawfile_directory}"
        )
    rawfile_directory = pathlib.Path(rawfile_directory).resolve()

    manifest = pd.read_csv(manifest_filepath, sep="\t", header=None)
    rawfile_paths = [
        rawfile_directory / pathlib.Path(p).name for p in manifest.iloc[:, 0]
    ]
    manifest.iloc[:, 0] = [p.as_posix() for p in rawfile_paths]
    manifest.to_csv(manifest_filepath, sep="\t", index=False, header=False)
