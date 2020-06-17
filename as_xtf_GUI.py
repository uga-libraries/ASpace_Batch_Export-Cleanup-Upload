import os
import platform
import subprocess
import sys
import webbrowser
import json
from pathlib import Path

import PySimpleGUI as sg
from asnake.client import ASnakeClient

import as_export as asx
import cleanup as clean
import xtf_upload as xup
import setup as setup


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
    sg.ChangeLookAndFeel('LightBlue2')
    as_username, as_password, as_api, close_program_as, client, version, repositories, xtf_version = \
        get_aspace_log(defaults, xtf_checkbox=True)
    if close_program_as is True:
        sys.exit()
    # For XTF Users Only
    rid_box_len = 36
    if xtf_version is True:
        xtf_username, xtf_password, xtf_hostname, xtf_remote_path, xtf_indexer_path, close_program_xtf = \
            get_xtf_log(defaults, login=True)
        if close_program_xtf is True:
            sys.exit()
        rid_box_len = 44
    cleanup_defaults = ["_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_",
                        "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_",
                        "_DEL_ALLNS_"]
    cleanup_options = [option for option, bool_val in defaults["ead_cleanup_defaults"].items() if bool_val is True]
    menu_def = [['File',
                 ['Clear Raw ASpace Export Folder',
                  'Clear Cleaned EAD Folder',
                  '---',
                  'Reset Defaults',
                  '---',
                  'Exit']
                 ],
                ['Edit',
                 ['Change ASpace Login Credentials',
                  '---',
                  'Change XTF Login Credentials',
                  'Change XTF Options',
                  '---',
                  'Change EAD Cleanup Defaults',
                  'Change EAD Export Options',
                  '---',
                  'Change MARCXML Export Options',
                  '---',
                  'Change PDF Export Options']
                 ],
                ['Help',
                 ['User Manual',
                  'About']
                 ]
                ]
    if xtf_version is False:
        for menu_option in menu_def:
            if isinstance(menu_option, list):
                for file_option in menu_option:
                    if isinstance(file_option, list):
                        if file_option[0] != "Clear Raw ASpace Export Folder" and file_option[0] != "User Manual":
                            file_option.remove("---")
                            file_option.remove("Change XTF Login Credentials")
                            file_option.remove("Change XTF Options")
    ead_layout = [[sg.Button(button_text=" EXPORT ", key="_EXPORT_EAD_"),
                   sg.Text("* The program may become unresponsive")],
                  [sg.Text("Options", font=("Roboto", 13)),
                   sg.Text(" " * 123)],
                  [sg.Button(" EAD Export Options ", key="_EAD_OPTIONS_", ),
                   sg.Button(" Cleanup Options ", key="Change Cleanup Defaults")],
                  [sg.Text("Output", font=("Roboto", 12))],
                  [sg.Button(button_text=" Open Cleaned EAD Folder ", key="_OPEN_CLEAN_B_"),
                   sg.Button(button_text=" Open Raw ASpace Exports ", key="_OPEN_RAW_EXPORTS_")]
                  ]
    xtf_layout = [[sg.Button(button_text=" Upload Files ", key="_UPLOAD_"),
                   sg.Text(" " * 2),
                   sg.Button(button_text=" Index Changed Records ", key="_INDEX_"),
                   sg.Text("* The program may become unresponsive")],
                  [sg.Text("Options", font=("Roboto", 13)),
                   sg.Text(" " * 123)],
                  [sg.Button(button_text=" XTF Options ", key="_XTF_OPTIONS_")]
                  ]
    marc_layout = [[sg.Button(button_text=" EXPORT ", key="_EXPORT_MARCXML_"),
                    sg.Text("* The program may become unresponsive", font=("Roboto", 11))],
                   [sg.Text("Options", font=("Roboto", 13))],
                   [sg.Button(" MARCXML Export Options ", key="_MARCXML_OPTIONS_")],
                   [sg.Button(button_text=" Open Output ", key="_OPEN_MARC_DEST_")],
                   [sg.Text(" " * 140)]
                   ]
    contlabel_layout = [[sg.Button(button_text=" EXPORT ", key="_EXPORT_LABEL_"),
                         sg.Text("* The program may become unresponsive")],
                        [sg.Text("Options", font=("Roboto", 13)),
                         sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True,
                                 key="_CONTOPT_HELP_")],
                        [sg.Button(button_text=" Open Output ", key="_OPEN_LABEL_DEST_")],
                        [sg.FolderBrowse(" Choose Output Folder: ", key="_OUTPUT_DIR_LABEL_",
                                         initial_folder=defaults["labels_export_default"]),
                         sg.InputText(defaults["labels_export_default"], key="_OUTPUT_DIR_LABEL_INPUT_",
                                      enable_events=True)],
                        [sg.Text(" " * 140)]
                        ]
    pdf_layout = [[sg.Text("WARNING:", font=("Roboto", 18), text_color="Red"),
                   sg.Text("Not compatible with ArchivesSpace versions 2.6.0 - 2.7.1\n"
                           "Your ArchivesSpace version is: {}".format(version), font=("Roboto", 13))],
                  [sg.Button(button_text=" EXPORT ", key="_EXPORT_PDF_"),
                   sg.Text("* The program may become unresponsive")],
                  [sg.Text("Options", font=("Roboto", 13)),
                   sg.Text(" " * 125)],
                  [sg.Button(" PDF Export Options ", key="_PDF_OPTIONS_"),
                   sg.Button(button_text=" Open Output ", key="_OPEN_PDF_DEST_")]
                  ]
    simple_layout_col1 = [[sg.Text("Enter Resource Identifiers here:", font=("Roboto", 12))],
                          [sg.Multiline(key="resource_id_input", size=(35, rid_box_len), focus=True)]
                          ]
    simple_layout_col2 = [[sg.Text("Choose your export option:", font=("Roboto", 12))],
                          [sg.Radio("EAD", "RADIO1", key="_EXPORT_EAD_RAD_", default=True, enable_events=True),
                           sg.Radio("MARCXML", "RADIO1", key="_EXPORT_MARCXML_RAD_", enable_events=True),
                           sg.Radio("Container Labels", "RADIO1", key="_EXPORT_CONTLABS_RAD_", enable_events=True),
                           sg.Radio("PDF", "RADIO1", key="_EXPORT_PDF_RAD_", enable_events=True)],
                          [sg.Text("Choose your repository:", font=("Roboto", 12))],
                          [sg.DropDown([repo for repo in repositories.keys()], readonly=True,
                                       default_value=defaults["repo_default"]["_REPO_NAME_"], key="_REPO_SELECT_",
                                       font=("Roboto", 11)),
                           sg.Button(" SAVE ", key="_REPO_DEFAULT_")],
                          [sg.Frame("Export EAD", ead_layout, font=("Roboto", 15), key="_EAD_LAYOUT_", visible=True),
                           sg.Frame("Export MARCXML", marc_layout, font=("Roboto", 15), key="_MARC_LAYOUT_",
                                    visible=False),
                           sg.Frame("Export Container Labels", contlabel_layout, font=("Roboto", 15),
                                    key="_LABEL_LAYOUT_",
                                    visible=False),
                           sg.Frame("Export PDF", pdf_layout, font=("Roboto", 15), key="_PDF_LAYOUT_", visible=False)],
                          [sg.Frame("Upload to XTF", xtf_layout, font=("Roboto", 15), key="_XTF_LAYOUT_",
                                    visible=xtf_version)],
                          [sg.Text("Output Terminal:", font=("Roboto", 12))],
                          [sg.Output(size=(80, 18), key="_output_")]
                          ]
    layout_simple = [[sg.Menu(menu_def)],
                     [sg.Column(simple_layout_col1), sg.Column(simple_layout_col2)]
                     ]
    window_simple = sg.Window("ArchivesSpace Batch Export-Cleanup-Upload Program", layout_simple)
    while True:
        event_simple, values_simple = window_simple.Read()
        if event_simple == 'Cancel' or event_simple is None or event_simple == "Exit":
            window_simple.close()
            break
        # ------------- CHANGE LAYOUTS SECTION -------------
        if event_simple == "_EXPORT_EAD_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=xtf_version)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_MARCXML_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_PDF_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=True)
        if event_simple == "_EXPORT_CONTLABS_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_XTF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
        # ------------- REPOSITORY SECTION -------------
        if event_simple == "_REPO_DEFAULT_":
            with open("defaults.json", "w") as DEFAULT:
                defaults["repo_default"]["_REPO_NAME_"] = values_simple["_REPO_SELECT_"]
                defaults["repo_default"]["_REPO_ID_"] = repositories[values_simple["_REPO_SELECT_"]]
                json.dump(defaults, DEFAULT)
                DEFAULT.close()
        # ------------- EAD SECTION -------------
        if event_simple == "_EXPORT_EAD_":
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        get_eads(input_ids, defaults, cleanup_options, repositories, client, values_simple)
                else:
                    get_eads(input_ids, defaults, cleanup_options, repositories, client, values_simple)
        if event_simple == "_EAD_OPTIONS_" or event_simple == "Change EAD Export Options":
            get_ead_options(defaults)
        if event_simple == "Change EAD Cleanup Defaults" or event_simple == "Change Cleanup Defaults":
            cleanup_options = get_cleanup_defaults(cleanup_defaults, defaults)
        if event_simple == "_OPEN_CLEAN_B_" or event_simple == 'Open Cleaned EAD Folder':
            if not defaults["ead_export_default"]["_OUTPUT_DIR_"]:
                filepath_eads = str(Path.cwd().joinpath("clean_eads"))
                open_file(filepath_eads)
            else:
                filepath_eads = str(Path(defaults["ead_export_default"]["_OUTPUT_DIR_"]))
                open_file(filepath_eads)
        if event_simple == "_OPEN_RAW_EXPORTS_" or event_simple == "Open RAW ASpace Exports":
            if not defaults["ead_export_default"]["_SOURCE_DIR_"]:
                filepath_eads = str(Path.cwd().joinpath("source_eads"))
                open_file(filepath_eads)
            else:
                filepath_eads = str(Path(defaults["ead_export_default"]["_SOURCE_DIR_"]))
                open_file(filepath_eads)
        # ------------- MARCXML SECTION -------------
        if event_simple == "_EXPORT_MARCXML_":
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        get_marcxml(input_ids, defaults, repositories, client, values_simple)
                else:
                    get_marcxml(input_ids, defaults, repositories, client, values_simple)
        if event_simple == "_OPEN_MARC_DEST_":
            if not defaults["marc_export_default"]["_OUTPUT_DIR_"]:
                filepath_marcs = str(Path.cwd().joinpath("source_marcs"))
                open_file(
                    filepath_marcs)
            else:
                filepath_marcs = str(Path(defaults["marc_export_default"]["_OUTPUT_DIR_"]))
                open_file(
                    filepath_marcs)
        if event_simple == "_MARCXML_OPTIONS_" or event_simple == "Change MARCXML Export Options":
            get_marc_options(defaults)
        # ------------- PDF SECTION -------------
        if event_simple == "_EXPORT_PDF_":
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        get_pdfs(input_ids, defaults, repositories, client, values_simple)
                else:
                    get_pdfs(input_ids, defaults, repositories, client, values_simple)
        if event_simple == "_OPEN_PDF_DEST_":
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
            input_ids = values_simple["resource_id_input"]
            if not values_simple["_REPO_SELECT_"]:
                sg.Popup("WARNING!\nPlease select a repository")
            else:
                if values_simple["_REPO_SELECT_"] == "Search Across Repositories (Sys Admin Only)":
                    sysadmin_popup = sg.PopupYesNo("WARNING!\nAre you an ArchivesSpace System Admin?\n")
                    if sysadmin_popup == "Yes":
                        get_contlabels(input_ids, defaults, repositories, client, values_simple)
                else:
                    get_contlabels(input_ids, defaults, repositories, client, values_simple)
        if event_simple == "_OUTPUT_DIR_LABEL_INPUT_":
            if os.path.isdir(values_simple["_OUTPUT_DIR_LABEL_INPUT_"]) is False:
                sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
            else:
                with open("defaults.json", "w") as defaults_labels:
                    defaults["labels_export_default"] = values_simple["_OUTPUT_DIR_LABEL_INPUT_"]
                    json.dump(defaults, defaults_labels)
                    defaults_labels.close()
        if event_simple == "_OPEN_LABEL_DEST_":
            if not defaults["labels_export_default"]:
                filepath_labels = str(Path.cwd().joinpath("source_labels"))
                open_file(filepath_labels)
            else:
                filepath_labels = str(Path(defaults["labels_export_default"]))
                open_file(filepath_labels)
        if event_simple == "_CONTOPT_HELP_":
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#container-labels-screen",
                            new=2)
        # ------------- MENU OPTIONS SECTION -------------
        # ------------------- FILE -------------------
        if event_simple == "Clear Cleaned EAD Folder":
            path = os.listdir("clean_eads/")
            try:
                file_count = 0
                for file in path:
                    file_count += 1
                    full_path = str(Path.joinpath(defaults["ead_export_default"]["_OUTPUT_DIR_"], file))
                    os.remove(full_path)
                print("Deleted {} files in clean_eads".format(str(file_count)))
            except Exception as e:
                print("No files in clean_eads folder\n" + str(e))
        if event_simple == "Clear Raw ASpace Export Folder":
            path = os.listdir("source_eads/")
            try:
                file_count = 0
                for file in path:
                    file_count += 1
                    full_path = str(Path.joinpath(defaults["ead_export_default"]["_SOURCE_DIR_"], file))
                    os.remove(full_path)
                print("Deleted {} files in source_eads".format(str(file_count)))
            except Exception as e:
                print("No files in source_eads folder\n" + str(e))
        if event_simple == "Reset Defaults":
            reset_defaults = sg.PopupYesNo("You are about to reset your configurations.\n"
                                           "Are you sure?")
            if reset_defaults == "Yes":
                setup.reset_defaults()
        # ------------------- EDIT -------------------
        if event_simple == "Change ASpace Login Credentials":
            as_username, as_password, as_api, close_program_as, client, version, repositories, xtf_version = \
                get_aspace_log(defaults, xtf_checkbox=False)
        if event_simple == 'Change XTF Login Credentials':
            xtf_username, xtf_password, xtf_hostname, xtf_remote_path, xtf_indexer_path, close_program_xtf = \
                get_xtf_log(defaults, login=False)
        # ------------------- HELP -------------------
        if event_simple == "About":
            window_about_active = True
            # TODO Change Version #
            layout_about = [
                [sg.Text("Created by Corey Schmidt for the University of Georgia Libraries\n\n"
                         "Version: 0.6.2\n\n"
                         "To check for the latest versions, check the Github\n", font=("Roboto", 12))],
                [sg.OK(bind_return_key=True, key="_ABOUT_OK_"), sg.Button("Check Github", key="_CHECK_GITHUB_")]
            ]
            window_about = sg.Window("About this program", layout_about)
            while window_about_active is True:
                event_about, values_about = window_about.Read()
                if event_about is None:
                    window_about.close()
                    window_about_active = False
                if event_about == "_CHECK_GITHUB_":
                    webbrowser.open("https://github.com/uga-libraries/AS_XTF-DEV/releases", new=2)
                if event_about == "_ABOUT_OK_":
                    window_about.close()
                    window_about_active = False
        if event_simple == "User Manual":
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual",
                            new=2)
        # ------------- UPLOAD TO XTF SECTION -------------
        if event_simple == "_UPLOAD_":
            window_upl_active = True
            files_list = [ead_file for ead_file in os.listdir(defaults["xtf_default"]["xtf_local_path"])
                          if Path(ead_file).suffix == ".xml" or Path(ead_file).suffix == ".pdf"]
            upload_options_layout = [[sg.Button("Upload to XTF", key="_UPLOAD_TO_XTF_"),
                                      sg.Text("* The program may be unresponsive, please wait.")],
                                     [sg.Text("Options", font=("Roboto", 12))],
                                     [sg.Button("XTF Options", key="_XTF_OPTIONS_2_")]
                                     ]
            xtf_upload_layout = [[sg.Text("Files to Upload:", font=("Roboto", 14))],
                                 [sg.Listbox(files_list, size=(50, 20), select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                                             key="_SELECT_FILES_")],
                                 [sg.Frame("XTF Upload", upload_options_layout, font=("Roboto", 14))]]
            window_upl = sg.Window("Upload Files to XTF", xtf_upload_layout)
            while window_upl_active is True:
                event_upl, values_upl = window_upl.Read()
                if event_upl is None:
                    window_upl.close()
                    window_upl_active = False
                if event_upl == "_XTF_OPTIONS_2_":
                    get_xtf_options(defaults)
                if event_upl == "_UPLOAD_TO_XTF_":
                    remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path)
                    xtf_files = fetch_local_files(defaults["xtf_default"]["xtf_local_path"],
                                                  values_upl["_SELECT_FILES_"])
                    upload_output = remote.bulk_upload(xtf_files)
                    print(upload_output)
                    if defaults["xtf_default"]["_REINDEX_AUTO_"] is True:
                        cmds_output = remote.execute_commands(
                            ['{} -index default'.format(defaults["xtf_default"]["xtf_indexer_path"])])
                        print("-" * 135)
                        print(cmds_output)
                    else:
                        print("-" * 135)
                    remote.disconnect()
                    # xtfup_id = files
                    # thread_id = threading.Thread(target=xtf_upload_wrapper,
                    #                              args=(xtfup_id, gui_queue, remote, files,
                    #                                    xtf_hostname),
                    #                              daemon=True)
                    # thread_id.start()
                    # try:
                    #     message = gui_queue.get_nowait()
                    # except queue.Empty:
                    #     message = None
                    # if message:
                    #     print(" Done")
                    #     print(message)
                    window_upl.close()
                    window_upl_active = False
        if event_simple == "_INDEX_":
            print("Beginning Re-Index, this may take awhile...\nThe program might become unresponsive.")
            remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path)
            cmds_output = remote.execute_commands(
                ['{} -index default'.format(defaults["xtf_default"]["xtf_indexer_path"])])
            print(cmds_output)
            print("-" * 135)
            remote.disconnect()
        if event_simple == "_XTF_OPTIONS_" or event_simple == "Change XTF Options":
            get_xtf_options(defaults)
    window_simple.close()


def get_aspace_log(defaults, xtf_checkbox=True):
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

    Returns:
        as_username (str): user's ArchivesSpace username
        as_password (str): user's ArchivesSpace password
        as_api (str): the ArchivesSpace API URL
        close_program (bool): if a user exits the popup, this will return true and end run_gui()
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        version (str): the current version of ArchivesSpace
        repositories (dict): contains info on all the repositories for an ArchivesSpace instance, including name as the
        key and id # as it's value
        xtf_version (bool): user indicated value whether they want to display xtf features in the GUI
    """
    as_username = None
    as_password = None
    as_api = None
    client = None
    asp_version = None
    repositories = {"Search Across Repositories (Sys Admin Only)": None}
    xtf_version = True
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
                as_username = values_log["_ASPACE_UNAME_"]
                as_password = values_log["_ASPACE_PWORD_"]
                as_api = values_log["_ASPACE_API_"]
                xtf_version = values_log["_USE_XTF_"]
                try:
                    client = ASnakeClient(baseurl=as_api, username=as_username, password=as_password)
                    client.authorize()
                    window_asplog_active = False
                    correct_creds = True
                except Exception as e:
                    error_message = ""
                    if ":" in str(e):
                        error_divided = str(e).split(":")
                        for line in error_divided:
                            error_message += line + "\n"
                    else:
                        error_message = str(e)
                    sg.Popup("Your username and/or password were entered incorrectly. Please try again.\n\n" +
                             error_message)
                asp_version = client.get("/version").content.decode().split(" ")[1]
                with open("defaults.json",
                          "w") as defaults_asp:  # If connection is successful, save the ASpace API in defaults.json
                    defaults["as_api"] = as_api
                    defaults["xtf_default"]["xtf_version"] = xtf_version
                    json.dump(defaults, defaults_asp)
                    defaults_asp.close()
                repo_results = client.get('/repositories')
                repo_results_dec = json.loads(repo_results.content.decode())
                for result in repo_results_dec:
                    repositories[result["name"]] = result["uri"][-1]
            if event_log is None or event_log == 'Cancel':
                window_login.close()
                window_asplog_active = False
                correct_creds = True
                close_program = True
                break
        window_login.close()
    return as_username, as_password, as_api, close_program, client, asp_version, repositories, xtf_version


def get_xtf_log(defaults, login=True):
    """
    Gets a user's XTF credentials.

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_xtf_log

    Args:
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        login (bool): determines whether window is on initial popup or within program, changes lang. of save button

    Returns:
        xtf_username (str): user's XTF username
        xtf_password (str): user's XTF password
        xtf_host (str): the host URL for the XTF instance.
        xtf_remote_path (str): the path (folder) where a user wants their data to be stored on the XTF host
        xtf_indexer_path (str): the path (file) where the website indexer is located
        close_program (bool): if a user exits the popup, this will return true and end run_gui()
    """
    xtf_username = None
    xtf_password = None
    xtf_host = None
    xtf_remote_path = None
    xtf_indexer_path = None
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
                       [sg.Text("XTF Indexer Path:", font=("Roboto", 11))]]
        xtflog_col2 = [[sg.InputText(focus=True, key="_XTF_UNAME_")],
                       [sg.InputText(password_char='*', key="_XTF_PWORD_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_host"], key="_XTF_HOSTNAME_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_remote_path"], key="_XTF_REMPATH_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_indexer_path"], key="_XTF_INDPATH_")]]
        layout_xtflog = [
            [sg.Column(xtflog_col1), sg.Column(xtflog_col2)],
            [sg.Button(save_button_xtf, bind_return_key=True, key="_SAVE_CLOSE_LOGIN_")]
        ]
        window_xtfcred = sg.Window("XTF Login Credentials", layout_xtflog)
        while window_xtflog_active is True:
            event_xlog, values_xlog = window_xtfcred.Read()
            if event_xlog == "_SAVE_CLOSE_LOGIN_":
                xtf_username = values_xlog["_XTF_UNAME_"]
                xtf_password = values_xlog["_XTF_PWORD_"]
                xtf_host = values_xlog["_XTF_HOSTNAME_"]
                xtf_remote_path = values_xlog["_XTF_REMPATH_"]
                xtf_indexer_path = values_xlog["_XTF_INDPATH_"]
                try:
                    remote = xup.RemoteClient(xtf_host, xtf_username, xtf_password, xtf_remote_path)
                    remote.client = remote.connect_remote()
                    if remote.scp is None:
                        raise Exception
                    else:
                        with open("defaults.json",
                                  "w") as defaults_xtf:
                            defaults["xtf_default"]["xtf_host"] = values_xlog["_XTF_HOSTNAME_"]
                            defaults["xtf_default"]["xtf_remote_path"] = values_xlog["_XTF_REMPATH_"]
                            defaults["xtf_default"]["xtf_indexer_path"] = values_xlog["_XTF_INDPATH_"]
                            json.dump(defaults, defaults_xtf)
                            defaults_xtf.close()
                        window_xtflog_active = False
                        correct_creds = True
                        break
                except Exception as e:
                    sg.Popup("Your username and/or password were entered incorrectly. Please try again.\n\n" + str(e))
                    window_xtflog_active = True
            if event_xlog is None or event_xlog == 'Cancel':
                window_xtfcred.close()
                window_xtflog_active = False
                correct_creds = True
                close_program = True
                break
        window_xtfcred.close()
    return xtf_username, xtf_password, xtf_host, xtf_remote_path, xtf_indexer_path, close_program


def get_eads(input_ids, defaults, cleanup_options, repositories, client, values_simple):
    """
    Iterates through the user input and sends them to as_export.py to fetch_results() and export_ead().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_eads

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        cleanup_options (list): options a user wants to run against an EAD.xml file after export to clean the file.
        These include the following:
            "_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_", "_DEL_CONTAIN_",
            "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_", "_DEL_ALLNS_"
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict): values as entered with the run_gui() function. See PySimpleGUI documentation for more info

    Returns:
        None
    """

    if "," in input_ids:
        resources = [user_input.strip() for user_input in input_ids.split(",")]
    else:
        resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        resource_export = asx.ASExport(input_id, repositories[values_simple["_REPO_SELECT_"]], client,
                                       defaults["ead_export_default"]["_SOURCE_DIR_"])
        resource_export.fetch_results()
        if resource_export.error is None:
            if resource_export.result is not None:
                print(resource_export.result)
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_ead(include_unpublished=defaults["ead_export_default"]["_INCLUDE_UNPUB_"],
                                       include_daos=defaults["ead_export_default"]["_INCLUDE_DAOS_"],
                                       numbered_cs=defaults["ead_export_default"]["_NUMBERED_CS_"],
                                       ead3=defaults["ead_export_default"]["_USE_EAD3_"])
            if resource_export.error is None:
                print(resource_export.result + "\n")
                if defaults["ead_export_default"]["_CLEAN_EADS_"] is True:
                    if defaults["ead_export_default"]["_KEEP_RAW_"] is True:
                        print("Cleaning up EAD record...", end='', flush=True)
                        valid, results = clean.cleanup_eads(resource_export.filepath, cleanup_options,
                                                            defaults["ead_export_default"]["_OUTPUT_DIR_"],
                                                            keep_raw_exports=True)
                        if valid:
                            print("Done")
                            print(results)
                        else:
                            print("XML validation error\n" + results)
                    else:
                        print("Cleaning up EAD record...", end='', flush=True)
                        valid, results = clean.cleanup_eads(resource_export.filepath, cleanup_options,
                                                            defaults["ead_export_default"]["_OUTPUT_DIR_"])
                        if valid:
                            print("Done")
                            print(results)
                        else:
                            print("XML validation error\n" + results)
            else:
                print(resource_export.error + "\n")
        else:
            print(resource_export.error + "\n")
    print("\n---------Finished {} exports---------\n".format(str(len(resources))))
    # asx_id = input_id
    # try:
    #     thread_export = threading.Thread(target=as_export_wrapper, args=(input_id, resource_repo,
    #                                                                      resource_uri, as_username,
    #                                                                      as_password, as_api,
    #                                                                      defaults["ead_export_default"][
    #                                                                          "_INCLUDE_UNPUB_"],
    #                                                                      defaults["ead_export_default"][
    #                                                                          "_INCLUDE_DAOS_"],
    #                                                                      defaults["ead_export_default"][
    #                                                                          "_NUMBERED_CS_"],
    #                                                                      defaults["ead_export_default"][
    #                                                                          "_USE_EAD3_"]))
    #     thread_export.start()
    #     # if thread_export[0] is not None:
    #     #     print(thread_export[1])
    #     # else:
    #     #     print(thread_export[1])
    # except:
    #     print("Exception occurred blah blah")
    #     # progress_bar.UpdateBar(i + 1)
    # if thread_export:
    #     sg.popup_animated(sg.DEFAULT_BASE64_LOADING_GIF, time_between_frames=1)
    #     if not thread_export.is_alive():  # the thread finished
    #         sg.popup_animated(None)
    #         thread_export = None
    #         if defaults["ead_export_default"]["_CLEAN_EADS_"] is True:
    #             if values_simple["_KEEP_RAW_"] is True:
    #                 if cleanup_options:  # if cleanup_options is not empty
    #                     path = clean.cleanup_eads(custom_clean=cleanup_defaults, keep_raw_exports=True)
    #                     cwd = os.getcwd()
    #                     raw_path = cwd + path
    #                     subprocess.Popen('explorer "{}"'.format(raw_path))
    #                 else:  # if cleanup_options is empty
    #                     path = clean.cleanup_eads(custom_clean=cleanup_defaults, keep_raw_exports=True)
    #                     cwd = os.getcwd()
    #                     raw_path = cwd + path
    #                     subprocess.Popen('explorer "{}"'.format(raw_path))
    #             else:
    #                 if cleanup_options:  # if cleanup_options is not empty
    #                     clean.cleanup_eads(custom_clean=cleanup_options)
    #                 else:  # if cleanup_options is empty
    #                     clean.cleanup_eads(custom_clean=cleanup_defaults)


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
                         [sg.FolderBrowse("Set raw ASpace output folder:",
                                          initial_folder=defaults["ead_export_default"]["_SOURCE_DIR_"]),
                          sg.InputText(default_text=defaults["ead_export_default"]["_SOURCE_DIR_"],
                                       key="_SOURCE_DIR_")],
                         [sg.Checkbox("Clean EAD records on export", key="_CLEAN_EADS_",
                                      default=defaults["ead_export_default"]["_CLEAN_EADS_"])],
                         [sg.FolderBrowse("Set clean ASpace output folder:",
                                          initial_folder=defaults["ead_export_default"]["_OUTPUT_DIR_"]),
                          sg.InputText(default_text=defaults["ead_export_default"]["_OUTPUT_DIR_"],
                                       key="_OUTPUT_DIR_")],
                         [sg.Button("Save Settings", key="_SAVE_SETTINGS_EAD_", bind_return_key=True)]]
        eadopt_window = sg.Window("EAD Options", eadopt_layout)
        while window_eadopt_active is True:
            event_eadopt, values_eadopt = eadopt_window.Read()
            if event_eadopt is None or event_eadopt == 'Cancel':
                window_eadopt_active = False
                correct_opts = True
                eadopt_window.close()
            if event_eadopt == "_EADOPT_HELP_":
                webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#ead-export-options",
                                new=2)
            if event_eadopt == "_SAVE_SETTINGS_EAD_":
                if values_eadopt["_KEEP_RAW_"] is False and values_eadopt["_CLEAN_EADS_"] is False:
                    sg.Popup("WARNING!\nOne of the checkboxes from the following need to be checked:"
                             "\n\nKeep raw ASpace Exports\nClean EAD records on export")
                else:
                    if os.path.isdir(values_eadopt["_SOURCE_DIR_"]) is False:
                        sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
                    elif os.path.isdir(values_eadopt["_OUTPUT_DIR_"]) is False:
                        sg.popup("WARNING!\nYour input for the cleanup output is invalid."
                                 "\nPlease try another directory")
                    else:
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
            "_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_", "_DEL_CONTAIN_",
            "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_", "_DEL_ALLNS_"
    """
    cleanup_options = []
    window_adv_active = True
    winadv_col1 = [[sg.Checkbox("Add Resource ID as EADID", key="_ADD_EADID_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_EADID_"])],
                   [sg.Checkbox("Delete Empty Notes", key="_DEL_NOTES_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_NOTES_"])],
                   [sg.Checkbox("Remove Non-Alphanumerics and Empty Extents", key="_CLN_EXTENTS_",
                                default=defaults["ead_cleanup_defaults"]["_CLN_EXTENTS_"])],
                   [sg.Checkbox("Add Certainty Attribute", key="_ADD_CERTAIN_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_CERTAIN_"])]]
    winadv_col2 = [[sg.Checkbox("Add label='Mixed Materials' to containers without label", key="_ADD_LABEL_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_LABEL_"])],
                   [sg.Checkbox("Delete Empty Containers", key="_DEL_CONTAIN_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_CONTAIN_"])],
                   [sg.Checkbox("Add Barcode as physloc Tag", key="_ADD_PHYSLOC_",
                                default=defaults["ead_cleanup_defaults"]["_ADD_PHYSLOC_"])],
                   [sg.Checkbox("Remove Archivists' Toolkit IDs", key="_DEL_ATIDS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_ATIDS_"])]]
    winadv_col3 = [[sg.Checkbox("Remove xlink Prefixes from Digital Objects", key="_CNT_XLINKS_",
                                default=defaults["ead_cleanup_defaults"]["_CNT_XLINKS_"])],
                   [sg.Checkbox("Remove Unused Namespaces", key="_DEL_NMSPCS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_NMSPCS_"])],
                   [sg.Checkbox("Remove All Namespaces", key="_DEL_ALLNS_",
                                default=defaults["ead_cleanup_defaults"]["_DEL_ALLNS_"])]]
    layout_adv = [
        [sg.Text("Advanced Options for Cleaning EAD Records", font=("Roboto", 14)),
         sg.Text("Help", font=("Roboto", 11), text_color="blue", enable_events=True, key="_CLEANUP_HELP_")],
        [sg.Column(winadv_col1), sg.Column(winadv_col2), sg.Column(winadv_col3)],
        [sg.Button("Save Settings", key="_SAVE_CLEAN_DEF_", bind_return_key=True)]
    ]
    window_adv = sg.Window("Change Cleanup Defaults", layout_adv)
    while window_adv_active is True:
        event_adv, values_adv = window_adv.Read()
        if event_adv == "_SAVE_CLEAN_DEF_":
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
                defaults["ead_cleanup_defaults"]["_DEL_CONTAIN_"] = values_adv["_DEL_CONTAIN_"]
                defaults["ead_cleanup_defaults"]["_ADD_PHYSLOC_"] = values_adv["_ADD_PHYSLOC_"]
                defaults["ead_cleanup_defaults"]["_DEL_ATIDS_"] = values_adv["_DEL_ATIDS_"]
                defaults["ead_cleanup_defaults"]["_CNT_XLINKS_"] = values_adv["_CNT_XLINKS_"]
                defaults["ead_cleanup_defaults"]["_DEL_NMSPCS_"] = values_adv["_DEL_NMSPCS_"]
                defaults["ead_cleanup_defaults"]["_DEL_ALLNS_"] = values_adv["_DEL_ALLNS_"]
                json.dump(defaults, defaults_cleanup)
                defaults_cleanup.close()
            # window_adv_active = False
            window_adv.close()
            return cleanup_options
        if event_adv == "_CLEANUP_HELP_":
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#cleanup-options",
                            new=2)
        if event_adv is None:
            # window_adv_active = False
            cleanup_options = [option for option, bool_val in defaults["ead_cleanup_defaults"].items() if
                               bool_val is True]
            window_adv.close()
            return cleanup_options


def get_marcxml(input_ids, defaults, repositories, client, values_simple):
    """
    Iterates through user input and sends them to as_export.py to fetch_results() and export_marcxml().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_marcxml

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict): values as entered with the run_gui() function. See PySimpleGUI documentation for more info

    Returns:
        None
    """
    if "," in input_ids:
        resources = [user_input.strip() for user_input in input_ids.split(",")]
    else:
        resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        resource_export = asx.ASExport(input_id, repositories[values_simple["_REPO_SELECT_"]], client,
                                       output_dir=defaults["marc_export_default"]["_OUTPUT_DIR_"])
        resource_export.fetch_results()
        if resource_export.error is None:
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_marcxml(
                include_unpublished=defaults["marc_export_default"]["_INCLUDE_UNPUB_"])
            if resource_export.error is None:
                print(resource_export.result + "\n")
            else:
                print(resource_export.error + "\n")
        else:
            print(resource_export.error)


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
                   [sg.FolderBrowse("Set output folder:",
                                    initial_folder=defaults["marc_export_default"]["_OUTPUT_DIR_"]),
                    sg.InputText(default_text=defaults["marc_export_default"]["_OUTPUT_DIR_"], key="_MARC_OUT_DIR_")],
                   [sg.Button("Save Settings", key="_SAVE_SETTINGS_MARC_", bind_return_key=True)]
                   ]
    window_marc = sg.Window("MARCXML Export Options", marc_layout)
    while window_marc_active is True:
        event_marc, values_marc = window_marc.Read()
        if event_marc is None or event_marc == 'Cancel':
            window_marc_active = False
            window_marc.close()
        if event_marc == "_MARCOPT_HELP_":
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#marcxml-screen",
                            new=2)
        if event_marc == "_SAVE_SETTINGS_MARC_":
            if os.path.isdir(values_marc["_MARC_OUT_DIR_"]) is False:
                sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
            else:
                with open("defaults.json", "w") as defaults_marc:
                    defaults["marc_export_default"]["_INCLUDE_UNPUB_"] = values_marc["_INCLUDE_UNPUB_"]
                    defaults["marc_export_default"]["_KEEP_RAW_"] = values_marc["_KEEP_RAW_"]
                    defaults["marc_export_default"]["_OUTPUT_DIR_"] = str(Path(values_marc["_MARC_OUT_DIR_"]))
                    json.dump(defaults, defaults_marc)
                    defaults_marc.close()
                window_marc_active = False
        window_marc.close()


def get_pdfs(input_ids, defaults, repositories, client, values_simple):
    """
    Iterates through the user input and sends them to as_export.py to fetch_results() and export_pdf().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_pdfs

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict): values as entered with the run_gui() function. See PySimpleGUI documentation for more info

    Returns:
        None
    """
    if "," in input_ids:
        resources = [user_input.strip() for user_input in input_ids.split(",")]
    else:
        resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        resource_export = asx.ASExport(input_id, repositories[values_simple["_REPO_SELECT_"]], client,
                                       output_dir=defaults["pdf_export_default"]["_OUTPUT_DIR_"])
        resource_export.fetch_results()
        if resource_export.error is None:
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_pdf(include_unpublished=defaults["ead_export_default"]["_INCLUDE_UNPUB_"],
                                       include_daos=defaults["pdf_export_default"]["_INCLUDE_DAOS_"],
                                       numbered_cs=defaults["pdf_export_default"]["_NUMBERED_CS_"],
                                       ead3=defaults["pdf_export_default"]["_USE_EAD3_"])
            if resource_export.error is None:
                print(resource_export.result + "\n")
            else:
                print(resource_export.error + "\n")
        else:
            print(resource_export.error)


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
                  [sg.FolderBrowse("Set output folder:",
                                   initial_folder=defaults["pdf_export_default"]["_OUTPUT_DIR_"]),
                   sg.InputText(default_text=defaults["pdf_export_default"]["_OUTPUT_DIR_"], key="_OUTPUT_DIR_")],
                  [sg.Button("Save Settings", key="_SAVE_SETTINGS_PDF_", bind_return_key=True)]
                  ]
    window_pdf = sg.Window("PDF Export Options", pdf_layout)
    while window_pdf_active is True:
        event_pdf, values_pdf = window_pdf.Read()
        if event_pdf is None or event_pdf == 'Cancel':
            window_pdf_active = False
            window_pdf.close()
        if event_pdf == "_PDFOPT_HELP_":
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#pdf-export-options",
                            new=2)
        if event_pdf == "_SAVE_SETTINGS_PDF_":
            if os.path.isdir(values_pdf["_OUTPUT_DIR_"]) is False:
                sg.popup("WARNING!\nYour input for the export output is invalid.\nPlease try another directory")
            else:
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


def get_contlabels(input_ids, defaults, repositories, client, values_simple):
    """
    Iterates through the user input and sends them to as_export.py to fetch_results() and export_labels().

    For an in-depth review on how this code is structured, see the wiki:
    https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#get_contlabels

    Args:
        input_ids (str): user inputs as gathered from the Resource Identifiers input box
        defaults (dict): contains the data from defaults.json file, all data the user has specified as default
        repositories (dict): repositories as listed in the ArchivesSpace instance
        client (ASnake.client object): the ArchivesSpace ASnake client for accessing and connecting to the API
        values_simple (dict): values as entered with the run_gui() function. See PySimpleGUI documentation for more info

    Returns:
        None
    """
    if "," in input_ids:
        resources = [user_input.strip() for user_input in input_ids.split(",")]
    else:
        resources = [user_input.strip() for user_input in input_ids.splitlines()]
    for input_id in resources:
        resource_export = asx.ASExport(input_id, repositories[values_simple["_REPO_SELECT_"]], client,
                                       output_dir=defaults["labels_export_default"])
        resource_export.fetch_results()
        if resource_export.error is None:
            print("Exporting {}...".format(input_id), end='', flush=True)
            resource_export.export_labels()
            if resource_export.error is None:
                print(resource_export.result + "\n")
            else:
                print(resource_export.error + "\n")
        else:
            print(resource_export.error)


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
                         [sg.Checkbox("Re-index changed records upon upload", key="_REINDEX_AUTO_",
                                      default=defaults["xtf_default"]["_REINDEX_AUTO_"])],
                         [sg.FolderBrowse(button_text="Select source folder:",
                                          initial_folder=defaults["xtf_default"]["xtf_local_path"]),
                          sg.InputText(default_text=defaults["xtf_default"]["xtf_local_path"], key="_XTF_SOURCE_")],
                         [sg.Button("Change XTF Login Credentials", key="_XTFOPT_CREDS_")],
                         [sg.Button("Save Settings", key="_SAVE_SETTINGS_XTF_", bind_return_key=True)]
                         ]
    window_xtf_option = sg.Window("XTF Options", xtf_option_layout)
    while xtf_option_active is True:
        event_xtfopt, values_xtfopt = window_xtf_option.Read()
        if event_xtfopt is None or event_xtfopt == 'Cancel':
            xtf_option_active = False
            window_xtf_option.close()
        if event_xtfopt == "_XTFOPT_HELP_":
            webbrowser.open("https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual#xtf-frame",
                            new=2)
        if event_xtfopt == "_XTFOPT_CREDS_":
            get_xtf_log(defaults)
        if event_xtfopt == "_SAVE_SETTINGS_XTF_":
            if os.path.isdir(values_xtfopt["_XTF_SOURCE_"]) is False:
                sg.popup("WARNING!\nYour input for the upload folder is invalid.\nPlease try another directory")
            else:
                with open("defaults.json", "w") as defaults_xtf:
                    defaults["xtf_default"]["_REINDEX_AUTO_"] = values_xtfopt["_REINDEX_AUTO_"]
                    defaults["xtf_default"]["xtf_local_path"] = values_xtfopt["_XTF_SOURCE_"]
                    json.dump(defaults, defaults_xtf)
                    defaults_xtf.close()
                xtf_option_active = False
                window_xtf_option.close()


# Add threading to allow loading screen
# def as_export_wrapper(resource_instance, include_unpublished, include_daos, numbered_cs, ead3):
#     # LOCATION 1
#     # this is our "long running function call"
#     resource_instance.export_ead(include_unpublished, include_daos, numbered_cs, ead3)
#     # at the end of the work, before exiting, send a message back to the GUI indicating end
#     # at this point, the thread exits
#     if resource_instance.error is None:
#         return resource_instance.results
#     else:
#         return resource_instance.error
#
#
# def xtf_upload_wrapper(xtfup_id, gui_queue, remote, files, xtf_host):
#     remote.bulk_upload(files)
#     remote.execute_commands(['/dlg/app/apache-tomcat-6.0.14-maint/webapps/hmfa/bin/textIndexer -index default'])
#     remote.disconnect()
#     gui_queue.put('{} ::: done'.format(xtfup_id))
#     return


def open_file(filepath):
    """
    Takes a filepath and opens the folder according to Windows, Mac, or Linux.

    Args:
        filepath (str): the filepath of the folder/directory a user wants to open

    Returns:
        None
    """
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
    local_files = os.walk(local_file_dir)
    for root, dirs, files in local_files:
        return [str(Path(root, file)) for file in files if file in select_files]


def setup_files():
    """
    Checks for directories in the current directory the GUI or .exe is located and tries to open defaults.json

    Returns:
        json_data (dict): contains data from defaults.json for user's default settings
    """
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
            setup.create_default_folders()
    try:
        with open("defaults.json", "r") as DEFAULTS:
            json_data = json.load(DEFAULTS)
            DEFAULTS.close()
    except Exception as defaults_error:
        print(str(defaults_error) + "\nThere was an error reading the defaults.json file. Recreating one now...")
        json_data = setup.set_defaults_file()
        print("Done")
    return json_data


# sg.preview_all_look_and_feel_themes()
if __name__ == "__main__":
    run_gui(setup_files())
