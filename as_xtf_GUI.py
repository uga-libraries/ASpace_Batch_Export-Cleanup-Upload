import os
import subprocess
import sys
import webbrowser
import queue
import threading
import json

import PySimpleGUI as sg
from asnake.client import ASnakeClient

import as_export as asx
import cleanup as clean
import files as fetch_files
import secrets as sec
import xtf_upload as xup
import setup as setup

'''      
     Create a secure login for your scripts without having to include your password    in the program.  Create an SHA1 hash code for your password using the GUI. Paste into variable in final program      
     1. Choose a password      
     2. Generate a hash code for your chosen password by running program and entering 'gui' as the password      
     3. Type password into the GUI      
     4. Copy and paste hash code Window GUI into variable named login_password_hash    
     5. Run program again and test your login!      
'''


# Use this GUI to get your password's hash code
# def hashgeneratorgui():
#     layout = [[sg.T('Password Hash Generator', size=(30, 1), font='Any 15')],
#               [sg.T('Password'), sg.In(key='password')],
#               [sg.T('SHA Hash'), sg.In('', size=(40, 1), key='hash')],
#               ]
#
#     window = sg.Window('SHA Generator', layout, auto_size_text=False, default_element_size=(10, 1),
#                        text_justification='r', return_keyboard_events=True, grab_anywhere=False)
#
#     while True:
#         event, values = window.read()
#         if event is None:
#             exit(69)
#
#         password = values['password']
#         try:
#             password_utf = password.encode('utf-8')
#             sha1hash = hashlib.sha1()
#             sha1hash.update(password_utf)
#             password_hash = sha1hash.hexdigest()
#             window['hash'].update(password_hash)
#         except:
#             pass
#
#         # ----------------------------- Paste this code into your program / script -----------------------------
#
#
# # determine if a password matches the secret password by comparing SHA1 hash codes
# def passwordmatches(password, hash):
#     password_utf = password.encode('utf-8')
#     sha1hash = hashlib.sha1()
#     sha1hash.update(password_utf)
#     password_hash = sha1hash.hexdigest()
#     if password_hash == hash:
#         return True
#     else:
#         return False
#
#
# login_password_hash = '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8'
# username = sg.popup_get_text('ASpace Username')
# password = sg.popup_get_text('ASpace Password', password_char='*')
# if passwordmatches(password, login_password_hash):
#     print('Login SUCCESSFUL')
# else:
#     print('Login FAILED!!')


# Input from GUI
def run_gui(defaults):
    sg.ChangeLookAndFeel('LightBlue2')
    as_username, as_password, as_api, close_program_as = get_aspace_log(defaults)
    if close_program_as is True:
        sys.exit()
    # TODO For XTF Users Only
    xtf_username, xtf_password, xtf_hostname, xtf_remote_path, close_program_xtf = get_xtf_log(defaults)
    if close_program_xtf is True:
        sys.exit()
    cleanup_defaults = ["_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_",
                        "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_",
                        "_DEL_ALLNS_"]
    cleanup_options = [option for option, bool_val in defaults["ead_cleanup_defaults"].items() if bool_val is True]
    thread_export = None
    menu_def = [['File',
                 ['Open Cleaned EAD Folder',
                  'Open Raw ASpace Exports',
                  '---',
                  'Clear Raw ASpace Export Folder',
                  'Clear Cleaned EAD Folder',
                  '---',
                  'Settings',
                  ['Change ASpace Login Credentials',
                   'Change XTF Login Credentials',
                   '---',
                   'Change EAD Cleanup Defaults',
                   'Change EAD Export Options',
                   '---',
                   'Change MARCXML Export Options',
                   '---',
                   'Change PDF Export Options'],
                  'Exit', ]
                 ],
                ['Edit',
                 ['Change ASpace Login Credentials',
                  'Change XTF Login Credentials',
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
    ead_layout = [[sg.Text("Export EAD Records", font=("Roboto", 14))],
                  [sg.Button(button_text="EXPORT", key="_EXPORT_EAD_")],
                  [sg.Text("Options", font=("Roboto", 11))],
                  [sg.Button("EAD Export Options", key="_EAD_OPTIONS_"),
                   sg.Button("Cleanup Options", key="Change Cleanup Defaults")],
                  [sg.Button(button_text="Open Output", key="_OPEN_CLEAN_B_")],
                  [sg.Text("-" * 245)],
                  [sg.Text("Upload to XTF", font=("Roboto", 14))],
                  [sg.Button(button_text="Upload", key="_UPLOAD_")]
                  ]
    marc_layout = [[sg.Text("Export MARCXML Records", font=("Roboto", 14))],
                   [sg.Button(button_text="EXPORT", key="_EXPORT_MARCXML_")],
                   [sg.Text("Options", font=("Roboto", 11))],
                   [sg.Button("MARCXML Export Options", key="_MARCXML_OPTIONS_")],
                   [sg.Button(button_text="Open Output", key="_OPEN_MARC_DEST_")],
                   ]
    contlabel_layout = [[sg.Text("Export Container Labels", font=("Roboto", 14))],
                        [sg.Button(button_text="EXPORT", key="_EXPORT_LABEL_")],
                        [sg.Text("Options", font=("Roboto", 11))],
                        [sg.Button(button_text="Open Output", key="_OPEN_LABEL_DEST_")],
                        [sg.FolderBrowse("Choose Output Folder:", key="_OUTPUT_DIR_LABEL_",
                                         initial_folder=defaults["labels_export_default"]),
                         sg.InputText(defaults["labels_export_default"], key="_OUTPUT_DIR_LABEL_INPUT_",
                                      enable_events=True)]
                        ]
    pdf_layout = [[sg.Text("Export PDFs", font=("Roboto", 14))],
                  [sg.Button(button_text="EXPORT", key="_EXPORT_PDF_")],
                  [sg.Text("Options", font=("Roboto", 11))],
                  [sg.Button("PDF Export Options", key="_PDF_OPTIONS_")],
                  [sg.Button(button_text="Open Output", key="_OPEN_PDF_DEST_")],
                  ]
    layout_simple = [[sg.Menu(menu_def)],
                     [sg.Text("Enter Resource Identifiers here:", font=("Roboto", 12)),
                      sg.Text("           Output Terminal:", font=("Roboto", 12))],
                     [sg.Multiline(key="resource_id_input", size=(35, 30), focus=True),
                      sg.Output(size=(100, 30), key="_output_")],
                     [sg.Text("Choose your export option:")],
                     [sg.Radio("EAD", "RADIO1", key="_EXPORT_EAD_RAD_", default=True, enable_events=True),
                      sg.Radio("MARCXML", "RADIO1", key="_EXPORT_MARCXML_RAD_", enable_events=True),
                      sg.Radio("Container Labels", "RADIO1", key="_EXPORT_CONTLABS_RAD_", enable_events=True),
                      sg.Radio("PDF", "RADIO1", key="_EXPORT_PDF_RAD_", enable_events=True)],
                     [sg.Text("-" * 248)],
                     [sg.Column(ead_layout, key="_EAD_LAYOUT_", visible=True),
                      sg.Column(marc_layout, key="_MARC_LAYOUT_", visible=False),
                      sg.Column(contlabel_layout, key="_LABEL_LAYOUT_", visible=False),
                      sg.Column(pdf_layout, key="_PDF_LAYOUT_", visible=False)],
                     [sg.Text("")]
                     ]
    window_simple = sg.Window("ArchivesSpace EAD Export/Cleanup/Upload Program", layout_simple)
    while True:
        event_simple, values_simple = window_simple.Read()
        if event_simple == 'Cancel' or event_simple is None or event_simple == "Exit":
            window_simple.close()
            break
        # ------------- CHANGE LAYOUTS SECTION -------------
        if event_simple == "_EXPORT_EAD_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_MARCXML_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_PDF_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=True)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=False)
        if event_simple == "_EXPORT_CONTLABS_RAD_":
            window_simple[f'{"_EAD_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_PDF_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_MARC_LAYOUT_"}'].update(visible=False)
            window_simple[f'{"_LABEL_LAYOUT_"}'].update(visible=True)
        # ------------- EAD SECTION -------------
        if event_simple == "_EXPORT_EAD_":
            input_ids = values_simple["resource_id_input"]
            resources = input_ids.splitlines()
            for input_id in resources:
                resource_export = asx.ASExport(input_id, as_username, as_password, as_api)
                resource_export.fetch_results()
                if resource_export.error is None:
                    print("Exporting EAD files...", end='', flush=True)
                    resource_export.export_ead(include_unpublished=defaults["ead_export_default"]["_INCLUDE_UNPUB_"],
                                               include_daos=defaults["ead_export_default"]["_INCLUDE_DAOS_"],
                                               numbered_cs=defaults["ead_export_default"]["_NUMBERED_CS_"],
                                               ead3=defaults["ead_export_default"]["_USE_EAD3_"])
                    if resource_export.error is None:
                        print(resource_export.result)
                        if defaults["ead_export_default"]["_CLEAN_EADS_"] is True:
                            if defaults["ead_export_default"]["_KEEP_RAW_"] is True:
                                filepath, results = clean.cleanup_eads(resource_export.filepath, cleanup_options,
                                                                       keep_raw_exports=True)
                            else:
                                filepath, results = clean.cleanup_eads(resource_export.filepath, cleanup_options)
                            for result in results:
                                print(result)
                    else:
                        print(resource_export.error)
                else:
                    print(resource_export.error)
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
        #         if defaults["ead_export_default"]["_CLEAN_EADS_"] is True: # if user wants EAD files to be run through cleanup.py - as set by the defaults.json
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
        if event_simple == "_EAD_OPTIONS_" or event_simple == "Change EAD Export Options":
            get_ead_options(defaults)
        if event_simple == "_OPEN_CLEAN_B_" or event_simple == 'Open Cleaned EAD Folder':
            if not defaults["ead_export_default"]["_OUTPUT_DIR_"]:
                cwd = os.getcwd()
                filepath_eads = cwd + "\clean_eads"
                subprocess.Popen('explorer "{}"'.format(filepath_eads))
            else:
                subprocess.Popen('explorer "{}"'.format(defaults["ead_export_default"]["_OUTPUT_DIR_"]))
        # ------------- MARCXML SECTION -------------
        if event_simple == "_EXPORT_MARCXML_":
            input_ids = values_simple["resource_id_input"]
            resources = input_ids.splitlines()
            for input_id in resources:
                resource_export = asx.ASExport(input_id, as_username, as_password, as_api)
                resource_export.fetch_results()
                if resource_export.error is None:
                    if not defaults["marc_export_default"]["_OUTPUT_DIR_"]:
                        output_dir_marc = os.getcwd() + "\\source_marcs"
                    else:
                        output_dir_marc = defaults["marc_export_default"]["_OUTPUT_DIR_"]
                    print("Exporting MARCXML files...", end='', flush=True)
                    resource_export.export_marcxml(output_dir=output_dir_marc,
                                                   include_unpublished=defaults["marc_export_default"]["_INCLUDE_UNPUB_"])
                    if resource_export.error is None:
                        print(resource_export.result)
                    else:
                        print(resource_export.error)
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
                else:
                    print(resource_export.error)
        if event_simple == "_OPEN_MARC_DEST_":
            if not defaults["marc_export_default"]["_OUTPUT_DIR_"]:
                filepath_marcs = os.getcwd() + "\\source_marcs"
                subprocess.Popen('explorer "{}"'.format(filepath_marcs))
            else:
                subprocess.Popen('explorer "{}"'.format(defaults["marc_export_default"]["_OUTPUT_DIR_"]))
        if event_simple == "_MARCXML_OPTIONS_" or event_simple == "Change MARCXML Export Options":
            get_marc_options(defaults)
        # ------------- PDF SECTION -------------
        if event_simple == "_EXPORT_PDF_":
            input_ids = values_simple["resource_id_input"]
            resources = input_ids.splitlines()
            for input_id in resources:
                resource_export = asx.ASExport(input_id, as_username, as_password, as_api)
                resource_export.fetch_results()
                if resource_export.error is None:
                    if not defaults["pdf_export_default"]["_OUTPUT_DIR_"]:
                        output_dir_pdf = os.getcwd() + "\\source_pdfs"
                    else:
                        output_dir_pdf = defaults["pdf_export_default"]["_OUTPUT_DIR_"]
                    print("Exporting PDF files...", end='', flush=True)
                    resource_export.export_pdf(output_dir=output_dir_pdf,
                                               include_unpublished=defaults["ead_export_default"]["_INCLUDE_UNPUB_"],
                                               include_daos=defaults["pdf_export_default"]["_INCLUDE_DAOS_"],
                                               numbered_cs=defaults["pdf_export_default"]["_NUMBERED_CS_"],
                                               ead3=defaults["pdf_export_default"]["_USE_EAD3_"])
                    if resource_export.error is None:
                        print(resource_export.result)
                    else:
                        print(resource_export.error)
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
                else:
                    print(resource_export.error)
        if event_simple == "_OPEN_PDF_DEST_":
            if not defaults["pdf_export_default"]["_OUTPUT_DIR_"]:
                cwd = os.getcwd()
                filepath_pdfs = cwd + "\source_pdfs"
                subprocess.Popen('explorer "{}"'.format(filepath_pdfs))
            else:
                subprocess.Popen('explorer "{}"'.format(defaults["pdf_export_default"]["_OUTPUT_DIR_"]))
        if event_simple == "_PDF_OPTIONS_" or event_simple == "Change PDF Export Options":
            get_pdf_options(defaults)
        # ------------- CONTAINER LABEL SECTION -------------
        if event_simple == "_EXPORT_LABEL_":
            input_ids = values_simple["resource_id_input"]
            resources = input_ids.splitlines()
            for input_id in resources:
                resource_export = asx.ASExport(input_id, as_username, as_password, as_api)
                resource_export.fetch_results()
                if resource_export.error is None:
                    if not defaults["labels_export_default"]:
                        output_dir_label = os.getcwd() + "\\source_labels"
                    else:
                        output_dir_label = defaults["labels_export_default"]
                    print("Exporting Container Labels files...", end='', flush=True)
                    resource_export.export_labels(output_dir=output_dir_label)
                    if resource_export.error is None:
                        print(resource_export.result)
                    else:
                        print(resource_export.error)
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

                else:
                    print(resource_export.error)
        if event_simple == "_OUTPUT_DIR_LABEL_INPUT_":
            with open("defaults.json", "w") as defaults_labels:
                print(values_simple["_OUTPUT_DIR_LABEL_"])
                defaults["labels_export_default"] = values_simple["_OUTPUT_DIR_LABEL_INPUT_"]
                json.dump(defaults, defaults_labels)
                defaults_labels.close()
        if event_simple == "_OPEN_LABEL_DEST_":
            if not defaults["labels_export_default"]:
                cwd = os.getcwd()
                filepath_labels = cwd + "\source_labels"
                subprocess.Popen('explorer "{}"'.format(filepath_labels))
            else:
                subprocess.Popen('explorer "{}"'.format(defaults["labels_export_default"]))
        # ------------- MENU OPTIONS SECTION -------------
        if event_simple == "Open Raw ASpace Exports":
            cwd = os.getcwd()
            source_path = cwd + "\source_eads"
            subprocess.Popen('explorer "{}"'.format(source_path))
        if event_simple == "Change ASpace Login Credentials":
            as_username, as_password, as_api, close_program_as = get_aspace_log(defaults)
        if event_simple == 'Change XTF Login Credentials':
            xtf_username, xtf_password, xtf_hostname, xtf_remote_path, close_program_xtf = get_xtf_log(defaults)
        if event_simple == "Clear Cleaned EAD Folder":
            path = os.listdir("clean_eads/")
            try:
                file_count = 0
                for file in path:
                    file_count += 1
                    full_path = os.getcwd() + "\\clean_eads\\" + file
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
                    full_path = os.getcwd() + "\\source_eads\\" + file
                    os.remove(full_path)
                print("Deleted {} files in source_eads".format(str(file_count)))
            except Exception as e:
                print("No files in source_eads folder\n" + str(e))
        if event_simple == "Change EAD Cleanup Defaults" or event_simple == "Change Cleanup Defaults":
            cleanup_defaults, cleanup_options = get_cleanup_defaults(cleanup_defaults, defaults)
        if event_simple == "About":
            window_about_active = True
            layout_about = [
                [sg.Text("Created by Corey Schmidt for the University of Georgia Libraries\n\n"
                         "Version: 0.4a1\n\n"
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
        # ------------- UPLOAD TO XTF SECTION -------------
        if event_simple == "_UPLOAD_":
            window_upl_active = True
            files_list = [ead_file for ead_file in os.listdir("clean_eads")]
            layout_upload = [
                [sg.Text("Choose which files you would like uploaded:")],
                [sg.Listbox(files_list, size=(50, 20), select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE,
                            key="_SELECT_FILES_")],
                [sg.Button("Upload to XTF", key="_UPLOAD_TO_XTF_")]
            ]
            window_upl = sg.Window("Upload Files to XTF", layout_upload)
            while window_upl_active is True:
                event_upl, values_upl = window_upl.Read()
                if event_upl == "_UPLOAD_TO_XTF_":
                    remote = xup.RemoteClient(xtf_hostname, xtf_username, xtf_password, xtf_remote_path)
                    files = fetch_files.fetch_local_files(sec.xtf_local_path, values_upl["_SELECT_FILES_"])
                    remote.bulk_upload(files)
                    cmds_output = remote.execute_commands(
                        ['/dlg/app/apache-tomcat-6.0.14-maint/webapps/hmfa/bin/textIndexer -index default'])
                    print("-" * 130)
                    print(cmds_output)
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
                if event_upl is None:
                    window_upl.close()
                    window_upl_active = False
    window_simple.close()


def get_aspace_log(defaults):
    as_username = None
    as_password = None
    as_api = None
    window_asplog_active = True
    correct_creds = False
    close_program = False
    while correct_creds is False:
        asplog_col1 = [[sg.Text("Enter your ArchivesSpace username:", font=("Roboto", 10))],
                       [sg.Text("Enter your ArchivesSpace password:", font=("Roboto", 10))],
                       [sg.Text("Enter your ArchivesSpace API URL:", font=("Roboto", 10))]]
        asplog_col2 = [[sg.InputText(focus=True, key="_ASPACE_UNAME_")],
                       [sg.InputText(password_char='*', key="_ASPACE_PWORD_")],
                       [sg.InputText(defaults["as_api"], key="_ASPACE_API_")]]
        layout_asplog = [
            [sg.Column(asplog_col1, key="_ASPLOG_COL1_", visible=True),
             sg.Column(asplog_col2, key="_ASPLOG_COL2_", visible=True)],
            [sg.Button("Save and Close", bind_return_key=True, key="_SAVE_CLOSE_LOGIN_")]
        ]
        window_login = sg.Window("ArchivesSpace Login Credentials", layout_asplog)
        while window_asplog_active is True:
            event_log, values_log = window_login.Read()
            if event_log == "_SAVE_CLOSE_LOGIN_":
                as_username = values_log["_ASPACE_UNAME_"]
                as_password = values_log["_ASPACE_PWORD_"]
                as_api = values_log["_ASPACE_API_"]
                try:
                    client = ASnakeClient(baseurl=as_api, username=as_username, password=as_password)
                    client.authorize()
                    with open("defaults.json",
                              "w") as DEFAULTS:  # If connection is successful, save the ASpace API in defaults.json
                        defaults["as_api"] = values_log["_ASPACE_API_"]
                        json.dump(defaults, DEFAULTS)
                        DEFAULTS.close()
                    window_asplog_active = False
                    correct_creds = True
                    break
                except Exception as e:
                    sg.Popup("Your username and/or password were entered incorrectly. Please try again.\n\n" + str(e))
            if event_log is None or event_log == 'Cancel':
                window_login.close()
                window_asplog_active = False
                correct_creds = True
                close_program = True
                break
        window_login.close()
    return as_username, as_password, as_api, close_program


def get_xtf_log(defaults):
    xtf_username = None
    xtf_password = None
    xtf_host = None
    xtf_remote_path = None
    window_xtflog_active = True
    correct_creds = False
    close_program = False
    while correct_creds is False:  # while not
        xtflog_col1 = [[sg.Text("Enter your XTF username:", font=("Roboto", 10))],
                       [sg.Text("Enter your XTF password:", font=("Roboto", 10))],
                       [sg.Text("Enter XTF Hostname:", font=("Roboto", 10))],
                       [sg.Text("Enter XTF Remote Path:", font=("Roboto", 10))]]
        xtflog_col2 = [[sg.InputText(focus=True, key="_XTF_UNAME_")],
                       [sg.InputText(password_char='*', key="_XTF_PWORD_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_host"], key="_XTF_HOSTNAME_")],
                       [sg.InputText(defaults["xtf_default"]["xtf_remote_path"], key="_XTF_REMPATH_")]]
        layout_xtflog = [
            [sg.Column(xtflog_col1), sg.Column(xtflog_col2)],
            [sg.Button("Save and Close", bind_return_key=True, key="_SAVE_CLOSE_LOGIN_")]
        ]
        window_xtfcred = sg.Window("XTF Login Credentials", layout_xtflog)
        while window_xtflog_active is True:  # while window_xtflog_active
            event_xlog, values_xlog = window_xtfcred.Read()
            if event_xlog == "_SAVE_CLOSE_LOGIN_":
                xtf_username = values_xlog["_XTF_UNAME_"]
                xtf_password = values_xlog["_XTF_PWORD_"]
                xtf_host = values_xlog["_XTF_HOSTNAME_"]
                xtf_remote_path = values_xlog["_XTF_REMPATH_"]
                try:
                    remote = xup.RemoteClient(xtf_host, xtf_username, xtf_password, xtf_remote_path)
                    remote.client = remote.connect_remote()
                    if remote.scp is None:
                        raise Exception
                    else:
                        with open("defaults.json",
                                  "w") as DEFAULTS:  # If connection is successful, save the ASpace API in defaults.json
                            defaults["xtf_default"]["xtf_host"] = values_xlog["_XTF_HOSTNAME_"]
                            defaults["xtf_default"]["xtf_remote_path"] = values_xlog["_XTF_REMPATH_"]
                            json.dump(defaults, DEFAULTS)
                            DEFAULTS.close()
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
    return xtf_username, xtf_password, xtf_host, xtf_remote_path, close_program


# TODO Add ability for user to specify output folder for RAW ASpace exports and cleaned EAD files
# TODO Add popup that when Keep raw ASpace Exports and Clean EAD records on export are false - give warning to user
def get_ead_options(defaults):
    correct_opts = False
    while correct_opts is False:
        window_eadopt_active = True
        eadopt_layout = [[sg.Text("Choose EAD Export Options", font=("Roboto", 12))],
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
                         [sg.Checkbox("Clean EAD records on export", key="_CLEAN_EADS_",
                                      default=defaults["ead_export_default"]["_CLEAN_EADS_"])],
                         # [sg.FolderBrowse("Set output folder:", key="_OUTPUT_DIR_",
                         #                  initial_folder=defaults["ead_export_default"]["_OUTPUT_DIR_"]),
                         #  sg.InputText(default_text=defaults["ead_export_default"]["_OUTPUT_DIR_"])],
                         [sg.Button("Save Settings", key="_SAVE_SETTINGS_EAD_", bind_return_key=True)]]
        eadopt_window = sg.Window("EAD Options", eadopt_layout)
        while window_eadopt_active is True:
            event_eadopt, values_eadopt = eadopt_window.Read()
            if event_eadopt is None or event_eadopt == 'Cancel':
                window_eadopt_active = False
                correct_opts = True
                eadopt_window.close()
            if event_eadopt == "_SAVE_SETTINGS_EAD_":
                if values_eadopt["_KEEP_RAW_"] is False and values_eadopt["_CLEAN_EADS_"] is False:
                    sg.Popup("WARNING!\nOne of the checkboxes from the following need to be true:"
                             "\n\nKeep raw ASpace Exports\nClean EAD records on export")
                else:
                    with open("defaults.json", "w") as DEFAULT:
                        defaults["ead_export_default"]["_INCLUDE_UNPUB_"] = values_eadopt["_INCLUDE_UNPUB_"]
                        defaults["ead_export_default"]["_INCLUDE_DAOS_"] = values_eadopt["_INCLUDE_DAOS_"]
                        defaults["ead_export_default"]["_NUMBERED_CS_"] = values_eadopt["_NUMBERED_CS_"]
                        defaults["ead_export_default"]["_USE_EAD3_"] = values_eadopt["_USE_EAD3_"]
                        defaults["ead_export_default"]["_KEEP_RAW_"] = values_eadopt["_KEEP_RAW_"]
                        defaults["ead_export_default"]["_CLEAN_EADS_"] = values_eadopt["_CLEAN_EADS_"]
                        # if "/" in values_eadopt["_OUTPUT_DIR_"]:
                        #     defaults["ead_export_default"]["_OUTPUT_DIR_"] = values_eadopt["_OUTPUT_DIR_"].replace("/", "\\")
                        # else:
                        #     defaults["ead_export_default"]["_OUTPUT_DIR_"] = values_eadopt["_OUTPUT_DIR_"]
                        json.dump(defaults, DEFAULT)
                        DEFAULT.close()
                    window_eadopt_active = False
                    correct_opts = True
            eadopt_window.close()


def get_cleanup_defaults(cleanup_defaults, defaults):
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
        [sg.Text("Advanced Options for Cleaning EAD Records", font=("Roboto", 12))],
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
            window_adv_active = False
            window_adv.close()
            print(cleanup_options)
            return cleanup_defaults, cleanup_options
        if event_adv is None:
            window_adv_active = False
            cleanup_options = [option for option, bool_val in defaults["ead_cleanup_defaults"].items() if
                               bool_val is True]
            print(cleanup_options)
            window_adv.close()
            return cleanup_defaults, cleanup_options


def get_marc_options(defaults):
    window_marc_active = True
    marc_layout = [[sg.Text("Choose MARCXML Export Options", font=("Roboto", 12))],
                   [sg.Checkbox("Include unpublished components", key="_INCLUDE_UNPUB_",
                                default=defaults["marc_export_default"]["_INCLUDE_UNPUB_"])],
                   [sg.Checkbox("Open output folder on export", key="_KEEP_RAW_",
                                default=defaults["marc_export_default"]["_KEEP_RAW_"])],
                   [sg.FolderBrowse("Set output folder:", key="_MARC_OUT_DIR_",
                                    initial_folder=defaults["marc_export_default"]["_OUTPUT_DIR_"]),
                    sg.InputText(default_text=defaults["marc_export_default"]["_OUTPUT_DIR_"])],
                   [sg.Button("Save Settings", key="_SAVE_SETTINGS_MARC_", bind_return_key=True)]
                   ]
    window_marc = sg.Window("MARCXML Export Options", marc_layout)
    while window_marc_active is True:
        event_marc, values_marc = window_marc.Read()
        if event_marc is None or event_marc == 'Cancel':
            window_marc_active = False
            window_marc.close()
        if event_marc == "_SAVE_SETTINGS_MARC_":
            with open("defaults.json", "w") as defaults_marc:
                defaults["marc_export_default"]["_INCLUDE_UNPUB_"] = values_marc["_INCLUDE_UNPUB_"]
                defaults["marc_export_default"]["_KEEP_RAW_"] = values_marc["_KEEP_RAW_"]
                defaults["marc_export_default"]["_OUTPUT_DIR_"] = values_marc["_MARC_OUT_DIR_"].replace("/", "\\")
                json.dump(defaults, defaults_marc)
                defaults_marc.close()
            window_marc_active = False
        window_marc.close()


def get_pdf_options(defaults):
    window_pdf_active = True
    pdf_layout = [[sg.Text("PDF Export Options", font=("Roboto", 12))],
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
                  [sg.FolderBrowse("Set output folder:", key="_OUTPUT_DIR_",
                                   initial_folder=defaults["pdf_export_default"]["_OUTPUT_DIR_"]),
                   sg.InputText(default_text=defaults["pdf_export_default"]["_OUTPUT_DIR_"])],
                  [sg.Button("Save Settings", key="_SAVE_SETTINGS_PDF_", bind_return_key=True)]
                  ]
    window_pdf = sg.Window("PDF Export Options", pdf_layout)
    while window_pdf_active is True:
        event_pdf, values_pdf = window_pdf.Read()
        if event_pdf is None or event_pdf == 'Cancel':
            window_pdf_active = False
            window_pdf.close()
        if event_pdf == "_SAVE_SETTINGS_PDF_":
            with open("defaults.json", "w") as defaults_pdf:
                defaults["pdf_export_default"]["_INCLUDE_UNPUB_"] = values_pdf["_INCLUDE_UNPUB_"]
                defaults["pdf_export_default"]["_INCLUDE_DAOS_"] = values_pdf["_INCLUDE_DAOS_"]
                defaults["pdf_export_default"]["_NUMBERED_CS_"] = values_pdf["_NUMBERED_CS_"]
                defaults["pdf_export_default"]["_USE_EAD3_"] = values_pdf["_USE_EAD3_"]
                defaults["pdf_export_default"]["_KEEP_RAW_"] = values_pdf["_KEEP_RAW_"]
                defaults["pdf_export_default"]["_OUTPUT_DIR_"] = values_pdf["_OUTPUT_DIR_"].replace("/", "\\")
                json.dump(defaults, defaults_pdf)
                defaults_pdf.close()
            window_pdf_active = False
        window_pdf.close()


def as_export_wrapper(resource_instance, include_unpublished, include_daos, numbered_cs, ead3):
    # LOCATION 1
    # this is our "long running function call"
    resource_instance.export_ead(include_unpublished, include_daos, numbered_cs, ead3)
    # at the end of the work, before exiting, send a message back to the GUI indicating end
    # at this point, the thread exits
    if resource_instance.error is None:
        return resource_instance.results
    else:
        return resource_instance.error


def xtf_upload_wrapper(xtfup_id, gui_queue, remote, files, xtf_host):
    remote.bulk_upload(files)
    remote.execute_commands(['/dlg/app/apache-tomcat-6.0.14-maint/webapps/hmfa/bin/textIndexer -index default'])
    remote.disconnect()
    gui_queue.put('{} ::: done'.format(xtfup_id))
    return


# sg.preview_all_look_and_feel_themes()
if __name__ == "__main__":
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
        print(str(defaults_error) + "\nThere was an error reading the defaults.json file. Recreating one now...",
              end='', flush=True)
        # TODO For non-XTF users, use this code:
        # json_data = setup.set_default_file()
        # TODO For XTF users, use this code:
        json_data = setup.set_default_file_xtf()
        print("Done")
    run_gui(json_data)
