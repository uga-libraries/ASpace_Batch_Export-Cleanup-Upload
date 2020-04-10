import os
import subprocess
import sys
import webbrowser
import queue
import threading

import PySimpleGUI as sg
from asnake.client import ASnakeClient

import as_export as asx
import cleanup as clean
import files as fetch_files
import secrets as sec
import xtf_upload as xup

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
def run_gui():
    sg.ChangeLookAndFeel('LightBlue2')
    gui_queue = queue.Queue()
    cleanup_default = ["_ADD_EADID_", "_DEL_NOTES_", "_CLN_EXTENTS_", "_ADD_CERTAIN_", "_ADD_LABEL_",
                       "_DEL_CONTAIN_", "_ADD_PHYSLOC_", "_DEL_ATIDS_", "_CNT_XLINKS_", "_DEL_NMSPCS_",
                       "_DEL_ALLNS_"]
    cleanup_options = []
    as_username, as_password, as_api, close_program_as = get_aspace_log()
    if close_program_as is True:
        sys.exit()
    xtf_username, xtf_password, xtf_hostname, xtf_remote_path, close_program_xtf = get_xtf_log()
    if close_program_xtf is True:
        sys.exit()
    menu_def = [['File',
                 ['Open Cleaned EAD Folder',
                  'Open Raw ASpace Exports',
                  '---',
                  'Clear Raw ASpace Export Folder',
                  'Clear Cleaned EAD Folder',
                  '---',
                  'Settings',
                  ['Change Cleanup Defaults',
                   'Change ASpace Login Credentials',
                   'Change XTF Login Credentials'],
                  'Exit', ]
                 ],
                ['Edit',
                 ['Change Cleanup Defaults',
                  'Change ASpace Login Credentials',
                  'Change XTF Login Credentials']
                 ],
                ['Help',
                 ['User Manual',
                  'About']
                 ]
                ]
    layout_simple = [
        [sg.Menu(menu_def, key="_TOP_MENU_SIMPLE_")],
        [sg.Text("Enter Resource Identifiers here:"),
         sg.Text("                "),
         sg.Text("Output Terminal:")],
        [sg.Multiline(key="resource_id_input", size=(35, 30), focus=True),
         sg.Output(size=(100, 30), key="_output_")],
        [sg.Button(button_text="Search and clean", key="_SEARCH_CLEAN_"),
         sg.Checkbox("Open raw ASpace exports", key="_OPEN_RAW_")],
        [sg.Button(button_text="Open Output", key="_OPEN_CLEAN_B_"),
         sg.Button(button_text="Upload", key="_UPLOAD_")]
    ]
    window_simple = sg.Window("ArchivesSpace EAD Export/Cleanup/Upload Program", layout_simple)

    while True:
        # will need a first time setup popup - see if there is a way to take that data and keep it.
        event_simple, values_simple = window_simple.Read()
        # use sg.print to output a scrolling debug window
        if event_simple == 'Cancel' or event_simple is None:
            break
        if event_simple == "_SEARCH_CLEAN_":
            input_ids = values_simple["resource_id_input"]
            resources = input_ids.splitlines()
            for input_id in resources:
                if asx.fetch_results(input_id, as_username, as_password, as_api)[0] is not None:
                    resource_uri, resource_repo = asx.fetch_results(input_id, as_username, as_password, as_api)
                    # export_result = asx.export_ead(input_id, resource_repo, resource_uri, as_username, as_password,
                    #                                as_api)
                    asx_id = input_id
                    print("Beginning AS Export...", end='', flush=True)
                    thread_id = threading.Thread(target=as_export_wrapper, args=(asx_id, gui_queue, input_id,
                                                                                 resource_repo, resource_uri,
                                                                                 as_username, as_password, as_api))
                    thread_id.start()
        try:
            message = gui_queue.get_nowait()
        except queue.Empty:  # get_nowait() will get exception when Queue is empty
            message = None  # break from the loop if no more messages are queued up
        # if message received from queue, display the message in the Window
        if message:
            print('Got a message back from the thread: ', message)
            if values_simple["_OPEN_RAW_"] is True:
                if cleanup_options:  # if cleanup_options is not empty
                    path = clean.cleanup_eads(custom_clean=cleanup_default, keep_raw_exports=True)
                    cwd = os.getcwd()
                    raw_path = cwd + path
                    subprocess.Popen('explorer "{}"'.format(raw_path))
                else:  # if cleanup_options is empty
                    path = clean.cleanup_eads(custom_clean=cleanup_default, keep_raw_exports=True)
                    cwd = os.getcwd()
                    raw_path = cwd + path
                    subprocess.Popen('explorer "{}"'.format(raw_path))
            else:
                if cleanup_options:  # if cleanup_options is not empty
                    clean.cleanup_eads(custom_clean=cleanup_options)
                else:  # if cleanup_options is empty
                    clean.cleanup_eads(custom_clean=cleanup_default)
        #     # progress_bar.UpdateBar(i + 1)
        if event_simple == "_OPEN_CLEAN_B_" or event_simple == 'Open Cleaned EAD Folder':
            cwd = os.getcwd()
            clean_path = cwd + "\clean_eads"
            subprocess.Popen('explorer "{}"'.format(clean_path))
        if event_simple == "Open Raw ASpace Exports":
            cwd = os.getcwd()
            source_path = cwd + "\source_eads"
            subprocess.Popen('explorer "{}"'.format(source_path))
        if event_simple == "Change ASpace Login Credentials":
            as_username, as_password, as_api, close_program_as = get_aspace_log()
        if event_simple == 'Change XTF Login Credentials':
            xtf_username, xtf_password, xtf_hostname, xtf_remote_path, close_program_xtf = get_xtf_log()
        if event_simple == "About":
            window_about_active = True
            layout_about = [
                [sg.Text("Created by Corey Schmidt for the University of Georgia Libraries\n\n"
                         "Version: 0.3a1\n\n"
                         "To check for the latest versions, check the Github\n")],
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
        if event_simple == "Change Cleanup Defaults":
            window_adv_active = True
            winadv_col1 = [[sg.Checkbox("Add Resource ID as EADID", key="_ADD_EADID_")],
                           [sg.Checkbox("Delete Empty Notes", key="_DEL_NOTES_")],
                           [sg.Checkbox("Remove Non-Alphanumerics and Empty Extents", key="_CLN_EXTENTS_")],
                           [sg.Checkbox("Add Certainty Attribute", key="_ADD_CERTAIN_")]]
            winadv_col2 = [[sg.Checkbox("Add label='Mixed Materials' to those without it", key="_ADD_LABEL_")],
                           [sg.Checkbox("Delete Empty Containers", key="_DEL_CONTAIN_")],
                           [sg.Checkbox("Add Barcode in physloc Tag", key="_ADD_PHYSLOC_")],
                           [sg.Checkbox("Remove Archivists' Toolkit IDs", key="_DEL_ATIDS_")]]
            winadv_col3 = [[sg.Checkbox("Remove xlink Prefixes from Digital Objects", key="_CNT_XLINKS_")],
                           [sg.Checkbox("Remove Unused Namespaces", key="_DEL_NMSPCS_")],
                           [sg.Checkbox("Remove All Namesspaces", key="_DEL_ALLNS_")]]
            layout_adv = [
                [sg.Text("Advanced Options for Cleaning EAD Records")],
                [sg.Text("Cleanup Options:", relief=sg.RELIEF_SOLID)],
                [sg.Column(winadv_col1), sg.Column(winadv_col2), sg.Column(winadv_col3)],
                [sg.Button("Save Settings", key="_SAVE_CLEAN_DEF_")]
            ]
            window_adv = sg.Window("Change Cleanup Defaults", layout_adv)
            while window_adv_active is True:
                event_adv, values_adv = window_adv.Read()
                if event_adv == "_SAVE_CLEAN_DEF_":
                    for option_key, option_value in values_adv.items():
                        if option_value is True:
                            print(option_key)
                            if option_key in cleanup_default:
                                cleanup_options.append(option_key)
                    window_adv.close()
                    window_adv_active = False
                if event_adv is None:
                    window_adv.close()
                    window_adv_active = False
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
                    xtfup_id = files
                    thread_id = threading.Thread(target=xtf_upload_wrapper, args=(xtfup_id, gui_queue, remote, files,
                                                                                  xtf_hostname),
                                                 daemon=True)
                    thread_id.start()
                    # xtfup_id = xtfup_id + 1 if xtfup_id < 19 else 0
                    try:
                        message = gui_queue.get_nowait()
                    except queue.Empty:
                        message = None
                    window_upl.close()
                    window_upl_active = False
                if event_upl is None:
                    window_upl.close()
                    window_upl_active = False
        if event_simple == "Exit":
            window_simple.close()
    window_simple.close()


def get_aspace_log():
    as_username = None
    as_password = None
    as_api = None
    window_asplog_active = True
    correct_creds = False
    close_program = False
    while correct_creds is False:
        asplog_col1 = [[sg.Text("Enter your ArchivesSpace username:")],
                       [sg.Text("Enter your ArchivesSpace password:")],
                       [sg.Text("Enter your ArchivesSpace API URL:")]]
        asplog_col2 = [[sg.InputText(focus=True, key="_ASPACE_UNAME_")],
                       [sg.InputText(password_char='*', key="_ASPACE_PWORD_")],
                       [sg.InputText(sec.as_api, key="_ASPACE_API_")]]
        layout_asplog = [
            [sg.Column(asplog_col1), sg.Column(asplog_col2)],
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


def get_xtf_log():
    xtf_username = None
    xtf_password = None
    xtf_host = None
    xtf_remote_path = None
    window_xtflog_active = True
    correct_creds = False
    close_program = False
    while correct_creds is False: # while not
        xtflog_col1 = [[sg.Text("Enter your XTF username:")],
                       [sg.Text("Enter your XTF password:")],
                       [sg.Text("Enter XTF Hostname:")],
                       [sg.Text("Enter XTF Remote Path:")]]
        xtflog_col2 = [[sg.InputText(focus=True, key="_XTF_UNAME_")],
                       [sg.InputText(password_char='*', key="_XTF_PWORD_")],
                       [sg.InputText(sec.xtf_host, key="_XTF_HOSTNAME_")],
                       [sg.InputText(sec.xtf_remote_path, key="_XTF_REMPATH_")]]
        layout_xtflog = [
            [sg.Column(xtflog_col1), sg.Column(xtflog_col2)],
            [sg.Button("Save and Close", bind_return_key=True, key="_SAVE_CLOSE_LOGIN_")]
        ]
        window_xtfcred = sg.Window("XTF Login Credentials", layout_xtflog)
        while window_xtflog_active is True: # while window_xtflog_active
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


def as_export_wrapper(asx_id, gui_queue, input_id, resource_repo, resource_uri, as_username, as_password, as_api):
    # LOCATION 1
    # this is our "long running function call"
    asx.export_ead(input_id, resource_repo, resource_uri, as_username, as_password, as_api)
    # time.sleep(5)  # sleep for a while as a simulation of a long-running computation
    # at the end of the work, before exiting, send a message back to the GUI indicating end
    gui_queue.put('{} ::: done'.format(asx_id))
    # at this point, the thread exits
    return


def xtf_upload_wrapper(xtfup_id, gui_queue, remote, files, xtf_host):
    loading_screen = True
    uploading_popup_layout = [[sg.Image(r'assets/loading.gif')],
                              [sg.Cancel(key="Cancel")]]
    loading_window = sg.Window("Uploading and Re-Indexing", uploading_popup_layout)
    while loading_screen is True:
        events, values = loading_window.Read()
        sg.Image.update_animation(source=r'assets/loading.gif', time_between_frames=0)
        remote.bulk_upload(files)
        remote.execute_commands(['/dlg/app/apache-tomcat-6.0.14-maint/webapps/hmfa/bin/textIndexer -index default'])
        remote.disconnect()
        gui_queue.put('{} ::: done'.format(xtfup_id))
        if events is None or events == 'Cancel':
            loading_window.close()
            loading_screen = False
    loading_window.close()
    return


# sg.preview_all_look_and_feel_themes()
run_gui()
