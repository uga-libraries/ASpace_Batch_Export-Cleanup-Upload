import json
import re

from as_xtf_GUI import logger
from pathlib import Path

id_field_regex = re.compile(r"(^id_+\d)")
id_combined_regex = re.compile(r'[\W_]+', re.UNICODE)


class ASExport:
    """
    Interacts with the ASpace API to search for and retrieve records.
    """
    def __init__(self, input_id, repo_id, client, output_dir, rmv_anc, export_all=False):
        """
        Must contain resource identifier, repository identifier, ASnake client, and output directory.

        Args:
            input_id (str): user generated from the Resource Identifier box in the GUI
            repo_id (int): contains the number for which a repository is assigned via the ArchivesSpace instance
            client (ASnake.client object): a client object from ASnake.client to allow to connect to the ASpace API
            output_dir (str): filepath containing the folder a user wants files to be exported to
        """
        self.input_id = input_id  # TODO: Replace using the user input as filename and use the ID from ASpace (not number, but user supplied in ASpace
        """str: user generated resource identifier"""
        self.filename = None
        """str: the name assigned to the exported file"""
        self.remove_alphanums = rmv_anc
        """bool: user option to remove all non-alphanumeric characters from the exported filename"""
        self.repo_id = repo_id
        """int: repository ID number selected by a user from the GUI - Search Across will not work"""
        self.resource_id = None
        """int: ArchivesSpace's assigned resource identifier found in the resource URI"""
        self.resource_repo = None
        """int: ArchivesSpace's assigned respository identifier found in a resource's URI"""
        self.client = client
        """ASnake.client object: client object from ASnake.client to allow to connect to the ASpace API"""
        self.error = None
        """str: value is None unless an error occurs and is then populated with a string detailing the error"""
        self.result = None
        """str: value is none unless an operation completes or multiple results are returned and is then populated 
        with a string detailing the result(s)"""
        self.filepath = None
        """str: filepath where records will be exported to"""
        self.output_directory = output_dir
        """str: location of the output directory for the file"""
        self.export_all = export_all
        """bool: whether exporting all records for a repository"""

    def fetch_results(self):
        """
        Searches ArchivesSpace for a resource that matches the self.input_id.

        For an in-depth review on how this code is structured, see the wiki:
        https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#fetch_results

        Returns:
            None
        """
        if self.export_all is False:
            combined_user_id = id_combined_regex.sub('', self.input_id)  # remove all non-alphanumeric characters
            if self.repo_id is not None:
                search_resources = self.client.get_paged('/repositories/{}/search'.format(str(self.repo_id)),
                                                         params={"q": 'four_part_id:' + self.input_id,
                                                                 "type": ['resource']})
            else:
                search_resources = self.client.get_paged('/search', params={"q": 'four_part_id:' + self.input_id,
                                                                            "type": ['resource']})
            search_results = [result for result in search_resources]
        else:
            search_results = [{"json": json.dumps(self.client.get(f'/repositories/{str(self.repo_id)}/resources/{str(self.input_id)}').json())}]
            combined_user_id = ""
        if not search_results:
            self.error = "No results were found. Have you entered the correct repository and/or resource ID?\n" \
                         "Results: " + str(search_results) + \
                         "\nUser Input: {}\n".format(self.input_id) + "-" * 135
        else:  # TODO: break this into different method called parse_result or something
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
                if self.export_all is True:
                    combined_user_id = combined_aspace_id_clean
                    self.filepath = str(Path(self.output_directory, combined_aspace_id_clean))
                user_id_index = 0
                if combined_user_id == combined_aspace_id_clean:  # if user-input id matches id in ASpace
                    try:
                        if self.remove_alphanums is True:  # TODO: confirm this exports RBRL112JRR not closed one and doesn't change the filename to add CLOSED
                            self.filename = combined_aspace_id_clean
                        else:
                            self.filename = combined_aspace_id[:-1]
                        self.filepath = str(Path(self.output_directory, str(self.filename)))
                        aspace_id = combined_aspace_id[:-1]
                        resource_full_uri = json_info["uri"].split("/")
                        self.resource_id = resource_full_uri[-1]
                        self.resource_repo = resource_full_uri[2]
                        match_results[aspace_id] = json_info["title"]
                        user_id_index += 1
                    except ValueError as parse_error:
                        self.error = (f'There was an error parsing ArchivesSpace ID, URI, or Title:'
                                      f'\nERROR: {parse_error}')
                else:
                    non_match_results[combined_aspace_id[:-1]] = json_info["title"]
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
                for ident, title in non_match_results.items():  # TODO: add match_results to self.results - above code is grabbing the 2nd result and exporting the filename of RBRL112JRRCLOSED
                    self.result += "Resource ID: {:15} {}{:<5} Title: {} \n\n".format(ident, "|", "", title)
                self.result += "-" * 135

    # make a request to the API for an ASpace ead
    def export_ead(self, include_unpublished=False, include_daos=True, numbered_cs=True, ead3=False):
        """
        Handles exporting EAD.xml files from ArchivesSpace.

        For an in-depth review on how this code is structured, see the wiki:
        https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#export_ead

        Args:
            include_unpublished (bool, optional): doesn't include unpublished portions of the resource
            include_daos (bool, optional): include digital objects
            numbered_cs (bool, optional): include numbered container levels
            ead3 (bool, optional): do not use EAD3 schema, instead defaults to EAD2002

        Returns:
            self.filepath (str): filepath where records will be exported to
            self.result (str): value is none unless an operation completes or multiple results are returned and is then
            populated with a string detailing the result(s)
            self.error (str): value is None unless an error occurs and is then populated with a string detailing the
            error
        """
        try:
            request_ead = self.client.get('repositories/{}/resource_descriptions/{}.xml'.format(self.resource_repo,
                                                                                                self.resource_id),
                                          params={'include_unpublished': include_unpublished,
                                                  'include_daos': include_daos, 'numbered_cs': numbered_cs,
                                                  'print_pdf': False, 'ead3': ead3})
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
        except Exception as e:
            self.error = "\nThe following errors were found when exporting {}:\n{}\n".format(self.input_id, e)

            self.error += "-" * 135
            return None, self.error

    def export_marcxml(self, include_unpublished=False):
        """
        Handles exporting MARCXML files from ArchivesSpace.

        For an in-depth review on how this code is structured, see the wiki:
        https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#export_marcxml

        Args:
            include_unpublished (bool): doesn't include unpublished portions of the resource

        Returns:
            self.filepath (str): filepath where records will be exported to
            self.result (str): value is none unless an operation completes or multiple results are returned and is then
            populated with a string detailing the result(s)
            self.error (str): value is None unless an error occurs and is then populated with a string detailing the
            error
        """
        try:
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
        except Exception as e:
            self.error = "\nThe following errors were found when exporting {}:\n{}\n".format(self.input_id, e)
            self.error += "-" * 135
            return None, self.error

    def export_pdf(self, include_unpublished=False, include_daos=True, numbered_cs=True, ead3=False):
        """
        Handles exporting PDF files from ArchivesSpace.

        For an in-depth review on how this code is structured, see the wiki:
        https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#export_pdf

        Args:
            include_unpublished (bool, optional): doesn't include unpublished portions of the resource
            include_daos (bool, optional): include digital objects
            numbered_cs (bool, optional): include numbered container levels
            ead3 (bool, optional): do not use EAD3 schema, instead defaults to EAD2002

        Returns:
            self.filepath (str): filepath where records will be exported to
            self.result (str): value is none unless an operation completes or multiple results are returned and is then
            populated with a string detailing the result(s)
            self.error (str): value is None unless an error occurs and is then populated with a string detailing the
            error
        """
        try:
            request_pdf = self.client.get('repositories/{}/resource_descriptions/{}.pdf'.format(self.resource_repo,
                                                                                                self.resource_id),
                                          params={'include_unpublished': include_unpublished,
                                                  'include_daos': include_daos, 'numbered_cs': numbered_cs,
                                                  'print_pdf': True, 'ead3': ead3})
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
        except Exception as e:
            self.error = "\nThe following errors were found when exporting {}:\n{}\n".format(self.input_id, e)
            self.error += "-" * 135
            return None, self.error

    def export_labels(self):
        """
        Handles exporting container label files from ArchivesSpace.

        For an in-depth review on how this code is structured, see the wiki:
        https://github.com/uga-libraries/ASpace_Batch_Export-Cleanup-Upload/wiki/Code-Structure#export_labels

        Returns:
            self.filepath (str): filepath where records will be exported to
            self.result (str): value is none unless an operation completes or multiple results are returned and is then
            populated with a string detailing the result(s)
            self.error (str): value is None unless an error occurs and is then populated with a string detailing the
            error
        """
        try:
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
        except Exception as e:
            self.error = "\nThe following errors were found when exporting {}:\n{}\n".format(self.input_id, e)
            self.error += "-" * 135
            return None, self.error
