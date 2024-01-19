# ArchivesSpace Batch Exporter

## Overview

This application batch exports records from ArchivesSpace in EAD, MARCXML, Container Label, or PDF. Additionally, it 
can run exported EAD records through a series of cleanup processes. Lastly, a user can choose to connect to an 
XTF-based finding aid website server to upload .xml or .pdf files to their instance of XTF.

![EAD_Export_Demo](https://user-images.githubusercontent.com/62658840/129760524-5895c29c-1b82-4572-9b68-6952a6710b0e.gif)

## Getting Started

### Dependencies
- [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake) - Library used for interacting with the 
ArchivesSpace API
- [cx_Freeze](https://cx-freeze.readthedocs.io/en/latest/) - Generated the executable file
- [Inno](https://jrsoftware.org/isinfo.php) - Generated Windows installer (for GitHub action only or local .exe generation)
- [loguru](https://pypi.org/project/loguru/) - Logging package
- [lxml](https://lxml.de/) - Parsing XML files for cleanup
- [paramiko](https://www.paramiko.org/) - Connecting to XTF server for file upload/indexing/delete
- [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI) - The GUI used
- [requests](https://requests.readthedocs.io/en/latest/) - Used for validating API link
- [scp](https://github.com/jbardin/scp.py) - Manages client for uploading/indexing/deleting files from XTF server

### Installation

#### For Windows Users
1. Go to [Releases](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/releases) and download the 
.exe file from the latest release.
2. Follow the on-screen instructions.
3. The [User Manual](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual) walking you 
through the program and its features can be found on the Wiki page.

#### For Mac Users
1. Install Python 3 on your computer. You can install python using the following link:
https://www.python.org/downloads/mac-osx/
2. Download the GitHub repo using the Code button in the top right corner of the repo, then unzip the downloaded file.
3. Open your terminal and go to the unzipped folder. Run the command: `pip3 install -r requirements.txt`.
4. After installing requirements, run the command: `python3 as_xtf_GUI.py`. This will start the program.
5. The [User Manual](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual) walking you 
through the program and its features can be found on the Wiki page.

### Script Arguments

Open your console of choice and navigate to the project directory and run `python3 as_xtf_GUI.py` to start the program. 
See #Prerequisites for more info.

#### Prerequisites
1. Install Python 3 on your computer. You can install python using the following link:
https://www.python.org/downloads/
2. Install packages as specified in requirements.txt
3. Your ArchivesSpace Instance's API URL (8089), your username and password
4. (OPTIONAL) XTF hostname URL, XTF remote path for EAD files, XTF indexer path to re-index new and/or changed files, 
and XTF lazy index path to update the .lazy files with appropriate permissions for rw-rw-r.

#### Installing
1. Clone/Download or Fork the Master branch
2. Set up your virtual environment using the packages as specified in requirements.txt
3. Run as_xtf_GUI.py. This will automatically create folders and a defaults.json file at the same directory
4. If you need to reset the defaults or rerun setup, delete the folders within the repository and defaults.json file 
and rerun as_xtf_GUI.py.

### Testing
There are currently no unittests associated with this project.

Right now, the best way to test the program is to input resource identifiers and try uploading
them to XTF. If you want to generate errors, input any string or random numbers, such as "hello world"
or 42.

#### For UGA
For Hargrett and Russell Libraries, input the following to generate different results:

* ms3000_2e - the biggest one, will take a long time to export and index
* ms1170-series1
* ms1376
* RBRL/025/ACLU
* RBRL/044/CFH
* RBRL/112/JRR
* HCTC001
* HCTC021
* UA97-121
* UA20-004
* hmap1640b55
* hmap1792a7

You can also try using the following, which will generate more than 1 result in the Output Terminal:
* ms1170
* RBRL/220/ROGP

## Workflow
See the [User Manual](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual) for a 
complete walkthrough of the application

## Author
* Corey Schmidt - Project Management Librarian/Archivist at the University of Georgia Libraries

## Acknowledgements:
* Adriane Hanson - Head of Digital Stewardship at the University of Georgia Libraries
* ArchivesSpace community
* Kevin Cottrell - GALILEO/Library Infrastructure Systems Architect at the University of Georgia Libraries
* PySimpleGUI
* Shawn Kiewel
* Tyler Brockmeyer
