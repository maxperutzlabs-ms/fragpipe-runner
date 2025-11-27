# FragPipe-Runner

## About

A Python library to simplify and support the execution of FragPipe when running in command-line mode.

It provides an interface to add a FASTA path to an existing workflow, handling the generation of manifest files from SDRF, and executing FragPipe.

## Compatibility

The current version of fragpipe-runner has been tested with FragPipe version 23 on Windows 11, running an LFQ workflow with DDA data.

## Installation

You can install the package from PyPI using pip:

```bash
pip install fragpipe-runner
```

## Usage

Here is a simple example of how to use the library to run a FragPipe workflow with a specified manifest file:

```python
import fragpipe_runner

fragpipe_runner.run_fragpipe(
    fragpipe_dir="path/to/fragpipe_23-1",
    workflow_path="path/to/workflow.workflow",
    manifest_path="path/to/manifest.fp-manifest",
    output_directory="path/to/output/directory",
)
```

To create a manifest file from an SDRF file, you can use the following code (note that experiments using isobaric mass tags like TMT are not yet supported):

```python
fragpipe_runner.manifest.sdrf_to_manifest(
    sdrf_path="path/to/sdrf_file.tsv",
    data_type="DDA",
    manifest_filepath="output/path/of/manifest.fp-manifest",
    experiment_field="factor value[condition]",
    replicate_field="characteristics[biological replicate]",
)

fragpipe_runner.manifest.update_rawfile_paths_in_manifest(
    manifest_filepath="output/path/of/manifest.fp-manifest",
    rawfile_directory="directory/containing/rawfiles"
)
```
