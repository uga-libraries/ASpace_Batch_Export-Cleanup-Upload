import json
import os

from pathlib import Path


def set_defaults_file():
    """
    Checks defaults.json file and if there is an error, creates a new defaults.json file and returns the data.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#set_default_file

    Returns:
        json_data (dict): contains all the data for default behavior for the GUI
    """
    create_default_folders()
    clean_eads = str(Path(os.getcwd(), "clean_eads"))
    source_eads = str(Path(os.getcwd(), "source_eads"))
    source_marcs = str(Path(os.getcwd(), "source_marcs"))
    source_pdfs = str(Path(os.getcwd(), "source_pdfs"))
    source_labels = str(Path(os.getcwd(), "source_labels"))
    xtf_default = ["ead_export_default", "_INCLUDE_UNPUB_", "_INCLUDE_DAOS_", "_NUMBERED_CS_", "_USE_EAD3_",
                   "_KEEP_RAW_", "_CLEAN_EADS_", "_OUTPUT_DIR_", "_SOURCE_DIR_", "marc_export_default",
                   "pdf_export_default", "labels_export_default", "ead_cleanup_defaults", "_ADD_EADID_", "_DEL_NOTES_",
                   "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_", "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_",
                   "_CNT_XLINKS_", "_DEL_NMSPCS_", "_DEL_ALLNS_", "as_api", "repo_default", "_REPO_NAME_", "_REPO_ID_",
                   "xtf_default", "xtf_version", "xtf_host", "xtf_remote_path", "xtf_local_path", "xtf_indexer_path",
                   "_REINDEX_AUTO_"]
    defaults_keys = []
    try:
        with open("defaults.json", "r") as DEFAULTS:
            json_data = json.load(DEFAULTS)
            for key, value in json_data.items():
                if key not in defaults_keys:
                    defaults_keys.append(key)
                if isinstance(value, dict):
                    for value_key in value.keys():
                        if value_key not in defaults_keys:
                            defaults_keys.append(value_key)
            for default in xtf_default:
                if default not in defaults_keys:
                    raise Exception
            DEFAULTS.close()
    except Exception as xtf_error:
        print(xtf_error)
        with open("defaults.json", "w") as DEFAULTS:
            defaults = {"ead_export_default": {"_INCLUDE_UNPUB_": False, "_INCLUDE_DAOS_": True, "_NUMBERED_CS_": True,
                                               "_USE_EAD3_": False, "_KEEP_RAW_": False, "_CLEAN_EADS_": True,
                                               "_OUTPUT_DIR_": clean_eads, "_SOURCE_DIR_": source_eads},
                        "marc_export_default": {"_INCLUDE_UNPUB_": False, "_KEEP_RAW_": False,
                                                "_OUTPUT_DIR_": source_marcs},
                        "pdf_export_default": {"_INCLUDE_UNPUB_": False, "_INCLUDE_DAOS_": True, "_NUMBERED_CS_": True,
                                               "_USE_EAD3_": False, "_KEEP_RAW_": False, "_OUTPUT_DIR_": source_pdfs},
                        "labels_export_default": source_labels,
                        "ead_cleanup_defaults": {"_ADD_EADID_": True, "_DEL_NOTES_": True, "_CLN_EXTENTS_": True,
                                                 "_ADD_CERTAIN_": True, "_ADD_LABEL_": True, "_DEL_CONTAIN_": True,
                                                 "_ADD_PHYSLOC_": True, "_DEL_ATIDS_": True, "_CNT_XLINKS_": True,
                                                 "_DEL_NMSPCS_": True, "_DEL_ALLNS_": True},
                        "as_api": "",
                        "repo_default": {"_REPO_NAME_": "", "_REPO_ID_": ""},
                        "xtf_default": {"xtf_version": True,
                                        "xtf_host": "",
                                        "xtf_remote_path": "",
                                        "xtf_local_path": clean_eads,
                                        "xtf_indexer_path": "",
                                        "_REINDEX_AUTO_": True}}
            dump_defaults = json.dumps(defaults)
            DEFAULTS.write(dump_defaults)
            DEFAULTS.close()
        with open("defaults.json", "r") as DEFAULTS:
            json_data = json.load(DEFAULTS)
            DEFAULTS.close()
    return json_data


def create_default_folders():
    """
    Checks for clean_eads, source_eads, source_labels, source_marcs, and source_pdfs within current working directory.

    Returns:
        None
    """
    # search for existance of a clean_eads folder for ArchivesSpace EAD records
    try:
        current_directory = os.getcwd()
        for root, directories, files in os.walk(current_directory):
            if "clean_eads" in directories:
                break
            else:
                raise Exception
    except Exception as clean_ead_error:
        print(str(clean_ead_error) + "\nNo clean_eads folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "clean_eads"
        clean_path = os.path.join(current_directory, folder)
        os.mkdir(clean_path)
        print(" Done.")
    # search for existance of a source folder for ArchivesSpace EAD records
    try:
        current_directory = os.getcwd()
        for root, directories, files in os.walk(current_directory):
            if "source_eads" in directories:
                break
            else:
                raise Exception
    except Exception as source_ead_error:
        print(str(source_ead_error) + "\nNo source_eads folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "source_eads"
        source_path = os.path.join(current_directory, folder)
        os.mkdir(source_path)
        print("{} folder created\n".format(folder))
    # search for existance of a source folder for ArchivesSpace MARCXML records
    try:
        current_directory = os.getcwd()
        for root, directories, files in os.walk(current_directory):
            if "source_marcs" in directories:
                break
            else:
                raise Exception
    except Exception as source_marc_error:
        print(str(source_marc_error) + "\nNo source_marcs folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "source_marcs"
        source_path = os.path.join(current_directory, folder)
        os.mkdir(source_path)
        print("{} folder created\n".format(folder))
    # search for existance of a source folder for ArchivesSpace PDF records
    try:
        current_directory = os.getcwd()
        for root, directories, files in os.walk(current_directory):
            if "source_pdfs" in directories:
                break
            else:
                raise Exception
    except Exception as source_pdf_error:
        print(str(source_pdf_error) + "\nNo source_pdfs folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "source_pdfs"
        source_path = os.path.join(current_directory, folder)
        os.mkdir(source_path)
        print("{} folder created\n".format(folder))
    # search for existance of a source folder for ArchivesSpace Container Labels
    try:
        current_directory = os.getcwd()
        for root, directories, files in os.walk(current_directory):
            if "source_labels" in directories:
                break
            else:
                raise Exception
    except Exception as source_label_error:
        print(str(source_label_error) + "\nNo source_labels folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "source_labels"
        source_path = os.path.join(current_directory, folder)
        os.mkdir(source_path)
        print("{} folder created\n".format(folder))


def reset_defaults():
    """
    Deletes and recreates defaults.json file.
    Returns:
        None
    """
    if os.path.isfile(Path(os.getcwd(), "defaults.json")) is True:
        os.remove(Path(os.getcwd(), "defaults.json"))
    set_defaults_file()
