import os
import platform
import subprocess
import sys
import webbrowser
import json
import re
from loguru import logger
from pathlib import Path

import PySimpleGUI as sg
from asnake.client import ASnakeClient
from asnake.client.web_client import ASnakeAuthError

import as_export as asx
import cleanup as clean
import xtf_upload as xup
import defaults_setup as dsetup

import requests
import threading
import gc

EAD_EXPORT_THREAD = '-EAD_THREAD-'
EXPORT_PROGRESS_THREAD = '-EXPORT_PROGRESS-'
MARCXML_EXPORT_THREAD = '-MARCXML_THREAD-'
PDF_EXPORT_THREAD = '-PDF_THREAD-'
CONTLABEL_EXPORT_THREAD = '-CONTLABEL_THREAD-'
XTF_UPLOAD_THREAD = '-XTFUP_THREAD-'
XTF_INDEX_THREAD = '-XTFIND_THREAD-'
XTF_DELETE_THREAD = '-XTFDEL_THREAD-'
XTF_GETFILES_THREAD = '-XTFGET_THREAD-'

logger.add(str(Path('logs', 'log_{time:YYYY-MM-DD}.log')),
           format="{time}-{level}: {message}")


@logger.catch
def run_gui(defaults):
    """
    Handles the GUI operation as outlined by PySimpleGUI's guidelines.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#run_gui

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default

    Returns:
        None
    """
    gc.disable()
    sg.theme('LightBlue2')
    logger.info("ArchivesSpace Login popup initiated")
    as_username, as_password, as_api, close_program_as, client, asp_version, repositories, resources, xtf_version = \
        get_aspace_log(defaults, xtf_checkbox=True)
    logger.info(f'ArchivesSpace version: {asp_version}')
    if close_program_as is True:
        logger.info("User initiated closing program")
        sys.exit()
    pdf_broken = ["v2.6.0", "v2.7.0", "v2.7.1"]
    if asp_version in pdf_broken:
        asp_pdf_api = True
    else:
        asp_pdf_api = False
    # For XTF Users Only
    rid_box_len = 36
    if xtf_version is True:
        logger.info("XTF Login popup initiated")
        xtf_username, xtf_password, xtf_hostname, xtf_remote_path, xtf_indexer_path, xtf_lazy_path, close_program_xtf \
            = get_xtf_log(defaults, login=True)
        if close_program_xtf is True:
            logger.info("User initiated closing program")
            sys.exit()
        xtf_login_menu_button = 'Change XTF Login Credentials'
        xtf_opt_button = 'Change XTF Options'
        rid_box_len = 44
        logger.info("XTF login successful")
    else:
        xtf_login_menu_button = '!Change XTF Login Credentials'
        xtf_opt_button = '!Change XTF Options'
        xtf_username, xtf_password, xtf_hostname, xtf_remote_path, xtf_indexer_path, xtf_lazy_path = "", "", "", \
                                                                                                     "", "", ""
    cleanup_defaults = ["_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_",
                        "_DEL_LANGTRAIL_", "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_DEL_ARCHIDS_",
                        "_CNT_XLINKS_", "_DEL_NMSPCS_", "_DEL_ALLNS_"]
    cleanup_options = [option for option, bool_val in defaults["ead_cleanup_defaults"].items() if bool_val is True]
    menu_def = [['File',
                 ['Clear Cleaned EAD Export Folder',
                  '---',
                  'Clear EAD Export Folder',
                  'Clear MARCXML Export Folder',
                  'Clear Container Label Export Folder',
                  'Clear PDF Export Folder',
                  '---',
                  'Reset Defaults',
                  '---',
                  'Exit']
                 ],
                ['Edit',
                 ['Change ASpace Login Credentials',
                  '---',
                  'Change EAD Cleanup Defaults',
                  'Change EAD Export Options',
                  '---',
                  'Change MARCXML Export Options',
                  '---',
                  'Change PDF Export Options',
                  '---',
                  xtf_login_menu_button,
                  xtf_opt_button,
                  ]
                 ],
                ['Help',
                 ['User Manual',
                  'About']
                 ]
                ]
    ead_layout = [[sg.Button(button_text=" EXPORT ", key="_EXPORT_EAD_",
                             tooltip=' Export EAD.xml resources ', disabled=False),
                   sg.Button(button_text=" EXPORT ALL ", key="_EXPORT_ALLEADS_",
                             tooltip=" Export all published resources as EAD.xml files ", disabled=False)],
                  [sg.Text("Options", font=("Roboto", 13)),
                   sg.Text(" " * 123)],
                  [sg.Button(" EAD Export Options ", key="_EAD_OPTIONS_",
                             tooltip=' Choose how you would like to export resources '),
                   sg.Button(" Cleanup Options ", key="Change Cleanup Defaults",
                             tooltip=' Select what operations you want to perform on exported EAD.xml files ')],
                  [sg.Text("Output", font=("Roboto", 12))],
                  [sg.Button(button_text=" Open Cleaned EAD Exports ", key="_OPEN_CLEAN_B_",
                             tooltip=' Open folder where cleaned EAD.xml files are stored '),
                   sg.Button(button_text=" Open Raw ASpace Exports ", key="_OPEN_RAW_EXPORTS_",
                             tooltip=' Open folder where raw ASpace EAD.xml files are stored ')]
                  ]
    xtf_layout = [[sg.Button(button_text=" Upload Files ", key="_UPLOAD_",
                             tooltip=' Upload select files to XTF ', disabled=False),
                   sg.Text(" " * 2),
                   sg.Button(button_text=" Delete Files ", key="_DELETE_",
                             tooltip=" Delete existing files from XTF ", disabled=False),
                   sg.Text(" " * 2),
                   sg.Button(button_text=" Index Changed Records ", key="_INDEX_",
                             tooltip=' Run an indexing of new/updated files in XTF ', disabled=False)],
                  [sg.Text("Options", font=("Roboto", 13)),
                   sg.Text(" " * 123)],
                  [sg.Button(button_text=" XTF Options ", key="_XTF_OPTIONS_",
                             tooltip=' Select options for XTF ')]
                  ]
    marc_layout = [[sg.Button(button_text=" EXPORT ", key="_EXPORT_MARCXML_",
                              tooltip=' Export MARC.xml resources ', disabled=False),
                    sg.Button(button_text=" EXPORT ALL ", key="_EXPORT_ALLMARCXMLS_",
                              tooltip=" Export all published resources as MARC.xml files ", disabled=False)],
                   [sg.Text("Options", font=("Roboto", 13))],
                   [sg.Button(" MARCXML Export Options ", key="_MARCXML_OPTIONS_",
                              tooltip=' Choose how you would like to export resources ')],
                   [sg.Button(button_text=" Open Output ", key="_OPEN_MARC_DEST_",
                              tooltip=' Open folder where MARC.xml files are stored ')],
                   [sg.Text(" " * 140)]
                   ]
    contlabel_layout = [[sg.Button(button_text=" EXPORT ", key="_EXPORT_LABEL_",
                                   tooltip=' Export container labels for resources ', disabled=False),
                         sg.Button(button_text=" EXPORT ALL ", key="_EXPORT_ALLCONTLABELS_", disabled=False,
                                   tooltip=" Export all published resources as container label files ")],
                        [sg.Text("Options", font=("Roboto", 13)),
                         sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True,
                                 key="_CONTOPT_HELP_")],
                        [sg.Button(button_text=" Open Output ", key="_OPEN_LABEL_DEST_",
                                   tooltip=' Open folder where container label files are stored ')],
                        [sg.FolderBrowse(" Choose Output Folder: ", key="_OUTPUT_DIR_LABEL_",
                                         initial_folder=defaults["labels_export_default"]),
                         sg.InputText(defaults["labels_export_default"], key="_OUTPUT_DIR_LABEL_INPUT_",
                                      enable_events=True)],
                        [sg.Text(" " * 140)]
                        ]
    pdf_layout = [[sg.Text("WARNING:", font=("Roboto", 18), text_color="Red", visible=asp_pdf_api),
                   sg.Text("Not compatible with ArchivesSpace versions 2.6.0 - 2.7.1\n"
                           "Your ArchivesSpace version is: {}".format(asp_version), font=("Roboto", 13),
                           visible=asp_pdf_api)],
                  [sg.Button(button_text=" EXPORT ", key="_EXPORT_PDF_",
                             tooltip=' Export PDF(s) for resources ', disabled=False),
                   sg.Button(button_text=" EXPORT ALL ", key="_EXPORT_ALLPDFS_",
                             tooltip=" Export all published resources as PDF files ", disabled=False)],
                  [sg.Text("Options", font=("Roboto", 13)),
                   sg.Text(" " * 125)],
                  [sg.Button(" PDF Export Options ", key="_PDF_OPTIONS_",
                             tooltip=' Choose how you would like to export resources '),
                   sg.Button(button_text=" Open Output ", key="_OPEN_PDF_DEST_",
                             tooltip=' Open folder where PDF(s) are stored ')]
                  ]
    simple_layout_col1 = [[sg.Text("Enter Resource Identifiers here:", font=("Roboto", 12))],
                          [sg.Multiline(key="resource_id_input", size=(35, rid_box_len), focus=True,
                                        tooltip=' Enter resource identifiers here and seperate either by comma or '
                                                'newline (enter) ')]
                          ]
    simple_layout_col2 = [[sg.Text("Choose your export option:", font=("Roboto", 12))],
                          [sg.Radio("EAD", "RADIO1", key="_EXPORT_EAD_RAD_", default=True, enable_events=True),
                           sg.Radio("MARCXML", "RADIO1", key="_EXPORT_MARCXML_RAD_", enable_events=True),
                           sg.Radio("Container Labels", "RADIO1", key="_EXPORT_CONTLABS_RAD_", enable_events=True),
                           sg.Radio("PDF", "RADIO1", key="_EXPORT_PDF_RAD_", enable_events=True)],
                          [sg.Text("Choose your repository:", font=("Roboto", 12))],
                          [sg.DropDown([repo for repo in repositories.keys()], readonly=True,
                                       default_value=defaults["repo_default"]["_REPO_NAME_"], key="_REPO_SELECT_",
                                       font=("Roboto", 11),
                                       tooltip=' Select a specific repository to export from '),
                           sg.Button(" SAVE ", key="_REPO_DEFAULT_",
                                     tooltip=' Save repository as default ')],
                          [sg.Frame("Export EAD", ead_layout, font=("Roboto", 15), key="_EAD_LAYOUT_", visible=True),
                           sg.Frame("Export MARCXML", marc_layout, font=("Roboto", 15), key="_MARC_LAYOUT_",
                                    visible=False),
                           sg.Frame("Export Container Labels", contlabel_layout, font=("Roboto", 15),
                                    key="_LABEL_LAYOUT_",
                                    visible=False),
                           sg.Frame("Export PDF", pdf_layout, font=("Roboto", 15), key="_PDF_LAYOUT_", visible=False)],
                          [sg.Frame("XTF Commands", xtf_layout, font=("Roboto", 15), key="_XTF_LAYOUT_",
                                    visible=xtf_version)],
                          [sg.Text("Output Terminal:", font=("Roboto", 12),
                                   tooltip=' Program messages are output here. To clear, select all and delete. ')],
                          [sg.Output(size=(80, 18), key="_output_")]
                          ]
    layout_simple = [[sg.Menu(menu_def)],
                     [sg.Column(simple_layout_col1), sg.Column(simple_layout_col2)]
                     ]
    window_simple = sg.Window("ArchivesSpace Batch Export-Cleanup-Upload Program", layout_simple)
    logger.info("Initiate GUI window")
    while True:
        gc.collect()
        event_simple, values_simple = window_simple.Read()
        if event_simple == 'Cancel' or event_simple is None or event_simple == "Exit":
            logger.info("User initiated closing program")
            window_simple.close()
            break
        # ------------- CHANGE LAYOUTS SECTION -------------
        if event_simple == "_EXPORT_EAD_RAD_":
            logger.info("_EXPORT_EAD_RAD_ - EAD window selected")
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=xtf_version)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_MARCXML_RAD_":
            logger.info("_EXPORT_MARCXML_RAD_ - MARCXML window selected")
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_PDF_RAD_":
            logger.info("_EXPORT_PDF_RAD_ - PDF window selected")
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=True)
        if event_simple == "_EXPORT_CONTLABS_RAD_":
            logger.info("_EXPORT_CONTLABS_RAD_ - Container Labels window selected")
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
        # ------------- REPOSITORY SECTION -------------
        if event_simple == "_REPO_DEFAULT_":
            logger.info(f'_REPO_DEFAULT_ - User saved {values_simple["_REPO_SELECT_"]} as default')
            with open("defaults.json", "w") as DEFAULT:
                defaults["repo_default"]["_REPO_NAME_"] = values_simple["_REPO_SELECT_"]
                defaults["repo_default"]["_REPO_ID_"] = repositories[values_simple["_REPO_SELECT_"]]
                json.dump(defaults, DEFAULT)
                DEFAULT.close()
        # ------------- EAD SECTION -------------
        if event_simple == "_EXPORT_EAD_":
            logger.info(f'_EXPORT_EAD_ - User initiated exporting EAD(s):\n{values_simple["resource_id_input"]}')
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        args = (input_ids, defaults, cleanup_options, repositories, client, values_simple,
                                window_simple,)
                        start_thread(get_eads, args, window_simple)
                        logger.info("EAD_EXPORT_THREAD started")
                else:
                    args = (input_ids, defaults, cleanup_options, repositories, client, values_simple, window_simple,)
                    start_thread(get_eads, args, window_simple)
                    logger.info("EAD_EXPORT_THREAD started")
        if event_simple == "_EXPORT_ALLEADS_":
            logger.info("_EXPORT_ALLEADS_ - User initiated exporting ALL EADs")
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        input_ids = resources
                        args = (input_ids, defaults, cleanup_options, repositories, client, window_simple,)
                        start_thread(get_all_eads, args, window_simple)
                        logger.info("EAD_EXPORT_THREAD started")
                else:
                    repo_id = repositories[values_simple["_REPO_SELECT_"]]
                    input_ids = {repo_id: resources[repo_id]}
                    args = (input_ids, defaults, cleanup_options, repositories, client, window_simple,)
                    start_thread(get_all_eads, args, window_simple)
                    logger.info("EAD_EXPORT_THREAD started")
        if event_simple == "_EAD_OPTIONS_" or event_simple == "Change EAD Export Options":
            get_ead_options(defaults)
        if event_simple == "Change EAD Cleanup Defaults" or event_simple == "Change Cleanup Defaults":
            cleanup_options = get_cleanup_defaults(cleanup_defaults, defaults)
        if event_simple == "_OPEN_CLEAN_B_":
            logger.info(f'Opening clean EAD exports directory: {defaults["ead_export_default"]["_OUTPUT_DIR_"]}')
            if not defaults["ead_export_default"]["_OUTPUT_DIR_"]:
                filepath_eads = str(Path.cwd().joinpath("clean_eads"))
                open_file(filepath_eads)
            else:
                filepath_eads = str(Path(defaults["ead_export_default"]["_OUTPUT_DIR_"]))
                open_file(filepath_eads)
        if event_simple == "_OPEN_RAW_EXPORTS_":
            logger.info(f'Opening raw EAD exports directory: {defaults["ead_export_default"]["_SOURCE_DIR_"]}')
            if not defaults["ead_export_default"]["_SOURCE_DIR_"]:
                filepath_eads = str(Path.cwd().joinpath("source_eads"))
                open_file(filepath_eads)
            else:
                filepath_eads = str(Path(defaults["ead_export_default"]["_SOURCE_DIR_"]))
                open_file(filepath_eads)
        # ------------- MARCXML SECTION -------------
        if event_simple == "_EXPORT_MARCXML_":
            logger.info(f'_EXPORT_MARCXML_ - User initiated exporting MARCXMLs:\n{values_simple["resource_id_input"]}')
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        args = (input_ids, defaults, repositories, client, values_simple, window_simple,)
                        start_thread(get_marcxml, args, window_simple)
                        logger.info("MARCXML_EXPORT_THREAD started")
                else:
                    args = (input_ids, defaults, repositories, client, values_simple, window_simple,)
                    start_thread(get_marcxml, args, window_simple)
                    logger.info("MARCXML_EXPORT_THREAD started")
        if event_simple == "_EXPORT_ALLMARCXMLS_":
            logger.info("_EXPORT_ALLMARCXMLS_ - User initiated exporting ALL MARCXML(s)")
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        input_ids = resources
                        args = (input_ids, defaults, repositories, client, window_simple,)
                        start_thread(get_all_marcxml, args, window_simple)
                        logger.info("MARCXML_EXPORT_THREAD started")
                else:
                    repo_id = repositories[values_simple["_REPO_SELECT_"]]
                    input_ids = {repo_id: resources[repo_id]}
                    args = (input_ids, defaults, repositories, client, window_simple,)
                    start_thread(get_all_marcxml, args, window_simple)
                    logger.info("MARCXML_EXPORT_THREAD started")
        if event_simple == "_OPEN_MARC_DEST_":
            logger.info(f'Opening MARCXML exports directory: {defaults["marc_export_default"]["_OUTPUT_DIR_"]}')
            if not defaults["marc_export_default"]["_OUTPUT_DIR_"]:
                filepath_marcs = str(Path.cwd().joinpath("source_marcs"))
                open_file(filepath_marcs)
            else:
                filepath_marcs = str(Path(defaults["marc_export_default"]["_OUTPUT_DIR_"]))
                open_file(filepath_marcs)
        if event_simple == "_MARCXML_OPTIONS_" or event_simple == "Change MARCXML Export Options":
            get_marc_options(defaults)
        # ------------- PDF SECTION -------------
        if event_simple == "_EXPORT_PDF_":
            logger.info(f'_EXPORT_PDF_ - User initiated exporting PDFs:\n{values_simple["resource_id_input"]}')
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        args = (input_ids, defaults, repositories, client, values_simple, window_simple,)
                        start_thread(get_pdfs, args, window_simple)
                        logger.info("PDF_EXPORT_THREAD started")
                else:
                    args = (input_ids, defaults, repositories, client, values_simple, window_simple,)
                    start_thread(get_pdfs, args, window_simple)
                    logger.info("PDF_EXPORT_THREAD started")
        if event_simple == "_EXPORT_ALLPDFS_":
            logger.info("_EXPORT_ALLMARCXMLS_ - User initiated exporting ALL PDF(s)")
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        input_ids = resources
                        args = (input_ids, defaults, repositories, client, window_simple,)
                        start_thread(get_all_pdfs, args, window_simple)
                        logger.info("PDF_EXPORT_THREAD started")
                else:
                    repo_id = repositories[values_simple["_REPO_SELECT_"]]
                    input_ids = {repo_id: resources[repo_id]}
                    args = (input_ids, defaults, repositories, client, window_simple,)
                    start_thread(get_all_pdfs, args, window_simple)
                    logger.info("PDF_EXPORT_THREAD started")
        if event_simple == "_OPEN_PDF_DEST_":
            logger.info(f'Opening PDF exports directory: {defaults["pdf_export_default"]["_OUTPUT_DIR_"]}')
            if not defaults["pdf_export_default"]["_OUTPUT_DIR_"]:
                filepath_pdfs = str(Path.cwd().joinpath("source_pdfs"))
                open_file(filepath_pdfs)
            else:
                filepath_pdfs = str(Path(defaults["pdf_export_default"]["_OUTPUT_DIR_"]))
                open_file(filepath_pdfs)
        if event_simple == "_PDF_OPTIONS_" or event_simple == "Change PDF Export Options":
            get_pdf_options(defaults)
        # ------------- CONTAINER LABEL SECTION -------------
        if event_simple == "_EXPORT_LABEL_":
            logger.info(f'_EXPORT_LABEL_ - User initiated exporting Container Labels:'
                        f'\n{values_simple["resource_id_input"]}')
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        args = (input_ids, defaults, repositories, client, values_simple, window_simple,)
                        start_thread(get_contlabels, args, window_simple)
                        logger.info("CONTLABEL_EXPORT_THREAD started")
                else:
                    args = (input_ids, defaults, repositories, client, values_simple, window_simple,)
                    start_thread(get_contlabels, args, window_simple)
                    logger.info("CONTLABEL_EXPORT_THREAD started")
        if event_simple == "_EXPORT_ALLCONTLABELS_":
            logger.info("_EXPORT_ALLCONTLABELS_ - User initiated exporting ALL Container Labels")
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
                logger.warning("User did not select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        logger.info("User selected - Search Across Repositories (Sys Admin Only)")
                        input_ids = resources
                        args = (input_ids, defaults, repositories, client, window_simple,)
                        start_thread(get_all_contlabels, args, window_simple)
                        logger.info("CONTLABEL_EXPORT_THREAD started")
                else:
                    repo_id = repositories[values_simple["_REPO_SELECT_"]]
                    input_ids = {repo_id: resources[repo_id]}
                    args = (input_ids, defaults, repositories, client, window_simple,)
                    start_thread(get_all_contlabels, args, window_simple)
                    logger.info("CONTLABEL_EXPORT_THREAD started")
        if event_simple == "_OUTPUT_DIR_LABEL_INPUT_":
            if os.path.isdir(values_simple["_OUTPUT_DIR_LABEL_INPUT_"]) is False:
                sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
                logger.warning("_OUTPUT_DIR_LABEL_INPUT_ - User selected invalid export output")
            else:
                with open("defaults.json", "w") as defaults_labels:
                    defaults["labels_export_default"] = values_simple["_OUTPUT_DIR_LABEL_INPUT_"]
                    json.dump(defaults, defaults_labels)
                    defaults_labels.close()
        if event_simple == "_OPEN_LABEL_DEST_":
            logger.info(f'Opening Container Labels exports directory: {defaults["labels_export_default"]}')
            if not defaults["labels_export_default"]:
                filepath_labels = str(Path.cwd().joinpath("source_labels"))
                open_file(filepath_labels)
            else:
                filepath_labels = str(Path(defaults["labels_export_default"]))
                open_file(filepath_labels)
        if event_simple == "_CONTOPT_HELP_":
            logger.info(f'User opened CONTLABELS Options Help button')
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#conta"
                            "iner-labels-screen",
                            new=2)
        # ------------- EXPORT THREADS -------------
        if event_simple in (EAD_EXPORT_THREAD, MARCXML_EXPORT_THREAD, PDF_EXPORT_THREAD, CONTLABEL_EXPORT_THREAD):
            window_simple[f'{"_EXPORT_EAD_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_ALLEADS_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_MARCXML_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_ALLMARCXMLS_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_LABEL_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_ALLCONTLABELS_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_PDF_"}'].update(disabled=False)
            window_simple[f'{"_EXPORT_ALLPDFS_"}'].update(disabled=False)
        if event_simple == EXPORT_PROGRESS_THREAD:
            sg.one_line_progress_meter("Export progress", values_simple["-EXPORT_PROGRESS-"][0],
                                       values_simple["-EXPORT_PROGRESS-"][1], orientation='h', no_button=True)
        # ------------- MENU OPTIONS SECTION -------------
        # ------------------- FILE -------------------
        if event_simple == "Clear Cleaned EAD Export Folder":
            logger.info(f'Clearing Cleaned EAD Export folder: {defaults["ead_export_default"]["_OUTPUT_DIR_"]}')
            clean_files = os.listdir(defaults["ead_export_default"]["_OUTPUT_DIR_"])
            try:
                file_count = 0
                for file in clean_files:
                    file_count += 1
                    full_path = str(Path(defaults["ead_export_default"]["_OUTPUT_DIR_"], file))
                    os.remove(full_path)
                print("Deleted {} files in clean_eads".format(str(file_count)))
                logger.info(f'Deleted {file_count} files in {defaults["ead_export_default"]["_OUTPUT_DIR_"]}')
            except Exception as e:
                print("No files in clean_eads folder\n" + str(e))
                logger.error(f'Tried deleting files from {defaults["ead_export_default"]["_OUTPUT_DIR_"]}: {e}')
        if event_simple == "Clear EAD Export Folder":
            logger.info(f'Clearing Raw EAD Export folder: {defaults["ead_export_default"]["_SOURCE_DIR_"]}')
            raw_files = os.listdir(defaults["ead_export_default"]["_SOURCE_DIR_"])
            try:
                file_count = 0
                for file in raw_files:
                    file_count += 1
                    full_path = str(Path(defaults["ead_export_default"]["_SOURCE_DIR_"], file))
                    os.remove(full_path)
                print("Deleted {} files in source_eads".format(str(file_count)))
                logger.info(f'Deleted {file_count} files in {defaults["ead_export_default"]["_SOURCE_DIR_"]}')
            except Exception as e:
                print("No files in source_eads folder\n" + str(e))
                logger.error(f'Tried deleting files from {defaults["ead_export_default"]["_SOURCE_DIR_"]}: {e}')
        if event_simple == "Clear MARCXML Export Folder":
            logger.info(f'Clearing MARCXML Export folder: {defaults["marc_export_default"]["_OUTPUT_DIR_"]}')
            raw_files = os.listdir(defaults["marc_export_default"]["_OUTPUT_DIR_"])
            try:
                file_count = 0
                for file in raw_files:
                    file_count += 1
                    full_path = str(Path(defaults["marc_export_default"]["_OUTPUT_DIR_"], file))
                    os.remove(full_path)
                print("Deleted {} files in source_marcs".format(str(file_count)))
                logger.info(f'Deleted {file_count} files in {defaults["marc_export_default"]["_OUTPUT_DIR_"]}')
            except Exception as e:
                print("No files in source_marcs folder\n" + str(e))
                logger.error(f'Tried deleting files from {defaults["marc_export_default"]["_OUTPUT_DIR_"]}: {e}')
        if event_simple == "Clear Container Label Export Folder":
            logger.info(f'Clearing Container Label Export folder: {defaults["labels_export_default"]}')
            raw_files = os.listdir(defaults["labels_export_default"])
            try:
                file_count = 0
                for file in raw_files:
                    file_count += 1
                    full_path = str(Path(defaults["labels_export_default"], file))
                    os.remove(full_path)
                print("Deleted {} files in source_labels".format(str(file_count)))
                logger.info(f'Deleted {file_count} files in {defaults["labels_export_default"]}')
            except Exception as e:
                print("No files in source_labels folder\n" + str(e))
                logger.error(f'Tried deleting files from {defaults["labels_export_default"]}: {e}')
        if event_simple == "Clear PDF Export Folder":
            logger.info(f'Clearing PDF Export folder: {defaults["pdf_export_default"]["_OUTPUT_DIR_"]}')
            raw_files = os.listdir(defaults["pdf_export_default"]["_OUTPUT_DIR_"])
            try:
                file_count = 0
                for file in raw_files:
                    file_count += 1
                    full_path = str(Path(defaults["pdf_export_default"]["_OUTPUT_DIR_"], file))
                    os.remove(full_path)
                print("Deleted {} files in source_pdfs".format(str(file_count)))
                logger.info(f'Deleted {file_count} files in {defaults["pdf_export_default"]["_OUTPUT_DIR_"]}')
            except Exception as e:
                print("No files in source_pdfs folder\n" + str(e))
                logger.error(f'Tried deleting files from {defaults["pdf_export_default"]["_OUTPUT_DIR_"]}: {e}')
        if event_simple == "Reset Defaults":
            reset_defaults = sg.PopupYesNo("You are about to reset your configurations. Are you sure? \n"
                                           "You will have to restart the program to see changes.")
            if reset_defaults == "Yes":
                logger.info("User initiated reseting defaults")
                try:
                    dsetup.reset_defaults()
                except Exception as e:
                    print(f'Error when resetting defaults: {e}')
                    logger.error(f'Error when resetting defaults: {e}')
        # ------------------- EDIT -------------------
        if event_simple == "Change ASpace Login Credentials":
            logger.info(f'User initiated changing ASpace login credentials within app')
            as_username, as_password, as_api, close_program_as, client, asp_version, repositories, resources, \
                xtf_version = get_aspace_log(defaults, xtf_checkbox=False, as_un=as_username, as_pw=as_password,
                                             as_ap=as_api, as_client=client, as_res=resources, as_repos=repositories,
                                             xtf_ver=xtf_version)
            logger.info(f'ASpace version: {asp_version}')
        if event_simple == 'Change XTF Login Credentials':
            logger.info(f'User initiated changing XTF login credentials within app')
            xtf_username, xtf_password, xtf_hostname, xtf_remote_path, xtf_indexer_path, xtf_lazy_path, \
                close_program_xtf = get_xtf_log(defaults, login=False, xtf_un=xtf_username, xtf_pw=xtf_password,
                                                xtf_ht=xtf_hostname, xtf_rp=xtf_remote_path, xtf_ip=xtf_indexer_path,
                                                xtf_lp=xtf_lazy_path)
        # ------------------- HELP -------------------
        if event_simple == "About":
            logger.info(f'User initiated About menu option')
            window_about_active = True
            layout_about = [
                [sg.Text("Created by Corey Schmidt for the University of Georgia Libraries\n\n"
                         "Version: 1.4.4-UGA\n\n"  # TODO Change Version #
                         "To check for the latest versions, check the Github\n", font=("Roboto", 12))],
                [sg.OK(bind_return_key=True, key="_ABOUT_OK_"), sg.Button(" Check Github ", key="_CHECK_GITHUB_"),
                 sg.Button(" Check GUI Info ", key="_CHECK_PYPSG_")]
            ]
            window_about = sg.Window("About this program", layout_about)
            while window_about_active is True:
                event_about, values_about = window_about.Read()
                if event_about is None:
                    window_about.close()
                    window_about_active = False
                if event_about == "_CHECK_GITHUB_":
                    try:
                        webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/releases",
                                        new=2)
                    except Exception as e:
                        print(f'Failed to open webbrowser: {e}')
                        logger.error(f'Failed to open webbrowser: {e}')
                if event_about == "_CHECK_PYPSG_":
                    try:
                        sg.popup_scrolled(sg.get_versions(), non_blocking=True, keep_on_top=True)
                    except Exception as e:
                        print(f'Failed to open PySimpleGUI versions popup: {e}')
                        logger.error(f'Failed to open PySimpleGUI versions popup: {e}')
                if event_about == "_ABOUT_OK_":
                    window_about.close()
                    window_about_active = False
        if event_simple == "User Manual":
            try:
                webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual",
                                new=2)
            except Exception as e:
                print(f'Failed to open webbrowser: {e}')
                logger.error(f'Failed to open webbrowser: {e}')
        # ------------- XTF SECTION -------------------
        if event_simple == "_UPLOAD_":
            logger.info(f'User initiated uploading files to XTF')
            window_upl_active = True
            window_simple[f'{"_UPLOAD_"}'].update(disabled=True)
            window_simple[f'{"_INDEX_"}'].update(disabled=True)
            window_simple[f'{"_DELETE_"}'].update(disabled=True)
            files_list = sort_list([ead_file for ead_file in os.listdir(defaults["xtf_default"]["xtf_local_path"])
                                    if Path(ead_file).suffix == ".xml" or Path(ead_file).suffix == ".pdf"])
            upload_options_layout = [[sg.Button(" Upload to XTF ", key="_UPLOAD_TO_XTF_", disabled=False),
                                      sg.Text(" " * 62)],
                                     [sg.Text("Options", font=("Roboto", 12))],
                                     [sg.Button(" XTF Options ", key="_XTF_OPTIONS_2_")]
                                     ]
            xtf_upload_layout = [[sg.Text("Files to Upload:", font=("Roboto", 14))],
                                 [sg.Listbox(files_list, size=(50, 20), select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                                             key="_SELECT_FILES_")],
                                 [sg.Frame("XTF Upload", upload_options_layout, font=("Roboto", 14))]]
            window_upl = sg.Window("Upload Files to XTF", xtf_upload_layout)
            while window_upl_active is True:
                event_upl, values_upl = window_upl.Read()
                if event_upl is None:
                    logger.info(f'User cancelled upload process')
                    window_simple[f'{"_UPLOAD_"}'].update(disabled=False)
                    window_simple[f'{"_INDEX_"}'].update(disabled=False)
                    window_simple[f'{"_DELETE_"}'].update(disabled=False)
                    window_upl.close()
                    window_upl_active = False
                if event_upl == "_XTF_OPTIONS_2_":
                    logger.info(f'User selected XTF Options from Upload window: _XTF_OPTIONS_2_')
                    get_xtf_options(defaults)
                if event_upl == "_UPLOAD_TO_XTF_":
                    logger.info(f'User began upload of files to XTF: _UPLOAD_TO_XTF_; Files: {values_upl}')
                    xtfup_thread = threading.Thread(target=upload_files_xtf, args=(defaults, xtf_hostname, xtf_username,
                                                                                   xtf_password, xtf_remote_path,
                                                                                   xtf_indexer_path, xtf_lazy_path,
                                                                                   values_upl, window_simple,))
                    xtfup_thread.start()
                    window_upl.close()
                    window_upl_active = False
        if event_simple == "_DELETE_":
            logger.info(f'User initiated deleting files from XTF')
            window_del_active = True
            window_simple[f'{"_UPLOAD_"}'].update(disabled=True)
            window_simple[f'{"_INDEX_"}'].update(disabled=True)
            window_simple[f'{"_DELETE_"}'].update(disabled=True)
            try:
                logger.info(f'Getting remotes files from XTF')
                print("Getting remote files, this may take a second...", flush=True, end="")
                remote_files = get_remote_files(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path,
                                                xtf_indexer_path, xtf_lazy_path)
            except Exception as e:
                logger.error(f'Error when getting files from XTF: {e}')
            else:
                print("Done")
                delete_options_layout = [[sg.Button(" Delete from XTF ", key="_DELETE_XTF_", disabled=False),
                                          sg.Text(" " * 62)],
                                         [sg.Text("Options", font=("Roboto", 12))],
                                         [sg.Button(" XTF Options ", key="_XTF_OPTIONS_3_")]
                                         ]
                xtf_delete_layout = [[sg.Text("Files to Delete:", font=("Roboto", 14))],
                                     [sg.Listbox(remote_files, size=(50, 20),
                                                 select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE, key="_SELECT_FILES_")],
                                     [sg.Frame("XTF Upload", delete_options_layout, font=("Roboto", 14))]]
                window_del = sg.Window("Delete Files from XTF", xtf_delete_layout)
                while window_del_active is True:
                    event_del, values_del = window_del.Read()
                    if event_del is None:
                        logger.info(f'User cancelled deleting files from XTF')
                        window_simple[f'{"_UPLOAD_"}'].update(disabled=False)
                        window_simple[f'{"_INDEX_"}'].update(disabled=False)
                        window_simple[f'{"_DELETE_"}'].update(disabled=False)
                        window_del.close()
                        window_del_active = False
                    if event_del == "_XTF_OPTIONS_3_":
                        logger.info(f'User initiated getting XTF options from Delete: _XTF_OPTIONS_3_')
                        get_xtf_options(defaults)
                    if event_del == "_DELETE_XTF_":
                        logger.info(f'User began delete of files from XTF: _DELETE_XTF_; Files: {values_del}')
                        xtfdel_thread = threading.Thread(target=delete_files_xtf, args=(defaults, xtf_hostname,
                                                                                        xtf_username, xtf_password,
                                                                                        xtf_remote_path,
                                                                                        xtf_indexer_path, xtf_lazy_path,
                                                                                        values_del, window_simple,))
                        xtfdel_thread.start()
                        window_del.close()
                        window_del_active = False
        if event_simple == "_INDEX_":
            logger.info(f'User initiated re-indexing: _INDEX_')
            xtfind_thread = threading.Thread(target=index_xtf, args=(defaults, xtf_hostname, xtf_username, xtf_password,
                                                                     xtf_remote_path, xtf_indexer_path,
                                                                     xtf_lazy_path, window_simple,))
            xtfind_thread.start()
            window_simple[f'{"_UPLOAD_"}'].update(disabled=True)
            window_simple[f'{"_INDEX_"}'].update(disabled=True)
            window_simple[f'{"_DELETE_"}'].update(disabled=True)
        if event_simple == "_XTF_OPTIONS_" or event_simple == "Change XTF Options":
            logger.info(f'User initiated XTF options: _XTF_OPTIONS_ or Change XTF Options')
            get_xtf_options(defaults)
        # ---------------- XTF THREADS ----------------
        if event_simple in (XTF_INDEX_THREAD, XTF_UPLOAD_THREAD, XTF_DELETE_THREAD, XTF_GETFILES_THREAD):
            window_simple[f'{"_UPLOAD_"}'].update(disabled=False)
            window_simple[f'{"_INDEX_"}'].update(disabled=False)
            window_simple[f'{"_DELETE_"}'].update(disabled=False)
    window_simple.close()


def get_aspace_log(defaults, xtf_checkbox, as_un=None, as_pw=None, as_ap=None, as_client=None, as_repos=None,
                   as_res=None, xtf_ver=None):
    """
    Gets a user's ArchiveSpace credentials.

    There are 3 components to it, the setup code, correct_creds while loop, and the window_asplog_active while loop. It
    uses ASnake.client to authenticate and stay connected to ArchivesSpace. Documentation for ASnake can be found here:
    https://archivesspace-labs.github.io/ArchivesSnake/html/index.html

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_aspace_log

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        xtf_checkbox (bool, optional): user input that is used to display XTF-related features in the GUI
        as_un (str, optional): user's ArchivesSpace username
        as_pw (str, optional): user's ArchivesSpace password
        as_ap (str, optional): the ArchivesSpace API URL
        as_client (ASnake.client object, optional): the ArchivesSpace ASnake client for accessing and connecting to the API
        as_repos (dict, optional): contains info on all the repositories for an ArchivesSpace instance, including name as the key and id # as it's value
        as_res (dict, optional): contains info on all the resources for an ArchivesSpace instance, including repository name as key and list of resource ids as value
        xtf_ver (bool, optional): user indicated value whether they want to display xtf features in the GUI

    Returns:
        as_username (str): user's ArchivesSpace username
        as_password (str): user's ArchivesSpace password
        as_api (str): the ArchivesSpace API URL
        close_program (bool): if a user exits the popup, this will return true and end run_gui()
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        asp_version (str): the current version of ArchivesSpace
        repositories (dict): contains info on all the repositories for an ArchivesSpace instance, including name as the key and id # as it's value
        resource_ids (dict): contains info on all the resources for each repository for an ArchivesSpace instance, including repository # as the key and a list of resource #s as strings as it's value
        xtf_version (bool): user indicated value whether they want to display xtf features in the GUI
    """
    as_username = as_un
    as_password = as_pw
    as_api = as_ap
    client = as_client
    asp_version = None
    if as_repos is None:
        repositories = {"Search Across Repositories (Sys Admin Only)": None}
    else:
        repositories = as_repos
    if as_res is None:
        resource_ids = {}
    else:
        resource_ids = as_res
    xtf_version = xtf_ver
    if xtf_checkbox is True:
        save_button_asp = " Save and Continue "
    else:
        save_button_asp = " Save and Close "
    window_asplog_active = True
    correct_creds = False
    close_program = False
    while correct_creds is False:
        asplog_col1 = [[sg.Text("ArchivesSpace username:", font=("Roboto", 11))],
                       [sg.Text("ArchivesSpace password:", font=("Roboto", 11))],
                       [sg.Text("ArchivesSpace API URL:", font=("Roboto", 11))]]
        asplog_col2 = [[sg.InputText(focus=True, key="_ASPACE_UNAME_")],
                       [sg.InputText(password_char='*', key="_ASPACE_PWORD_")],
                       [sg.InputText(defaults["as_api"], key="_ASPACE_API_")]]
        layout_asplog = [
            [sg.Column(asplog_col1, key="_ASPLOG_COL1_", visible=True),
             sg.Column(asplog_col2, key="_ASPLOG_COL2_", visible=True)],
            [sg.Checkbox("Use XTF features of this tool", font=("Roboto", 12), key="_USE_XTF_",
                         default=defaults["xtf_default"]["xtf_version"], visible=xtf_checkbox)],
            [sg.Button(save_button_asp, bind_return_key=True, key="_SAVE_CLOSE_LOGIN_")]
        ]
        window_login = sg.Window("ArchivesSpace Login Credentials", layout_asplog)
        while window_asplog_active is True:
            event_log, values_log = window_login.Read()
            if event_log == "_SAVE_CLOSE_LOGIN_":
                logger.info(f'User initiated ASpace login')
                connect_client = ASnakeClient(baseurl=values_log["_ASPACE_API_"],
                                              username=values_log["_ASPACE_UNAME_"],
                                              password=values_log["_ASPACE_PWORD_"])
                try:
                    requests.get(values_log["_ASPACE_API_"])
                except Exception as api_error:
                    sg.Popup("Your API credentials were entered incorrectly.\n"
                             "Please try again.\n\n" + api_error.__str__())
                    logger.error(f'Error with validating API credentials: {api_error};'
                                 f' API: {values_log["_ASPACE_API_"]}')
                else:
                    try:
                        connect_client.authorize()
                    except ASnakeAuthError as e:
                        error_message = ""
                        if ":" in str(e):
                            error_divided = str(e).split(":")
                            for line in error_divided:
                                error_message += line + "\n"
                        else:
                            error_message = str(e)
                        sg.Popup("Your username and/or password were entered incorrectly. Please try again.\n\n" +
                                 error_message)
                        logger.error(f'Username and/or password failed: {error_message}')
                    else:
                        client = connect_client
                        as_username = values_log["_ASPACE_UNAME_"]
                        as_password = values_log["_ASPACE_PWORD_"]
                        as_api = values_log["_ASPACE_API_"]
                        xtf_version = values_log["_USE_XTF_"]
                        asp_version = client.get("/version").content.decode().split(" ")[1].replace("(",
                                                                                                    "").replace(")", "")
                        with open("defaults.json",
                                  "w") as defaults_asp:  # If connection is successful, save ASpace API in defaults.json
                            defaults["as_api"] = as_api
                            defaults["xtf_default"]["xtf_version"] = xtf_version
                            json.dump(defaults, defaults_asp)
                            defaults_asp.close()
                        # Get repositories info
                        if len(repositories) == 1:
                            repo_results = client.get('/repositories')
                            repo_results_dec = json.loads(repo_results.content.decode())
                            for result in repo_results_dec:
                                uri_components = result["uri"].split("/")
                                repositories[result["name"]] = int(uri_components[-1])
                            # Get resource ids
                            for repository in repo_results.json():
                                resources = client.get(f"{repository['uri']}/resources", params={"all_ids":
                                                                                                 True}).json()
                                uri_components = repository["uri"].split("/")
                                repository_id = int(uri_components[-1])
                                resource_ids[repository_id] = [resource_id for resource_id in resources]
                        window_asplog_active = False
                        correct_creds = True
            if event_log is None or event_log == 'Cancel':
                logger.info(f'User cancelled ASpace login')
                window_login.close()
                window_asplog_active = False
                correct_creds = True
                close_program = True
                break
        window_login.close()
    return as_username, as_password, as_api, close_program, client, asp_version, repositories, resource_ids, xtf_version


def get_xtf_log(defaults, login=True, xtf_un=None, xtf_pw=None, xtf_ht=None, xtf_rp=None, xtf_ip=None, xtf_lp=None):
    """
    Gets a user's XTF credentials.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_xtf_log

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        login (bool): determines whether window is on initial popup or within program, changes lang. of save button
        xtf_un (object, optional): user's XTF username
        xtf_pw (object, optional): user's XTF password
        xtf_ht (object, optional): the host URL for the XTF instance
        xtf_rp (object, optional): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_ip (object, optional): the path (file) where the website indexer is located
        xtf_lp (object, optional): the path (folder) where xml.lazy files are stored - for permissions updates

    Returns:
        xtf_username (str): user's XTF username
        xtf_password (str): user's XTF password
        xtf_host (str): the host URL for the XTF instance
        xtf_remote_path (str): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_indexer_path (str): the path (file) where the website indexer is located
        xtf_lazy_path (str): the path (folder) where the xml.lazy files are stored - used to update permissions
        close_program (bool): if a user exits the popup, this will return true and end run_gui()
    """
    xtf_username = xtf_un
    xtf_password = xtf_pw
    xtf_host = xtf_ht
    xtf_remote_path = xtf_rp
    xtf_indexer_path = xtf_ip
    xtf_lazy_path = xtf_lp
    if login is True:
        save_button_xtf = " Save and Continue "
    else:
        save_button_xtf = " Save and Close "
    window_xtflog_active = True
    correct_creds = False
    close_program = False
    while correct_creds is False:
        xtflog_col1 = [[sg.Text("XTF username:", font=("Roboto", 11))],
                       [sg.Text("XTF password:", font=("Roboto", 11))],
                       [sg.Text("XTF Hostname:", font=("Roboto", 11))],
                       [sg.Text("XTF Remote Path:", font=("Roboto", 11))],
                       [sg.Text("XTF Indexer Path:", font=("Roboto", 11))],
                       [sg.Text("XTF Lazy Index Path:", font=("Roboto", 11))]]
        xtflog_col2 = [[sg.InputText(focus=True, key="_XTF_UNAME_")],
                       [sg.InputText(password_char='*', key="_XTF_PWORD_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_host"], key="_XTF_HOSTNAME_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_remote_path"], key="_XTF_REMPATH_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_indexer_path"], key="_XTF_INDPATH_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_lazyindex_path"], key="_XTF_LAZYPATH_")]]
        layout_xtflog = [
            [sg.Column(xtflog_col1), sg.Column(xtflog_col2)],
            [sg.Button(save_button_xtf, bind_return_key=True, key="_SAVE_CLOSE_LOGIN_")]
        ]
        window_xtfcred = sg.Window("XTF Login Credentials", layout_xtflog)
        while window_xtflog_active is True:
            event_xlog, values_xlog = window_xtfcred.Read()
            logger.info(f'User initiated XTF Login credentials')
            if event_xlog == "_SAVE_CLOSE_LOGIN_":
                try:
                    remote = xup.RemoteClient(values_xlog["_XTF_HOSTNAME_"], values_xlog["_XTF_UNAME_"],
                                              values_xlog["_XTF_PWORD_"], values_xlog["_XTF_REMPATH_"],
                                              values_xlog["_XTF_INDPATH_"], values_xlog["_XTF_LAZYPATH_"])
                    remote.client = remote.connect_remote()
                    if remote.scp is None:
                        raise Exception(remote.client)
                    else:
                        xtf_username = values_xlog["_XTF_UNAME_"]
                        xtf_password = values_xlog["_XTF_PWORD_"]
                        xtf_host = values_xlog["_XTF_HOSTNAME_"]
                        xtf_remote_path = values_xlog["_XTF_REMPATH_"]
                        xtf_indexer_path = values_xlog["_XTF_INDPATH_"]
                        xtf_lazy_path = values_xlog["_XTF_LAZYPATH_"]
                        with open("defaults.json",
                                  "w") as defaults_xtf:
                            defaults["xtf_default"]["xtf_host"] = values_xlog["_XTF_HOSTNAME_"]
                            defaults["xtf_default"]["xtf_remote_path"] = values_xlog["_XTF_REMPATH_"]
                            defaults["xtf_default"]["xtf_indexer_path"] = values_xlog["_XTF_INDPATH_"]
                            defaults["xtf_default"]["xtf_lazyindex_path"] = values_xlog["_XTF_LAZYPATH_"]
                            json.dump(defaults, defaults_xtf)
                            defaults_xtf.close()
                        window_xtflog_active = False
                        correct_creds = True
                        break
                except Exception as e:
                    sg.Popup("Your username, password, or info were entered incorrectly. Please try again.\n\n" +
                             str(e))
                    logger.error(f'XTF credentials failed.\nHostname: {values_xlog["_XTF_HOSTNAME_"]}'
                                 f'\nRemote Path: {values_xlog["_XTF_REMPATH_"]}'
                                 f'\nIndexer Path: {values_xlog["_XTF_INDPATH_"]}'
                                 f'\nLazy Index Path: {values_xlog["_XTF_LAZYPATH_"]}')
                    window_xtflog_active = True
            if event_xlog is None or event_xlog == 'Cancel':
                logger.info(f'User cancelled XTF login')
                window_xtfcred.close()
                window_xtflog_active = False
                correct_creds = True
                close_program = True
                break
        window_xtfcred.close()
    return xtf_username, xtf_password, xtf_host, xtf_remote_path, xtf_indexer_path, xtf_lazy_path, close_program


def get_eads(input_ids, defaults, cleanup_options, repositories, client, values_simple, gui_window, export_all=False):
    """
    Iterates through the user input and sends them to as_export.py to fetch_results() and export_ead().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_eads

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        cleanup_options (list): options a user wants to run against an EAD.xml file after export to clean the file
        These include the following:
            "_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_", "_DEL_LANGTRAIL_",
            "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_DEL_ARCHIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_",
            "_DEL_ALLNS_"
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict or int): values as entered with the run_gui() function, or repository ID for export all
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info
        export_all (bool): whether to pass URIs of all published resources to export

    Returns:
        None
    """
    resources = []
    export_counter = 0
    if export_all is True:
        resources = [input_ids]
        repo_id = values_simple
    else:
        repo_id = repositories[values_simple["_REPO_SELECT_"]]
        if "," in input_ids:
            csep_resources = [user_input.strip() for user_input in input_ids.split(",")]
            for resource in csep_resources:
                linebreak_resources = resource.splitlines()
                for lb_resource in linebreak_resources:
                    resources.append(lb_resource)
        else:
            resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        if export_all is True:
            logger.info(f'Beginning EAD export: EXPORT_ALL')
            resource_export = asx.ASExport(input_id, repo_id, client, defaults["ead_export_default"]["_SOURCE_DIR_"],
                                           export_all=True)
        else:
            logger.info(f'Beginning EAD export: {resources}')
            resource_export = asx.ASExport(input_id, repo_id, client, defaults["ead_export_default"]["_SOURCE_DIR_"])
        resource_export.fetch_results()
        if resource_export.error is None:
            if resource_export.result is not None:
                logger.info(f'Fetched results: {resource_export.result}')
                print(resource_export.result)
            if export_all is False:
                gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
            logger.info(f'Exporting: {input_id}')
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_ead(include_unpublished=defaults["ead_export_default"]["_INCLUDE_UNPUB_"],
                                       include_daos=defaults["ead_export_default"]["_INCLUDE_DAOS_"],
                                       numbered_cs=defaults["ead_export_default"]["_NUMBERED_CS_"],
                                       ead3=defaults["ead_export_default"]["_USE_EAD3_"])
            if resource_export.error is None:
                logger.info(f'EAD export complete: {resource_export.result}')
                print(resource_export.result + "\n")
                if defaults["ead_export_default"]["_CLEAN_EADS_"] is True:
                    if defaults["ead_export_default"]["_KEEP_RAW_"] is True:
                        logger.info(f'EAD cleaning up record {resource_export.filepath}')
                        print("Cleaning up EAD record...")
                        valid, results = clean.cleanup_eads(resource_export.filepath, cleanup_options,
                                                            defaults["ead_export_default"]["_OUTPUT_DIR_"],
                                                            keep_raw_exports=True)
                        if valid:
                            logger.info(f'EAD cleanup complete: {results}')
                            print("Done")
                            print(results)
                            export_counter += 1
                            if export_all is False:
                                gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
                        else:
                            logger.info(f'XML validation error: {results}')
                            print("XML validation error\n" + results)
                    else:
                        logger.info(f'EAD cleaning up record {resource_export.filepath}')
                        print("Cleaning up EAD record...", end='', flush=True)
                        valid, results = clean.cleanup_eads(resource_export.filepath, cleanup_options,
                                                            defaults["ead_export_default"]["_OUTPUT_DIR_"])
                        if valid:
                            logger.info(f'EAD cleanup complete: {results}')
                            print("Done")
                            print(results)
                            export_counter += 1
                            if export_all is False:
                                gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
                        else:
                            logger.info(f'XML validation error: {results}')
                            print("XML validation error\n" + results)
                else:
                    export_counter += 1
                    if export_all is False:
                        gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
            else:
                logger.info(f'EAD export error: {resource_export.error}')
                print(resource_export.error + "\n")
                export_counter += 1
                gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
        else:
            logger.info(f'EAD fetch results error: {resource_export.error}')
            print(resource_export.error + "\n")
    if export_all is False:
        trailing_line = 76 - len(f'Finished {str(export_counter)} exports') - (len(str(export_counter)) - 1)
        logger.info(f'Finished EAD exports: {export_counter}')
        print("\n" + "-" * 55 + "Finished {} exports".format(str(export_counter)) + "-" * trailing_line + "\n")
        gui_window.write_event_value('-EAD_THREAD-', (threading.current_thread().name,))


def get_all_eads(input_ids, defaults, cleanup_options, repositories, client, gui_window):
    """
    Iterates through resources set to Publish = True and sends them to get_eads() to fetch and export files.

    Args:
        input_ids (dict): contains repository ASpace ID as key and all published resource IDs in a list as value.
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        cleanup_options (list): options a user wants to run against an EAD.xml file after export to clean the file.
        These include the following:
            "_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_", "_DEL_LANGTRAIL_",
            "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_DEL_ARCHIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_",
            "_DEL_ALLNS_"
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info

    Returns:
        None
    """
    export_all_counter = 0
    all_resources_counter = 0
    for resource_uris in input_ids.values():
        all_resources_counter += len(resource_uris)
    for repo_id, resource_uris in input_ids.items():
        for resource_uri in resource_uris:
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
            resource_json = client.get(f'/repositories/{str(repo_id)}/resources/{str(resource_uri)}').json()
            if resource_json["publish"] is True:
                get_eads(resource_uri, defaults, cleanup_options, repositories, client, repo_id, gui_window,
                         export_all=True)
            else:
                export_all_counter += -1
                all_resources_counter += -1
            export_all_counter += 1
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
    trailing_line = 76 - len(f'Finished {str(export_all_counter)} exports') - (len(str(export_all_counter)) - 1)
    logger.info(f'Finished EAD exports: {export_all_counter}')
    print("\n" + "-" * 55 + "Finished {} exports".format(str(export_all_counter)) + "-" * trailing_line + "\n")
    gui_window.write_event_value('-EAD_THREAD-', (threading.current_thread().name,))


def get_ead_options(defaults):
    """
    Write the options selected to the defaults.json file.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_ead_options

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default

    Returns:
        None
    """
    correct_opts = False
    while correct_opts is False:
        window_eadopt_active = True
        eadopt_layout = [[sg.Text("Choose EAD Export Options", font=("Roboto", 14)),
                          sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True,
                                  key="_EADOPT_HELP_")],
                         [sg.Checkbox("Include unpublished components", key="_INCLUDE_UNPUB_",
                                      default=defaults["ead_export_default"]["_INCLUDE_UNPUB_"])],
                         [sg.Checkbox("Include digital objects", key="_INCLUDE_DAOS_",
                                      default=defaults["ead_export_default"]["_INCLUDE_DAOS_"])],
                         [sg.Checkbox("Use numbered container levels", key="_NUMBERED_CS_",
                                      default=defaults["ead_export_default"]["_NUMBERED_CS_"])],
                         [sg.Checkbox("Convert to EAD3", key="_USE_EAD3_",
                                      default=defaults["ead_export_default"]["_USE_EAD3_"])],
                         [sg.Checkbox("Keep raw ASpace Exports", key="_KEEP_RAW_",
                                      default=defaults["ead_export_default"]["_KEEP_RAW_"])],
                         [sg.FolderBrowse(" Set raw ASpace output folder: ",
                                          initial_folder=defaults["ead_export_default"]["_SOURCE_DIR_"]),
                          sg.InputText(default_text=defaults["ead_export_default"]["_SOURCE_DIR_"],
                                       key="_SOURCE_DIR_")],
                         [sg.Checkbox("Clean EAD records on export", key="_CLEAN_EADS_",
                                      default=defaults["ead_export_default"]["_CLEAN_EADS_"])],
                         [sg.FolderBrowse(" Set clean ASpace output folder: ",
                                          initial_folder=defaults["ead_export_default"]["_OUTPUT_DIR_"]),
                          sg.InputText(default_text=defaults["ead_export_default"]["_OUTPUT_DIR_"],
                                       key="_OUTPUT_DIR_")],
                         [sg.Button(" Save Settings ", key="_SAVE_SETTINGS_EAD_", bind_return_key=True)]]
        eadopt_window = sg.Window("EAD Options", eadopt_layout)
        while window_eadopt_active is True:
            logger.info(f'User initiated EAD Options')
            event_eadopt, values_eadopt = eadopt_window.Read()
            if event_eadopt is None or event_eadopt == 'Cancel':
                logger.info(f'User cancelled EAD options')
                window_eadopt_active = False
                correct_opts = True
                eadopt_window.close()
            if event_eadopt == "_EADOPT_HELP_":
                logger.info(f'User opened EAD Options Help button')
                webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#e"
                                "ad-export-options",
                                new=2)
            if event_eadopt == "_SAVE_SETTINGS_EAD_":
                if values_eadopt["_KEEP_RAW_"] is False and values_eadopt["_CLEAN_EADS_"] is False:
                    logger.info(f'User selected EAD Options: _KEEP_RAW_ and _CLEAN_EADS_ - not allowed')
                    sg.Popup("WARNING!\nOne of the checkboxes from the following need to be checked:"
                             "\n\nKeep raw ASpace Exports\nClean EAD records on export")
                else:
                    if os.path.isdir(values_eadopt["_SOURCE_DIR_"]) is False:
                        logger.info(f'User input an invalid EAD _SOURCE_DIR_: {values_eadopt["_SOURCE_DIR_"]}')
                        sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
                    elif os.path.isdir(values_eadopt["_OUTPUT_DIR_"]) is False:
                        logger.info(f'User input an invalid EAD _OUTPUT_DIR_: {values_eadopt["_OUTPUT_DIR_"]}')
                        sg.popup("WARNING!\nYour input for the cleanup output is invalid."
                                 "\nPlease try another directory")
                    else:
                        logger.info(f'User selected EAD Options: {values_eadopt}')
                        with open("defaults.json", "w") as DEFAULT:
                            defaults["ead_export_default"]["_INCLUDE_UNPUB_"] = values_eadopt["_INCLUDE_UNPUB_"]
                            defaults["ead_export_default"]["_INCLUDE_DAOS_"] = values_eadopt["_INCLUDE_DAOS_"]
                            defaults["ead_export_default"]["_NUMBERED_CS_"] = values_eadopt["_NUMBERED_CS_"]
                            defaults["ead_export_default"]["_USE_EAD3_"] = values_eadopt["_USE_EAD3_"]
                            defaults["ead_export_default"]["_KEEP_RAW_"] = values_eadopt["_KEEP_RAW_"]
                            defaults["ead_export_default"]["_CLEAN_EADS_"] = values_eadopt["_CLEAN_EADS_"]
                            defaults["ead_export_default"]["_SOURCE_DIR_"] = str(Path(values_eadopt["_SOURCE_DIR_"]))
                            defaults["ead_export_default"]["_OUTPUT_DIR_"] = str(Path(values_eadopt["_OUTPUT_DIR_"]))
                            json.dump(defaults, DEFAULT)
                            DEFAULT.close()
                        window_eadopt_active = False
                        correct_opts = True
        eadopt_window.close()


def get_cleanup_defaults(cleanup_defaults, defaults):
    """
    Write the options selected to the defaults.json file.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_cleanup_defaults

    Args:
        cleanup_defaults (list): key strings listing all available cleanup options
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default

    Returns:
        cleanup_options (list): options a user wants to run against an EAD.xml file after export to clean the file.
        These include the following:
            "_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_", "_DEL_LANGTRAIL_",
            "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_DEL_ARCHIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_",
            "_DEL_ALLNS_"
    """
    cleanup_options = []
    window_adv_active = True
    winadv_col1 = [[sg.Checkbox("Add Resource ID as EADID", key="_ADD_EADID_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_EADID_"])],
                   [sg.Checkbox("Delete Empty Notes", key="_DEL_NOTES_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_NOTES_"])],
                   [sg.Checkbox("Remove '(), [], {}' from and Empty Extents", key="_CLN_EXTENTS_",
                                default=defaults["ead_cleanup_defaults"]["_CLN_EXTENTS_"])],
                   [sg.Checkbox("Add Certainty Attribute", key="_ADD_CERTAIN_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_CERTAIN_"])],
                   [sg.Checkbox("Add label='Mixed Materials' to containers without label", key="_ADD_LABEL_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_LABEL_"])],
                   [sg.Checkbox("Remove trailing . from langmaterial", key="_DEL_LANGTRAIL_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_LANGTRAIL_"])],
                   [sg.Checkbox("Delete Empty Containers", key="_DEL_CONTAIN_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_CONTAIN_"])]]
    winadv_col2 = [[sg.Checkbox("Add Barcode as physloc Tag", key="_ADD_PHYSLOC_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_PHYSLOC_"])],
                   [sg.Checkbox("Remove Archivists' Toolkit IDs", key="_DEL_ATIDS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_ATIDS_"])],
                   [sg.Checkbox("Remove Archon IDs", key="_DEL_ARCHIDS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_ARCHIDS_"])],
                   [sg.Checkbox("Remove xlink Prefixes from Digital Objects", key="_CNT_XLINKS_",
                                default=defaults["ead_cleanup_defaults"]["_CNT_XLINKS_"])],
                   [sg.Checkbox("Remove Unused Namespaces", key="_DEL_NMSPCS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_NMSPCS_"])],
                   [sg.Checkbox("Remove All Namespaces", key="_DEL_ALLNS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_ALLNS_"])]]
    layout_adv = [
        [sg.Text("Advanced Options for Cleaning EAD Records", font=("Roboto", 14)),
         sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True, key="_CLEANUP_HELP_")],
        [sg.Column(winadv_col1), sg.Column(winadv_col2)],
        [sg.Button(" Save Settings ", key="_SAVE_CLEAN_DEF_", bind_return_key=True)]
    ]
    window_adv = sg.Window("Change Cleanup Defaults", layout_adv)
    while window_adv_active is True:
        logger.info(f'User initiated EAD Cleanup Options')
        event_adv, values_adv = window_adv.Read()
        if event_adv == "_SAVE_CLEAN_DEF_":
            logger.info(f'User selected cleanup options: {values_adv}')
            for option_key, option_value in values_adv.items():
                if option_value is True:
                    if option_key in cleanup_defaults:
                        cleanup_options.append(option_key)
            with open("defaults.json", "w") as defaults_cleanup:
                defaults["ead_cleanup_defaults"]["_ADD_EADID_"] = values_adv["_ADD_EADID_"]
                defaults["ead_cleanup_defaults"]["_DEL_NOTES_"] = values_adv["_DEL_NOTES_"]
                defaults["ead_cleanup_defaults"]["_CLN_EXTENTS_"] = values_adv["_CLN_EXTENTS_"]
                defaults["ead_cleanup_defaults"]["_ADD_CERTAIN_"] = values_adv["_ADD_CERTAIN_"]
                defaults["ead_cleanup_defaults"]["_ADD_LABEL_"] = values_adv["_ADD_LABEL_"]
                defaults["ead_cleanup_defaults"]["_DEL_LANGTRAIL_"] = values_adv["_DEL_LANGTRAIL_"]
                defaults["ead_cleanup_defaults"]["_DEL_CONTAIN_"] = values_adv["_DEL_CONTAIN_"]
                defaults["ead_cleanup_defaults"]["_ADD_PHYSLOC_"] = values_adv["_ADD_PHYSLOC_"]
                defaults["ead_cleanup_defaults"]["_DEL_ATIDS_"] = values_adv["_DEL_ATIDS_"]
                defaults["ead_cleanup_defaults"]["_DEL_ARCHIDS_"] = values_adv["_DEL_ARCHIDS_"]
                defaults["ead_cleanup_defaults"]["_CNT_XLINKS_"] = values_adv["_CNT_XLINKS_"]
                defaults["ead_cleanup_defaults"]["_DEL_NMSPCS_"] = values_adv["_DEL_NMSPCS_"]
                defaults["ead_cleanup_defaults"]["_DEL_ALLNS_"] = values_adv["_DEL_ALLNS_"]
                json.dump(defaults, defaults_cleanup)
                defaults_cleanup.close()
            # window_adv_active = False
            window_adv.close()
            return cleanup_options
        if event_adv == "_CLEANUP_HELP_":
            logger.info(f'User opened EAD Cleanup Options Help button')
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#clean"
                            "up-options",
                            new=2)
        if event_adv is None:
            logger.info(f'User cancelled EAD Cleanup Options')
            cleanup_options = [option for option, bool_val in defaults["ead_cleanup_defaults"].items() if
                               bool_val is True]
            window_adv.close()
            return cleanup_options


def get_marcxml(input_ids, defaults, repositories, client, values_simple, gui_window, export_all=False):
    """
    Iterates through user input and sends them to as_export.py to fetch_results() and export_marcxml().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_marcxml

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict or int): values as entered with the run_gui() function, or repository ID for export all
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info
        export_all (bool): whether to pass URIs of all published resources to export

    Returns:
        None
    """
    resources = []
    export_counter = 0
    if export_all is True:
        resources = [input_ids]
        repo_id = values_simple
    else:
        repo_id = repositories[values_simple["_REPO_SELECT_"]]
        if "," in input_ids:
            csep_resources = [user_input.strip() for user_input in input_ids.split(",")]
            for resource in csep_resources:
                linebreak_resources = resource.splitlines()
                for lb_resource in linebreak_resources:
                    resources.append(lb_resource)
        else:
            resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        if export_all is True:
            logger.info(f'Beginning MARCXML export: EXPORT_ALL')
            resource_export = asx.ASExport(input_id, repo_id, client,
                                           output_dir=defaults["marc_export_default"]["_OUTPUT_DIR_"], export_all=True)
        else:
            logger.info(f'Beginning MARCXML export: {resources}')
            resource_export = asx.ASExport(input_id, repo_id, client,
                                           output_dir=defaults["marc_export_default"]["_OUTPUT_DIR_"])
        resource_export.fetch_results()
        if resource_export.error is None:
            logger.info(f'Exporting: {input_id}')
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_marcxml(
                include_unpublished=defaults["marc_export_default"]["_INCLUDE_UNPUB_"])
            if resource_export.error is None:
                logger.info(f'MARCXML export complete: {resource_export.result}')
                print(resource_export.result + "\n")
                export_counter += 1
                if export_all is False:
                    gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
            else:
                logger.info(f'MARCXML export error: {resource_export.error}')
                print(resource_export.error + "\n")
        else:
            logger.info(f'MARCXML export error: {resource_export.error}')
            print(resource_export.error)
            export_counter += 1
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
    if export_all is False:
        trailing_line = 76 - len(f'Finished {str(export_counter)} exports') - (len(str(export_counter)) - 1)
        logger.info(f'Finished MARCXML exports: {export_counter}')
        print("\n" + "-" * 55 + "Finished {} exports".format(str(export_counter)) + "-" * trailing_line + "\n")
        gui_window.write_event_value('-MARCXML_THREAD-', (threading.current_thread().name,))


def get_all_marcxml(input_ids, defaults, repositories, client, gui_window):
    """
    Iterates through resources set to Publish = True and sends them to get_marcxml() to fetch and export files.

    Args:
        input_ids (dict): contains repository ASpace ID as key and all published resource IDs in a list as value.
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info

    Returns:
        None
    """
    export_all_counter = 0
    all_resources_counter = 0
    for resource_uris in input_ids.values():
        all_resources_counter += len(resource_uris)
    for repo_id, resource_uris in input_ids.items():
        for resource_uri in resource_uris:
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
            resource_json = client.get(f'/repositories/{str(repo_id)}/resources/{str(resource_uri)}').json()
            if resource_json["publish"] is True:
                get_marcxml(resource_uri, defaults, repositories, client, repo_id, gui_window, export_all=True)
            else:
                export_all_counter += -1
                all_resources_counter += -1
            export_all_counter += 1
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
    trailing_line = 76 - len(f'Finished {str(export_all_counter)} exports') - (len(str(export_all_counter)) - 1)
    logger.info(f'Finished MARCXML exports: {export_all_counter}')
    print("\n" + "-" * 55 + "Finished {} exports".format(str(export_all_counter)) + "-" * trailing_line + "\n")
    gui_window.write_event_value('-MARCXML_THREAD-', (threading.current_thread().name,))


def get_marc_options(defaults):
    """
    Write the options selected to the defaults.json file.

    This function opens a window in the GUI that allows a user to choose specific export options. These options include:

        1. Include unpublished components (default is false)
        2. Open output folder on export (default is false)
        3. Set output folder

    The function will write the options selected to the defaults.json file.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_marc_options

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default

    Returns:
        None
    """
    window_marc_active = True
    marc_layout = [[sg.Text("Choose MARCXML Export Options", font=("Roboto", 14)),
                    sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True, key="_MARCOPT_HELP_")],
                   [sg.Checkbox("Include unpublished components", key="_INCLUDE_UNPUB_",
                                default=defaults["marc_export_default"]["_INCLUDE_UNPUB_"])],
                   [sg.Checkbox("Open output folder on export", key="_KEEP_RAW_",
                                default=defaults["marc_export_default"]["_KEEP_RAW_"])],
                   [sg.FolderBrowse(" Set output folder: ",
                                    initial_folder=defaults["marc_export_default"]["_OUTPUT_DIR_"]),
                    sg.InputText(default_text=defaults["marc_export_default"]["_OUTPUT_DIR_"], key="_MARC_OUT_DIR_")],
                   [sg.Button(" Save Settings ", key="_SAVE_SETTINGS_MARC_", bind_return_key=True)]
                   ]
    window_marc = sg.Window("MARCXML Export Options", marc_layout)
    while window_marc_active is True:
        event_marc, values_marc = window_marc.Read()
        logger.info(f'User initiated MARCXML Options')
        if event_marc is None or event_marc == 'Cancel':
            logger.info(f'User cancelled MARCXML Options')
            window_marc_active = False
            window_marc.close()
        if event_marc == "_MARCOPT_HELP_":
            logger.info(f'User opened MARCXML Options Help button')
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#marcx"
                            "ml-screen",
                            new=2)
        if event_marc == "_SAVE_SETTINGS_MARC_":
            if os.path.isdir(values_marc["_MARC_OUT_DIR_"]) is False:
                logger.info(f'User input an invalid MARCXML _MARC_OUT_DIR_: {values_marc["_MARC_OUT_DIR_"]}')
                sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
            else:
                logger.info(f'User selected MARCXML options: {values_marc}')
                with open("defaults.json", "w") as defaults_marc:
                    defaults["marc_export_default"]["_INCLUDE_UNPUB_"] = values_marc["_INCLUDE_UNPUB_"]
                    defaults["marc_export_default"]["_KEEP_RAW_"] = values_marc["_KEEP_RAW_"]
                    defaults["marc_export_default"]["_OUTPUT_DIR_"] = str(Path(values_marc["_MARC_OUT_DIR_"]))
                    json.dump(defaults, defaults_marc)
                    defaults_marc.close()
                window_marc_active = False
        window_marc.close()


def get_pdfs(input_ids, defaults, repositories, client, values_simple, gui_window, export_all=False):
    """
    Iterates through the user input and sends them to as_export.py to fetch_results() and export_pdf().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_pdfs

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict or int): values as entered with the run_gui() function, or repository ID for export all
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info
        export_all (bool): whether to pass URIs of all published resources to export

    Returns:
        None
    """
    resources = []
    export_counter = 0
    if export_all is True:
        resources = [input_ids]
        repo_id = values_simple
    else:
        repo_id = repositories[values_simple["_REPO_SELECT_"]]
        if "," in input_ids:
            csep_resources = [user_input.strip() for user_input in input_ids.split(",")]
            for resource in csep_resources:
                linebreak_resources = resource.splitlines()
                for lb_resource in linebreak_resources:
                    resources.append(lb_resource)
        else:
            resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        if export_all is True:
            logger.info(f'Beginning PDF export: EXPORT_ALL')
            resource_export = asx.ASExport(input_id, repo_id, client,
                                           output_dir=defaults["pdf_export_default"]["_OUTPUT_DIR_"], export_all=True)
        else:
            logger.info(f'Beginning PDF export: {resources}')
            resource_export = asx.ASExport(input_id, repo_id, client,
                                           output_dir=defaults["pdf_export_default"]["_OUTPUT_DIR_"])
        resource_export.fetch_results()
        if resource_export.error is None:
            logger.info(f'Exporting: {input_id}')
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_pdf(include_unpublished=defaults["ead_export_default"]["_INCLUDE_UNPUB_"],
                                       include_daos=defaults["pdf_export_default"]["_INCLUDE_DAOS_"],
                                       numbered_cs=defaults["pdf_export_default"]["_NUMBERED_CS_"],
                                       ead3=defaults["pdf_export_default"]["_USE_EAD3_"])
            if resource_export.error is None:
                logger.info(f'Export PDF complete: {resource_export.result}')
                print(resource_export.result + "\n")
                export_counter += 1
                if export_all is False:
                    gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
            else:
                logger.info(f'PDF export error: {resource_export.error}')
                print(resource_export.error + "\n")
                export_counter += 1
                gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
        else:
            logger.info(f'PDF export error: {resource_export.error}')
            print(resource_export.error)
    if export_all is False:
        trailing_line = 76 - len(f'Finished {str(export_counter)} exports') - (len(str(export_counter)) - 1)
        logger.info(f'Finished PDF exports: {export_counter}')
        print("\n" + "-" * 55 + "Finished {} exports".format(str(export_counter)) + "-" * trailing_line + "\n")
        gui_window.write_event_value('-PDF_THREAD-', (threading.current_thread().name,))


def get_all_pdfs(input_ids, defaults, repositories, client, gui_window):
    """
    Iterates through resources set to Publish = True and sends them to get_pdfs() to fetch and export files.

    Args:
        input_ids (dict): contains repository ASpace ID as key and all published resource IDs in a list as value.
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info

    Returns:
        None
    """
    export_all_counter = 0
    all_resources_counter = 0
    for resource_uris in input_ids.values():
        all_resources_counter += len(resource_uris)
    for repo_id, resource_uris in input_ids.items():
        for resource_uri in resource_uris:
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
            resource_json = client.get(f'/repositories/{str(repo_id)}/resources/{str(resource_uri)}').json()
            if resource_json["publish"] is True:
                get_pdfs(resource_uri, defaults, repositories, client, repo_id, gui_window, export_all=True)
            else:
                export_all_counter += -1
                all_resources_counter += -1
            export_all_counter += 1
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
    trailing_line = 76 - len(f'Finished {str(export_all_counter)} exports') - (len(str(export_all_counter)) - 1)
    logger.info(f'Finished PDF exports: {export_all_counter}')
    print("\n" + "-" * 55 + "Finished {} exports".format(str(export_all_counter)) + "-" * trailing_line + "\n")
    gui_window.write_event_value('-PDF_THREAD-', (threading.current_thread().name,))


def get_pdf_options(defaults):
    """
    Write the options selected to the defaults.json file.

    This function opens a window in the GUI that allows a user to choose specific export options. These options include:

        1. Include unpublished components (default is false)
        2. Include digital objects (default is true)
        3. Use numbered container levels (default is true)
        4. Convert to EAD3 (default is false)
        5. Open ASpace Exports on Export (default is false)
        6. Set output folder

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_pdf_options

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default

    Returns:
        None
    """
    window_pdf_active = True
    pdf_layout = [[sg.Text("Choose PDF Export Options", font=("Roboto", 14)),
                   sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True, key="_PDFOPT_HELP_")],
                  [sg.Checkbox("Include unpublished components", key="_INCLUDE_UNPUB_",
                               default=defaults["pdf_export_default"]["_INCLUDE_UNPUB_"])],
                  [sg.Checkbox("Include digital objects", key="_INCLUDE_DAOS_",
                               default=defaults["pdf_export_default"]["_INCLUDE_DAOS_"])],
                  [sg.Checkbox("Use numbered container levels", key="_NUMBERED_CS_",
                               default=defaults["pdf_export_default"]["_NUMBERED_CS_"])],
                  [sg.Checkbox("Convert to EAD3", key="_USE_EAD3_",
                               default=defaults["pdf_export_default"]["_USE_EAD3_"])],
                  [sg.Checkbox("Open ASpace Exports on Export", key="_KEEP_RAW_",
                               default=defaults["pdf_export_default"]["_KEEP_RAW_"])],
                  [sg.FolderBrowse(" Set output folder: ",
                                   initial_folder=defaults["pdf_export_default"]["_OUTPUT_DIR_"]),
                   sg.InputText(default_text=defaults["pdf_export_default"]["_OUTPUT_DIR_"], key="_OUTPUT_DIR_")],
                  [sg.Button(" Save Settings ", key="_SAVE_SETTINGS_PDF_", bind_return_key=True)]
                  ]
    window_pdf = sg.Window("PDF Export Options", pdf_layout)
    while window_pdf_active is True:
        event_pdf, values_pdf = window_pdf.Read()
        logger.info(f'User initiated PDF Options')
        if event_pdf is None or event_pdf == 'Cancel':
            logger.info(f'User cancelled PDF Options')
            window_pdf_active = False
            window_pdf.close()
        if event_pdf == "_PDFOPT_HELP_":
            logger.info(f'User opened PDF Options Help button')
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#pdf-e"
                            "xport-options",
                            new=2)
        if event_pdf == "_SAVE_SETTINGS_PDF_":
            if os.path.isdir(values_pdf["_OUTPUT_DIR_"]) is False:
                logger.info(f'User input an invalid PDF _OUTPUT_DIR_: {values_pdf["_OUTPUT_DIR_"]}')
                sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
            else:
                logger.info(f'User selected PDF Options: {values_pdf}')
                with open("defaults.json", "w") as defaults_pdf:
                    defaults["pdf_export_default"]["_INCLUDE_UNPUB_"] = values_pdf["_INCLUDE_UNPUB_"]
                    defaults["pdf_export_default"]["_INCLUDE_DAOS_"] = values_pdf["_INCLUDE_DAOS_"]
                    defaults["pdf_export_default"]["_NUMBERED_CS_"] = values_pdf["_NUMBERED_CS_"]
                    defaults["pdf_export_default"]["_USE_EAD3_"] = values_pdf["_USE_EAD3_"]
                    defaults["pdf_export_default"]["_KEEP_RAW_"] = values_pdf["_KEEP_RAW_"]
                    defaults["pdf_export_default"]["_OUTPUT_DIR_"] = str(Path(values_pdf["_OUTPUT_DIR_"]))
                    json.dump(defaults, defaults_pdf)
                    defaults_pdf.close()
                window_pdf_active = False
        window_pdf.close()


def get_contlabels(input_ids, defaults, repositories, client, values_simple, gui_window, export_all=False):
    """
    Iterates through the user input and sends them to as_export.py to fetch_results() and export_labels().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_contlabels

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict or int): values as entered with the run_gui() function, or repository ID for export all
        gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info
        export_all (bool): whether to pass URIs of all published resources to export

    Returns:
        None
    """
    resources = []
    export_counter = 0
    if export_all is True:
        resources = [input_ids]
        repo_id = values_simple
    else:
        repo_id = repositories[values_simple["_REPO_SELECT_"]]
        if "," in input_ids:
            csep_resources = [user_input.strip() for user_input in input_ids.split(",")]
            for resource in csep_resources:
                linebreak_resources = resource.splitlines()
                for lb_resource in linebreak_resources:
                    resources.append(lb_resource)
        else:
            resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        if export_all is True:
            logger.info(f'Beginning CONTLABELS export: EXPORT_ALL')
            resource_export = asx.ASExport(input_id, repo_id, client,
                                           output_dir=defaults["labels_export_default"], export_all=True)
        else:
            logger.info(f'Beginning CONTLABELS export: {resources}')
            resource_export = asx.ASExport(input_id, repo_id, client,
                                           output_dir=defaults["labels_export_default"])
        resource_export.fetch_results()
        if resource_export.error is None:
            logger.info(f'Exporting: {input_id}')
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_labels()
            if resource_export.error is None:
                logger.info(f'Export CONTLABELS complete: {resource_export.result}')
                print(resource_export.result + "\n")
                export_counter += 1
                if export_all is False:
                    gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
            else:
                logger.info(f'CONTLABELS export error: {resource_export.error}')
                print(resource_export.error + "\n")
        else:
            logger.info(f'CONTLABELS export error: {resource_export.error}')
            print(resource_export.error)
            export_counter += 1
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_counter, len(resources)))
    if export_all is False:
        trailing_line = 76 - len(f'Finished {str(export_counter)} exports') - (len(str(export_counter)) - 1)
        logger.info(f'Finished CONTLABELS exports: {export_counter}')
        print("\n" + "-" * 55 + "Finished {} exports".format(str(export_counter)) + "-" * trailing_line + "\n")
        gui_window.write_event_value('-CONTLABEL_THREAD-', (threading.current_thread().name,))


def get_all_contlabels(input_ids, defaults, repositories, client, gui_window):
    """
        Iterates through resources set to Publish = True and sends them to get_contlabels() to fetch and export files.

        Args:
            input_ids (dict): contains repository ASpace ID as key and all published resource IDs in a list as value.
            defaults (dict): contains the data from defaults.json file, all data the user has specified as default
            repositories (dict): repositories as listed in the ArchivesSpace instance
            client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
            gui_window (PySimpleGUI Object): is the GUI window for the app. See PySimpleGUI.org for more info

        Returns:
            None
        """
    export_all_counter = 0
    all_resources_counter = 0
    for resource_uris in input_ids.values():
        all_resources_counter += len(resource_uris)
    for repo_id, resource_uris in input_ids.items():
        for resource_uri in resource_uris:
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
            resource_json = client.get(f'/repositories/{str(repo_id)}/resources/{str(resource_uri)}').json()
            if resource_json["publish"] is True:
                get_contlabels(resource_uri, defaults, repositories, client, repo_id, gui_window, export_all=True)
            else:
                export_all_counter += -1
                all_resources_counter += -1
            export_all_counter += 1
            gui_window.write_event_value('-EXPORT_PROGRESS-', (export_all_counter, all_resources_counter))
    trailing_line = 76 - len(f'Finished {str(export_all_counter)} exports') - (len(str(export_all_counter)) - 1)
    logger.info(f'Finished CONTLABELS exports: {export_all_counter}')
    print("\n" + "-" * 55 + "Finished {} exports".format(str(export_all_counter)) + "-" * trailing_line + "\n")
    gui_window.write_event_value('-CONTLABEL_THREAD-', (threading.current_thread().name,))


def upload_files_xtf(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path,
                     xtf_lazy_path, values_upl, gui_window):
    """
    Uploads files to XTF.
    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        xtf_hostname (str): the host URL for the XTF instance
        xtf_username (str): user's XTF username
        xtf_password (str): user's XTF password
        xtf_remote_path (str): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_index_path (str): the path (file) where the textIndexer for XTF is - used to run the index
        xtf_lazy_path (str): the path (folder) where the xml.lazy files are stored - used to update permissions
        values_upl (dict): the GUI values a user chose when selecting files to upload to XTF
        gui_window (PySimpleGUI object): the GUI window used by PySimpleGUI. Used to return an event
    Returns:
        None
    """
    remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path)
    logger.info(f'Uploading files to XTF. Files: {values_upl["_SELECT_FILES_"]}, Remote Path: {xtf_remote_path}, '
                f'Local path: {defaults["xtf_default"]["xtf_local_path"]}')
    print("Uploading files...")
    xtf_files = fetch_local_files(defaults["xtf_default"]["xtf_local_path"], values_upl["_SELECT_FILES_"])
    upload_output = remote.bulk_upload(xtf_files)
    logger.info(f'Uploading results: {upload_output}')
    print(upload_output)
    for file in xtf_files:
        update_permissions = remote.execute_commands(['/bin/chmod 664 {}/{}'.format(defaults["xtf_default"]
                                                                                    ["xtf_remote_path"],
                                                                                    Path(file).name)])
        logger.info(f'Updated file permissions: {update_permissions}')
        print(update_permissions)
    if defaults["xtf_default"]["_REINDEX_AUTO_"] is True:
        logger.info(f'Re-indexing files...')
        index_xtf(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path,
                  gui_window, xtf_files)
    else:
        print("-" * 135)
    remote.disconnect()
    gui_window.write_event_value('-XTFUP_THREAD-', (threading.current_thread().name,))


def delete_files_xtf(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path,
                     values_del, gui_window):
    """
    Delete files from XTF.
    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        xtf_hostname (str): the host URL for the XTF instance
        xtf_username (str): user's XTF username
        xtf_password (str): user's XTF password
        xtf_remote_path (str): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_index_path (str): the path (file) where the textIndexer for XTF is - used to run the index
        xtf_lazy_path (str): the path (folder) where the xml.lazy files are stored - used to update permissions
        values_del (dict): the GUI values a user chose when selecting files to upload to XTF
        gui_window (PySimpleGUI object): the GUI window used by PySimpleGUI. Used to return an event
    Returns:
        None
    """
    remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path)
    logger.info(f'Deleting files from XTF. Files: {values_del["_SELECT_FILES_"]}, Remote Path: {xtf_remote_path}, '
                f'Local path: {defaults["xtf_default"]["xtf_local_path"]}')
    print("Deleting files...")
    xtf_files = [str(defaults["xtf_default"]["xtf_remote_path"] + "/" + str(file)) for file in
                 values_del["_SELECT_FILES_"]]
    try:
        for file in xtf_files:
            print(file)
            cmds_output = remote.execute_commands(['rm {}'.format(file)])
            logger.info(f'Deleted file from XTF: {cmds_output}')
            print(cmds_output)
        print("-" * 135)
        if defaults["xtf_default"]["_REINDEX_AUTO_"] is True:
            logger.info(f'Re-indexing files...')
            index_xtf(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path,
                      xtf_lazy_path, gui_window)
    except Exception as e:
        logger.error(f'Deleting files from XTF error: {e}')
        print("An error occurred: " + str(e))
    remote.disconnect()
    gui_window.write_event_value('-XTFDEL_THREAD-', (threading.current_thread().name,))


def index_xtf(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path,
              gui_window, xtf_files=None):
    """
    Runs a re-index of all changed or new files in XTF. It is not a clean re-index.
    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        xtf_hostname (str): the host URL for the XTF instance
        xtf_username (str): user's XTF username
        xtf_password (str): user's XTF password
        xtf_remote_path (str): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_index_path (str): the path (file) where the textIndexer for XTF is - used to run the index
        xtf_lazy_path (str): the path (folder) where the lazy files are generated from an index, used to set permissions
        gui_window (PySimpleGUI object): the GUI window used by PySimpleGUI. Used to return an event
        xtf_files (list, optional): the list of file paths of files that were uploaded
    Returns:
        None
    """
    logger.info(f'Beginning XTF re-index...')
    print("Beginning Re-Index, this may take awhile...")
    remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path)
    if xtf_files is None:
        try:
            cmds_output = remote.execute_commands(
                ['{} -index default'.format(defaults["xtf_default"]["xtf_indexer_path"]),
                 '/bin/chmod 664 {}/*'.format(defaults["xtf_default"]["xtf_lazyindex_path"])])
            logger.info(f'Re-index XTF complete: {cmds_output}')
            print(cmds_output)
            print("-" * 135)
        except Exception as e:
            logger.error(f'Re-index XTF error: {e}')
            print("An error occurred: " + str(e))
    else:
        try:
            logger.info(f'Re-indexing XTF .lazy files: {defaults["xtf_default"]["xtf_indexer_path"]}')
            commands = ['{} -index default'.format(defaults["xtf_default"]["xtf_indexer_path"])]
            for file in xtf_files:
                lazyfile = Path(file).name + ".lazy"
                commands.append('/bin/chmod 664 {}/{}'.format(defaults["xtf_default"]["xtf_lazyindex_path"], lazyfile))
            cmds_output = remote.execute_commands(commands)
            logger.info(f'Re-index XTF complete: {cmds_output}')
            print(cmds_output)
            print("-" * 135)
        except Exception as e:
            logger.error(f'Re-index XTF error: {e}')
            print("An error occurred: " + str(e))
    remote.disconnect()
    gui_window.write_event_value('-XTFIND_THREAD-', (threading.current_thread().name,))


def get_remote_files(defaults, xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path,
                     xtf_lazy_path):
    """
    Gets all of the files in the remote path directory currently on the XTF server.

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        xtf_hostname (str): the host URL for the XTF instance
        xtf_username (str): user's XTF username
        xtf_password (str): user's XTF password
        xtf_remote_path (str): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_index_path (str): the path (file) where the textIndexer for XTF is - used to run the index
        xtf_lazy_path (str): the path (folder) where the lazy files are generated from an index, used to set permissions

    Returns:
        remote_files (list): a sorted list of all the files in the remote path directory
    """
    logger.info(f'Getting remote files from XTF: {xtf_remote_path}')
    remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path)
    remote_files = sort_list(remote.execute_commands(
        ['ls {}'.format(defaults["xtf_default"]["xtf_remote_path"])]).splitlines())
    remote.disconnect()
    return remote_files


def get_xtf_options(defaults):
    """
    Set options for uploading and re-indexing records to XTF.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_xtf_options

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default

    Returns:
        None
    """
    xtf_option_active = True
    xtf_option_layout = [[sg.Text("Choose XTF Options", font=("Roboto", 14)),
                          sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True,
                                  key="_XTFOPT_HELP_")],
                         [sg.Checkbox("Re-index changed records after upload/delete", key="_REINDEX_AUTO_",
                                      default=defaults["xtf_default"]["_REINDEX_AUTO_"])],
                         [sg.FolderBrowse(button_text=" Select source folder: ",
                                          initial_folder=defaults["xtf_default"]["xtf_local_path"]),
                          sg.InputText(default_text=defaults["xtf_default"]["xtf_local_path"], key="_XTF_SOURCE_")],
                         [sg.Button(" Change XTF Login Credentials ", key="_XTFOPT_CREDS_")],
                         [sg.Button(" Save Settings ", key="_SAVE_SETTINGS_XTF_", bind_return_key=True)]
                         ]
    window_xtf_option = sg.Window("XTF Options", xtf_option_layout)
    while xtf_option_active is True:
        event_xtfopt, values_xtfopt = window_xtf_option.Read()
        logger.info(f'User initiated XTF Options')
        if event_xtfopt is None or event_xtfopt == 'Cancel':
            logger.info(f'User cancelled XTF Options')
            xtf_option_active = False
            window_xtf_option.close()
        if event_xtfopt == "_XTFOPT_HELP_":
            logger.info(f'User opened XTF Options Help button')
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#xtf-f"
                            "rame",
                            new=2)
        if event_xtfopt == "_XTFOPT_CREDS_":
            get_xtf_log(defaults)
        if event_xtfopt == "_SAVE_SETTINGS_XTF_":
            if os.path.isdir(values_xtfopt["_XTF_SOURCE_"]) is False:
                logger.info(f'User input an invalid PDF _OUTPUT_DIR_: {values_xtfopt["_XTF_SOURCE_"]}')
                sg.popup("WARNING!\nYour input for the upload folder is invalid.\nPlease try another directory")
            else:
                logger.info(f'User selected XTF Options: {values_xtfopt}')
                with open("defaults.json", "w") as defaults_xtf:
                    defaults["xtf_default"]["_REINDEX_AUTO_"] = values_xtfopt["_REINDEX_AUTO_"]
                    defaults["xtf_default"]["xtf_local_path"] = values_xtfopt["_XTF_SOURCE_"]
                    json.dump(defaults, defaults_xtf)
                    defaults_xtf.close()
                xtf_option_active = False
                window_xtf_option.close()


def open_file(filepath):
    """
    Takes a filepath and opens the folder according to Windows, Mac, or Linux.

    Args:
        filepath (str): the filepath of the folder/directory a user wants to open

    Returns:
        None
    """
    logger.info(f'Fetching filepath: {filepath}')
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", filepath])
    else:
        subprocess.Popen(["xdg-open", filepath])


def fetch_local_files(local_file_dir, select_files):
    """
    Upload local files to remote host.

    SOURCE: Todd Birchard, 'SSH & SCP in Python with Paramiko',
    https://hackersandslackers.com/automate-ssh-scp-python-paramiko/

    Args:
        local_file_dir (str): the local file directory path used to determine what file to use for uploading to XTF
        select_files (list): files to be uploaded to XTF

    Returns:
        (list): contains filepaths for files to be uploaded to XTF
    """
    logger.info(f'Fetching local files: {local_file_dir}, {select_files}')
    local_files = os.walk(local_file_dir)
    for root, dirs, files in local_files:
        return [str(Path(root, file)) for file in files if file in select_files]


def setup_files():
    """
    Checks for directories in the current directory the GUI or .exe is located and tries to open defaults.json

    Returns:
        json_data (dict): contains data from defaults.json for user's default settings
    """
    logger.info(f'Checking setup files...')
    current_directory = os.getcwd()
    for root, directories, files in os.walk(current_directory):
        if "clean_eads" in directories:
            continue
        elif "source_eads" in directories:
            continue
        elif "source_marcs" in directories:
            continue
        elif "source_pdfs" in directories:
            continue
        elif "source_labels" in directories:
            continue
        else:
            dsetup.create_default_folders()
    try:
        json_data = dsetup.set_defaults_file()
        return json_data
    except Exception as defaults_error:
        logger.error(f'Error checking defaults.json file: {defaults_error}')
        print(str(defaults_error) + "\nThere was an error checking the defaults.json file. "
                                    "Please delete your defaults.json file and run the program again")


def sort_list(input_list):
    """
    Sorts a list in human readable order. Source: https://blog.codinghorror.com/sorting-for-humans-natural-sort-order/

    Args:
        input_list (list): a list to be sorted

    Returns:
        A list sorted in human readable order
    """
    logger.info(f'Sorting list...')
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(input_list, key=alphanum_key)


def start_thread(function, args, gui_window):
    """
    Starts a thread and disables buttons to prevent multiple requests/threads.

    Args:
        function (function): the function to pass to the thread
        args (tuple): the arguments to pass to the function with ending ,. Ex. (arg, arg, arg,)
        gui_window (PySimpleGUI object): the GUI window used by PySimpleGUI. Used to return an event

    Returns:
        None
    """
    logger.info(f'Starting thread: {function}')
    ead_thread = threading.Thread(target=function, args=args)
    ead_thread.start()
    gui_window[f'{"_EXPORT_EAD_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_ALLEADS_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_MARCXML_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_ALLMARCXMLS_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_LABEL_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_ALLCONTLABELS_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_PDF_"}'].update(disabled=True)
    gui_window[f'{"_EXPORT_ALLPDFS_"}'].update(disabled=True)


# sg.theme_previewer()
if __name__ == "__main__":
    logger.info(f'Version Info:\n{sg.get_versions()}')
    run_gui(setup_files())
