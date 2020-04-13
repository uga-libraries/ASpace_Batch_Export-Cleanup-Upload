import json
import os

from asnake.client import ASnakeClient


# take input of resource identifiers and search for them
def fetch_results(input_id, as_username, as_password, as_api):
    resource_uri = ""
    resource_repo = ""
    # Initiate AS client
    try:
        client = ASnakeClient(baseurl=as_api, username=as_username, password=as_password)
        client.authorize()
    except Exception as asnake_error:
        error = "Your username and/or password were entered incorrectly. Try changing those in Edit -> Change ASpace " \
                "Login Credentials\n" + str(asnake_error)
        return None, error
    # sort multi-line identifiers
    id_lines = []
    if "-" in input_id:
        id_lines = input_id.split("-")
    elif "." in input_id:
        id_lines = input_id.split(".")
    else:
        id_lines.append(input_id)
    search_resources = client.get('/search', params={"q": 'four_part_id:' + input_id, "page": 1, "type": ['resource']})  # need to change to get_paged - but returns a generator object - maybe for loop that?
    if search_resources.status_code != 200:
        return None, "There was an issue connecting to ArchivesSpace" + str(search_resources.status_code)
    else:
        search_results = json.loads(search_resources.content.decode())  # .decode().strip()
        if search_results["results"]:
            # after searching for them, get their URI
            result_count = len(search_results["results"])
            non_match_results = {}
            match_results = {}
            for result in search_results["results"]:
                json_info = json.loads(result["json"])
                total_id_lines = range(0, len(id_lines))
                combined_id = ""
                for id_num in total_id_lines:
                    if "id_{}".format(str(id_num)) in json_info:  # check to see if id_# exists - ms1170.series4 has
                        # only id_0 vs. ms1170-series5 - has id_1
                        combined_id += json_info["id_{}".format(str(id_num))] + "-"  # had to insert [:-1] in else to
                        # strip extra - at end
                        if json_info["id_{}".format(str(id_num))] == id_lines[id_num]:  # cycle through the range of id
                            # lines for the length of ids in id_lines list, if the id_#'s value (string) for a
                            # multi-line identifier matches the id string found in id_lines, then continue
                            resource_full_uri = result["uri"].split("/")
                            resource_uri = resource_full_uri[-1]
                            resource_repo = resource_full_uri[2]
                            match_results[combined_id[:-1]] = json_info["title"]
                        else:
                            non_match_results[combined_id[:-1]] = json_info["title"]
            if match_results:  # if non_match_results is empty, return variables
                return resource_uri, resource_repo
            else:
                results_error = "{} results were found, but the resource identifier did not match. " \
                                "Have you entered the resource id correctly?".format(result_count) + \
                                "\nStatus code: " + \
                                str(search_resources.status_code) + "\nUser Input: {}".format(input_id) + "\nResults: "
                for ident, title in non_match_results.items():
                    results_error += "\n     Resource ID: {:10} {:>1}{:<5} Title: {} \n".format(ident, "|", "", title)
            return None, results_error
        else:
            error = "No results were found. Have you entered the resource id correctly?\nStatus code: " + \
                    str(search_resources.status_code) + "\nUser Input: {}\n".format(input_id)
            return None, error


# make a request to the API for an ASpace ead
def export_ead(input_id, resource_repo, resource_uri, as_username, as_password, as_api):
    # Initiate AS client
    client = ASnakeClient(baseurl=as_api, username=as_username, password=as_password)
    client.authorize()
    print("Exporting EAD files...", end='', flush=True)
    request_ead = client.get('repositories/{}/resource_descriptions/{}.xml?'.format(resource_repo, resource_uri),
                             params={'include_unpublished': False, 'include_daos': True, 'numbered_cs': True,
                                     'print_pdf': False, 'ead3': False})
    # save the record to a designated folder in the same directory.
    if request_ead.status_code == 200:
        if "/" in input_id:
            input_id = input_id.replace("/", "_")
        filepath = "source_eads/{}.xml".format(input_id)
        with open(filepath, "wb") as local_file:
            local_file.write(request_ead.content)
            local_file.close()
            result = " Done"
            return filepath, result
    else:
        error = " The following errors were found when exporting {}: {}\n".format(input_id, request_ead.status_code)
        return None, error


# search for existance of a source folder for ArchivesSpace EAD records
try:
    current_directory = os.getcwd()
    for root, directories, files in os.walk(current_directory):
        if "source_eads" in directories:
            source_path = current_directory + "/source_eads"
            break
        else:
            raise Exception
except Exception as e:
    print(str(e) + "\nNo source folder found, creating new one...", end='', flush=True)
    current_directory = os.getcwd()
    folder = "source_eads"
    source_path = os.path.join(current_directory, folder)
    os.mkdir(source_path)
    print("{} folder created\n".format(folder))
