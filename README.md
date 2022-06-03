# ArchivesSpace Batching

This application batch exports records from ArchivesSpace in EAD, MARCXML, Container Label, or PDF form. 
Additionally, it can run exported EAD records through a series of cleanup processes. Lastly, a user can
enable the XTF version to upload .xml or .pdf files to their instance of XTF, a finding aid website hosting platform.

![EAD_Export_Demo](https://user-images.githubusercontent.com/62658840/129760524-5895c29c-1b82-4572-9b68-6952a6710b0e.gif)

## Getting Started

### For Windows Users
1. Go to [Releases](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/releases) and download the 
.exe file from the latest release.
2. Follow the on-screen instructions.
3. The [User Manual](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual) walking you 
through the program and its features can be found on the Wiki page.

### For Mac Users
1. Install Python 3 on your computer. You can install python using the following link:
https://www.python.org/downloads/mac-osx/
2. Download the GitHub repo using the Code button in the top right corner of the repo, then unzip the downloaded file.
3. Open your terminal and go to the unzipped folder. Run the command: `pip3 install -r requirements.txt`.
4. After installing requirements, run the command: `python3 as_xtf_GUI.py`. This will start the program.
5. The [User Manual](https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/User-Manual) walking you 
through the program and its features can be found on the Wiki page.

### For Developers

#### Prerequisites
1. Install Python 3 on your computer. You can install python using the following link:
https://www.python.org/downloads/
2. Packages as specified in requirements.txt
3. Your ArchivesSpace Instance's API URL (8089), your username and password
4. (OPTIONAL) XTF hostname URL, XTF remote path for EAD files, and XTF indexer path to re-index new and/or changed 
files.

#### Installing
1. Clone/Download or Fork the Master branch
2. Set up your virtual environment using the packages as specified in requirements.txt
3. Run as_xtf_GUI.py. This will automatically create folders and a defaults.json file at the same directory
4. If you need to reset the defaults or rerun setup, delete the folders within the repository and defaults.json file 
and rerun as_xtf_GUI.py.

## Testing
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
* UA00-024
* hmap1640b55
* hmap1792a7

You can also try using the following, which will generate more than 1 result in the Output Terminal:
* ms1170
* RBRL/220/ROGP

## Built With
* [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI) - The GUI used
* [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake) - Library used for interacting with the 
ArchivesSpace API
* [Paramiko](https://github.com/paramiko/paramiko) - SSH and client library
* [lxml](https://github.com/lxml/lxml) - Used for parsing and modifying .xml files
* [PyInstaller](https://github.com/pyinstaller/pyinstaller) - Generated the executable file
* [Inno](https://jrsoftware.org/isinfo.php) - Generated Windows installer

## Contributing
See the CONTRIBUTING.md for more information.

## Versioning
Trying our best to adhere to [SemVer](https://semver.org/).

## Authors
* Corey Schmidt - ArchivesSpace Project Manager at the University of Georgia Libraries

## License Information

This program is licensed under a Creative Commons Attribution Share Alike 4.0 International. Please see LICENSE.txt for 
more information.

### Special Thanks to:
* Adriane Hanson - Head of Digital Stewardship at the University of Georgia Libraries
* ArchivesSpace community
* Kevin Cottrell - GALILEO/Library Infrastructure Systems Architect at the University of Georgia Libraries
* PySimpleGUI
* Shawn Kiewel
* Tyler Brockmeyer
