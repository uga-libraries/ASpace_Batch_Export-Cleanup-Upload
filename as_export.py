import json
import re

from pathlib import Path

id_field_regex = re.compile(r"(^id_+\d)")
id_combined_regex = re.compile('[\W_]+', re.UNICODE)


class ASExport:
    def __init__(self, input_id, repo_id, client, output_dir):
        self.input_id = input_id
        if "/" in self.input_id:
            self.filename = self.input_id.replace("/", "")  # Replace backslashes with nothing - xtf builds urls with no spaces in-between
        else:
            self.filename = self.input_id
        self.repo_id = repo_id
        self.resource_id = None
        self.resource_repo = None
        self.client = client
        self.error = None
        self.result = None
        self.filepath = str(Path(output_dir, self.filename))

    # take input of resource identifiers and search for them
    def fetch_results(self):
        combined_user_id = id_combined_regex.sub('', self.input_id)  # remove all non-alphanumeric characters
        if self.repo_id is not None:
            search_resources = self.client.get_paged('/repositories/{}/search'.format(self.repo_id),
                                                     params={"q": 'four_part_id:' + self.input_id,
                                                             "type": ['resource']})
        else:
            search_resources = self.client.get_paged('/search', params={"q": 'four_part_id:' + self.input_id,
                                                                        "type": ['resource']})
        search_results = []
        for result in search_resources:
            search_results.append(result)
        if not search_results:
            self.error = "No results were found. Have you entered the correct repository and/or resource ID?\n" \
                         "Results: " + str(search_results) + \
                         "\nUser Input: {}\n".format(self.input_id) + "-" * 135
            # self.error = "There was an issue connecting to ArchivesSpace\n Error: "\
            #              + str(search_resources.status_code) + "\nContent: " + str(search_resources.content)
        else:
            # after searching for them, get their URI
            result_count = len(search_results)
            aspace_id = ""
            non_match_results = {}
            match_results = {}
            for result in search_results:
                combined_aspace_id = ""
                json_info = json.loads(result["json"])
                for key, value in json_info.items():
                    id_match = id_field_regex.match(key)
                    if id_match:
                        combined_aspace_id += value + "-"
                combined_aspace_id_clean = id_combined_regex.sub('', combined_aspace_id)  # remove all non-alphanumeric characters
                user_id_index = 0
                try:
                    if combined_user_id == combined_aspace_id_clean:  # if user-input id matches id in ASpace
                        aspace_id = combined_aspace_id[:-1]
                        resource_full_uri = result["uri"].split("/")
                        self.resource_id = resource_full_uri[-1]
                        self.resource_repo = resource_full_uri[2]
                        match_results[combined_aspace_id[:-1]] = json_info["title"]
                        user_id_index += 1
                    else:
                        raise Exception
                except Exception:
                    # strip extra - at end
                    non_match_results[combined_aspace_id[:-1]] = json_info["title"]  # had to insert [:-1] in else to
                    user_id_index += 1
            if non_match_results and not match_results:  # if non_match_results contains non-matches, return error
                self.error = "{} results were found, but the resource identifier did not match. " \
                             "Have you entered the resource id correctly?".format(result_count) + \
                             "\nUser Input: {}".format(self.input_id) + \
                             "\nResults: "
                for ident, title in non_match_results.items():
                    self.error += "\n     Resource ID: {:15} {:>1}{:<5} Title: {} \n".format(ident, "|", "", title)
                self.error += "-" * 135
            if non_match_results and match_results:
                self.result = "Returning {}...\nOther results:\n\n".format(aspace_id)
                for ident, title in non_match_results.items():
                    self.result += "Resource ID: {:15} {}{:<5} Title: {} \n\n".format(ident, "|", "", title)
                self.result += "-" * 135

    # make a request to the API for an ASpace ead
    def export_ead(self, include_unpublished=False, include_daos=True, numbered_cs=True, ead3=False):
        request_ead = self.client.get('repositories/{}/resource_descriptions/{}.xml'.format(self.resource_repo,
                                                                                            self.resource_id),
                                      params={'include_unpublished': include_unpublished, 'include_daos': include_daos,
                                              'numbered_cs': numbered_cs, 'print_pdf': False, 'ead3': ead3})
        if request_ead.status_code == 200:
            self.filepath += ".xml"
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_ead.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_ead,
                                                                                                 request_ead.text)
            self.error += "-" * 135
            return None, self.error

    def export_marcxml(self, include_unpublished=False):
        request_marcxml = self.client.get('/repositories/{}/resources/marc21/{}.xml'.format(self.resource_repo,
                                                                                            self.resource_id),
                                          params={'include_unpublished_marc': include_unpublished})
        if request_marcxml.status_code == 200:
            self.filepath += ".xml"
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_marcxml.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_marcxml,
                                                                                                 request_marcxml.text)
            self.error += "-" * 135
            return None, self.error

    def export_pdf(self, include_unpublished=False, include_daos=True, numbered_cs=True, ead3=False):
        request_pdf = self.client.get('repositories/{}/resource_descriptions/{}.pdf'.format(self.resource_repo,
                                                                                            self.resource_id),
                                      params={'include_unpublished': include_unpublished, 'include_daos': include_daos,
                                              'numbered_cs': numbered_cs, 'print_pdf': True, 'ead3': ead3})
        if request_pdf.status_code == 200:
            self.filepath += ".pdf"
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_pdf.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_pdf,
                                                                                                 request_pdf.text)
            self.error += "-" * 135
            return None, self.error

    def export_labels(self):
        request_labels = self.client.get('repositories/{}/resource_labels/{}.tsv'.format(self.resource_repo,
                                                                                         self.resource_id))
        if request_labels.status_code == 200:
            self.filepath += ".tsv"
            with open(self.filepath, "wb") as local_file:
                local_file.write(request_labels.content)
                local_file.close()
                self.result = "Done"
                return self.filepath, self.result
        else:
            self.error = "\nThe following errors were found when exporting {}:\n{}: {}\n".format(self.input_id,
                                                                                                 request_labels,
                                                                                                 request_labels.text)
            self.error += "-" * 135
            return None, self.error
