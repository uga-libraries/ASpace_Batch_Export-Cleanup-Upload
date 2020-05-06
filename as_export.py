import json
import re

from asnake.client import ASnakeClient
id_regex = re.compile(r"(^id_+\d)")


class ASExport:
    def __init__(self, input_id, as_username, as_password, as_api):
        self.input_id = input_id
        self.as_usernmae = as_username
        self.as_password = as_password
        self.as_api = as_api
        self.resource_id = None
        self.resource_repo = None
        self.client = None
        self.error = None
        self.result = None
        self.filepath = ""
        try:
            self.client = ASnakeClient(baseurl=as_api, username=as_username, password=as_password)
            self.client.authorize()
        except Exception as asnake_error:
            self.error = \
                "Your username and/or password were entered incorrectly. Try changing those in Edit -> Change ASpace " \
                "Login Credentials\n" + str(asnake_error)

    # take input of resource identifiers and search for them
    def fetch_results(self):
        # sort multi-line identifiers
        id_lines = []
        if "-" in self.input_id:
            id_lines = self.input_id.split("-")
        elif "." in self.input_id:
            id_lines = self.input_id.split(".")
        else:
            id_lines.append(self.input_id)
        search_resources = self.client.get('/search', params={"q": 'four_part_id:' + self.input_id, "page": 1,
                                                              "type": ['resource']})  # need to change to get_paged - but returns a generator object - maybe for loop that?
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
                    total_ids = []
                    for key, value in json_info.items():
                        id_match = id_regex.match(key)
                        if id_match:
                            total_ids.append(value)
                    combined_id = ""
                    user_id_index = 0
                    for json_id in total_ids:
                        try:
                            if json_id == id_lines[user_id_index]:
                                resource_full_uri = result["uri"].split("/")
                                self.resource_id = resource_full_uri[-1]
                                self.resource_repo = resource_full_uri[2]
                                match_results[combined_id[:-1]] = json_info["title"]
                                user_id_index += 1
                            else:
                                raise Exception
                        except Exception:
                            for json_id_2 in total_ids:
                                combined_id += json_id_2 + "-"
                            # strip extra - at end
                            non_match_results[combined_id[:-1]] = json_info["title"]  # had to insert [:-1] in else to
                            user_id_index += 1
                if non_match_results:  # if non_match_results contains non-matches, return error
                    self.error = "{} results were found, but the resource identifier did not match. " \
                                 "Have you entered the resource id correctly?".format(result_count) + \
                                 "\nStatus code: " + \
                                 str(search_resources.status_code) + "\nUser Input: {}".format(self.input_id) + \
                                 "\nResults: "
                    for ident, title in non_match_results.items():
                        self.error += "\n     Resource ID: {:15} {:>1}{:<5} Title: {} \n".format(ident, "|", "", title)
            else:
                self.error = "No results were found. Have you entered the resource id correctly?\nStatus code: " + \
                             str(search_resources.status_code) + "\nUser Input: {}\n".format(self.input_id)

    # make a request to the API for an ASpace ead
    def export_ead(self, include_unpublished=False, include_daos=True, numbered_cs=True, ead3=False, ):
        request_ead = self.client.get('repositories/{}/resource_descriptions/{}.xml'.format(self.resource_repo,
                                                                                            self.resource_id),
                                      params={'include_unpublished': include_unpublished, 'include_daos': include_daos,
                                              'numbered_cs': numbered_cs, 'print_pdf': False, 'ead3': ead3})
        # TODO save the record to a designated folder in the same directory.
        if request_ead.status_code == 200:
            if "/" in self.input_id:
                self.input_id = self.input_id.replace("/", "_")
            self.filepath = "source_eads/{}.xml".format(self.input_id)
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_ead.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_ead,
                                                                                                 request_ead.text)
            return None, self.error

    def export_marcxml(self, output_dir, include_unpublished=False):
        request_marcxml = self.client.get('/repositories/{}/resources/marc21/{}.xml'.format(self.resource_repo,
                                                                                            self.resource_id),
                                          params={'include_unpublished_marc': include_unpublished})
        if request_marcxml.status_code == 200:
            if "/" in self.input_id:
                self.input_id = self.input_id.replace("/", "_")
            self.filepath = output_dir + "/{}.xml".format(self.input_id)
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_marcxml.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_marcxml,
                                                                                                 request_marcxml.text)
            return None, self.error

    def export_pdf(self, output_dir, include_unpublished=False, include_daos=True, numbered_cs=True, ead3=False):
        request_pdf = self.client.get('repositories/{}/resource_descriptions/{}.pdf'.format(self.resource_repo,
                                                                                            self.resource_id),
                                      params={'include_unpublished': include_unpublished, 'include_daos': include_daos,
                                              'numbered_cs': numbered_cs, 'print_pdf': True, 'ead3': ead3})
        if request_pdf.status_code == 200:
            if "/" in self.input_id:
                self.input_id = self.input_id.replace("/", "_")
            self.filepath = output_dir + "/{}.pdf".format(self.input_id)
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_pdf.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_pdf,
                                                                                                 request_pdf.text)
            return None, self.error

    def export_labels(self, output_dir):
        request_labels = self.client.get('repositories/{}/resource_labels/{}.tsv'.format(self.resource_repo,
                                                                                         self.resource_id))
        if request_labels.status_code == 200:
            if "/" in self.input_id:
                self.input_id = self.input_id.replace("/", "_")
            self.filepath = output_dir + "{}.tsv".format(self.input_id)
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_labels.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_labels,
                                                                                                 request_labels.text)
            return None, self.error
