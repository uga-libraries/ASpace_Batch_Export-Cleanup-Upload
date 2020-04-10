import os
import re

from lxml import etree

extent_regex = re.compile(r"(\D)")
barcode_regex = re.compile(r"\[(.*?)\]")
atid_regex = re.compile(r"Archivists Toolkit Database")
dao_regex = re.compile(r"(\bdao\b)")


class EADRecord:
    cert_attrib = ["circa", "ca.", "c", "approximately", "probably", "c.", "between", "after"]

    def __init__(self, file_root):
        self.eadid = file_root[0][0].text
        self.daos = False

    def add_eadid(self, file_root):
        ead_file_root = file_root
        if self.eadid is None:
            for child in ead_file_root[1][0]:
                if "unitid" in str(child.tag):
                    if "type" in child.attrib:
                        if "Archivists Toolkit Database::RESOURCE" != child.attrib["type"]:
                            self.eadid = child.text
                            ead_file_root[0][0].text = self.eadid
                    else:
                        print(child.text)
                        self.eadid = child.text
                        ead_file_root[0][0].text = self.eadid
            print("Added " + str(self.eadid) + " as eadid")
        return ead_file_root

    def delete_empty_notes(self, file_root):
        count1_notes = 0
        count2_notes = 0
        ead_file_root = file_root
        for child in ead_file_root.findall(".//*"):
            if child.tag == '{urn:isbn:1-931666-22-9}p':  # {urn:isbn:1-931666-22-9}p dependency on using urn:isbn:
                count1_notes += 1
                if child.text is None:
                    parent = child.getparent()
                    parent.remove(child)
                    count2_notes += 1
            # if "p" in child.tag:
            #     print(child.tag)
        print("We found " + str(count1_notes) + " <p>'s in " + str(self.eadid) + " and removed " + str(count2_notes) +
              " empty notes")
        return ead_file_root
        # delete empty paragraphs

    def edit_extents(self, file_root):
        count_ext1 = 0
        count_ext2 = 0
        count_ext3 = 0
        ead_file_root = file_root
        for child in ead_file_root.iter():
            if "extent" in child.tag:
                count_ext1 += 1
                if child.text is not None:  # got "NoneType" object for RBRL/044/CFH
                    child.text.strip()
                    match = extent_regex.match(child.text)
                    if match:  # Converts this: "(8x10") NEGATIVE [negative missing] b/w"  to this: "8x10" NEGATIVE ...
                        cleaned_extent1 = child.text.replace("(", "", 1)
                        cleaned_extent2 = cleaned_extent1.replace(")", "", 1)
                        child.text = cleaned_extent2
                        count_ext3 += 1
                elif child.text is None:
                    parent = child.getparent()
                    try:
                        parent.remove(child)
                    except Exception as e:
                        print("Could not remove empty extent field, error:\n" + str(e))
                    count_ext2 += 1
        print("We found " + str(count_ext1) + " <extent>'s in " + str(self.eadid) + " and removed " + str(
            count_ext2) + " empty extents and corrected " + str(count_ext3) + " extent descriptions starting "
                                                                              "with non-numeric character")
        return ead_file_root
        # delete empty extents
        # remove non-alphanumeric starter characters (ex. (49.5 linear feet, 5.8 gigabytes, 39 audiovisual items))

    def add_certainty_attr(self, file_root):
        count_ud = 0
        count_appr = 0
        ead_file_root = file_root
        for child in ead_file_root.findall(".//*"):
            if "unitdate" in child.tag:
                count_ud += 1
                unitdate_text = child.text.split()
                for date in unitdate_text:
                    if date in EADRecord.cert_attrib:
                        child.set("certainty", "approximate")
                        count_appr += 1
        print("We found " + str(count_ud) + " unitdates in " + str(self.eadid) + " and set " + str(count_appr) +
              " certainty attributes")
        return ead_file_root
        # add certainty attribute to dates that include words like (circa, attribute)

    def add_label_attr(self, file_root):
        count_lb = 0
        count_cont = 0
        ead_file_root = file_root
        for child in ead_file_root.iter():
            if "container" in child.tag:
                if "label" not in child.attrib:
                    child.attrib["label"] = "Mixed Materials"
                    count_lb += 1
                    count_cont += 1
                else:
                    count_cont += 1
        print("We found " + str(count_cont) + " containers in " + str(self.eadid) + " and set " + str(
            count_lb) + " label attributes")
        return ead_file_root
        # add label attributes to container elements

    def delete_empty_containers(self, file_root):
        count1_notes = 0
        count2_notes = 0
        ead_file_root = file_root
        for child in ead_file_root.iter():
            if "container" in child.tag:
                count1_notes += 1
                if child.text is None:
                    print("Found empty container, deleting...")
                    parent = child.getparent()
                    parent.remove(child)
                    print("Removed empty container")
                    count2_notes += 1
        print("We found " + str(count1_notes) + " <container>'s in " + str(self.eadid) + " and removed " +
              str(count2_notes) + " empty containers")
        return ead_file_root

    def update_barcode(self, file_root):
        count1_barcodes = 0
        count2_barcodes = 0
        ead_file_root = file_root
        for child in ead_file_root.iter():
            if "container" in child.tag:
                attributes = child.attrib
                if 'label' in attributes:
                    count1_barcodes += 1
                    match = barcode_regex.search(attributes["label"])
                    if match:
                        count2_barcodes += 1
                        barcode = match.group(1)
                        # child.set("containerid", match.group(1)) -- set as attribute to container
                        parent = child.getparent()
                        barcode_tag = etree.SubElement(parent, "physloc", type="barcode")
                        barcode_tag.text = "{}".format(barcode)
        print("We found " + str(count1_barcodes) + " <container labels>'s in " + str(self.eadid) + " and added " +
              str(count2_barcodes) + " barcodes in the physloc tag")
        return ead_file_root

    def remove_at_leftovers(self, file_root):
        count1_at = 0
        count2_at = 0
        ead_file_root = file_root
        for element in ead_file_root.iter():
            if "unitid" in element.tag:
                attributes = element.attrib
                count1_at += 1
                if "type" in attributes:
                    match = atid_regex.match(attributes["type"])
                    if match:
                        count2_at += 1
                        parent = element.getparent()
                        parent.remove(element)
                    else:
                        print("'Archivists Toolkit Database' not found in: " + str(attributes["label"]))
        print("We found " + str(count1_at) + " unitids in " + str(self.eadid) + " and removed " +
              str(count2_at) + " Archivists Toolkit legacy ids")
        return ead_file_root

    def count_xlinks(self, file_root):
        count1_xlink = 0
        count2_xlink = 0
        ead_file_root = file_root
        for element in ead_file_root.iter():
            search = dao_regex.search(element.tag)
            if search:
                self.daos = True
                count1_xlink += 1
                attributes = element.attrib
                count2_xlink += len(attributes)
        print("We found " + str(count1_xlink) + " digital objects in " + str(self.eadid) + " and there are " +
              str(count2_xlink) + " xlink prefaces in attributes")
        return ead_file_root

    @staticmethod
    def clean_unused_ns(file_root):
        ead_file_root = file_root
        # objectify.deannotate(ead_file_root, cleanup_namespaces=True) # doesn't work
        for element in ead_file_root.getiterator():
            element.tag = etree.QName(element).localname
        etree.cleanup_namespaces(ead_file_root)  # https://lxml.de/api/lxml.etree-module.html#cleanup_namespaces
        return ead_file_root

    @staticmethod
    def clean_do_dec(file_root):
        # encoding="unicode" allows non-byte string to be made
        ead_string = etree.tostring(file_root, encoding="unicode", pretty_print=True,
                                    doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        if "xlink" in ead_string:
            del_xlink_attrib = ead_string.replace('xlink:', '')
            # check if audience="internal" at beginning of <ead>
            if del_xlink_attrib.find('audience="internal"', 0, 62) != -1:
                xml_string = del_xlink_attrib.replace('<ead audience="internal" xmlns="urn:isbn:1-931666-22-9" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                                                      '<ead>')
            elif 'audience="internal"' in del_xlink_attrib:
                xml_string = del_xlink_attrib.replace('<ead xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" audience="internal" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                                                      '<ead>')
            else:
                xml_string = del_xlink_attrib.replace('<ead xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                                                      '<ead>')
        else:
            if 'audience="internal"' in ead_string:
                xml_string = ead_string.replace('<ead xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" audience="internal" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                                                '<ead>')
            else:
                xml_string = ead_string.replace('<ead xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                                                '<ead>')
        # print(xml_string)
        clean_xml = xml_string.encode(encoding="UTF-8")
        return clean_xml

    @staticmethod
    def clean_suite(ead, file_root, custom_clean):
        addid = ead.add_eadid(file_root)
        delnot = ead.delete_empty_notes(file_root)
        edtext = ead.edit_extents(file_root)
        certatt = ead.add_certainty_attr(file_root)
        labelatt = ead.add_label_attr(file_root)
        empcont = ead.delete_empty_containers(file_root)
        contid = ead.update_barcode(file_root)
        remvat = ead.remove_at_leftovers(file_root)
        cntxlk = ead.count_xlinks(file_root)
        eadhead = ead.clean_unused_ns(file_root)
        xmldec = ead.clean_do_dec(file_root)
        cleanup_cmds = {"_ADD_EADID_": addid, "_DEL_NOTES_": delnot, "_CLN_EXTENTS_": edtext,
                        "_ADD_CERTAIN_": certatt, "_ADD_LABEL_": labelatt, "_DEL_CONTAIN_": empcont,
                        "_ADD_PHYSLOC_": contid, "_DEL_ATIDS_": remvat, "_CNT_XLINKS_": cntxlk,
                        "_DEL_NMSPCS_": eadhead, "_DEL_ALLNS_": xmldec}
        cmds_ordered = [cmd for cmd in cleanup_cmds.keys() if cmd in custom_clean]  # not sure if this will match add_eadid or return false for not matching whole ead.add_eadid(ead_root)
        cleaned_root = None
        print(cmds_ordered)
        for cmd in cmds_ordered:
            if cmd in cleanup_cmds: # if the string in cmds_ordered matches the key in cleanup_cmds
                cleaned_root = cleanup_cmds[cmd]  # run the value of the key which should be a class method specified above
        if not isinstance(cleaned_root, bytes):
            ead_string = etree.tostring(cleaned_root, encoding="unicode", pretty_print=True,
                                        doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
            clean_xml = ead_string.encode(encoding="UTF-8")
            return clean_xml
        else:
            return cleaned_root


# cycle through EAD files in directory
def cleanup_eads(custom_clean, keep_raw_exports=False):
    if custom_clean is not None:
        if isinstance(custom_clean, list):
            parser = etree.XMLParser(remove_blank_text=True, ns_clean=True)  # clean up redundant namespace declarations
            for file in os.listdir("source_eads/"):
                # run schemaclean.pl
                #                 # if file.endswith(".xml"):
                #                 #     addcmd = ['perl5.30.1.exe',
                #                 #               'schemaclean.pl',
                #                 #               'source_eads/',
                #                 #               str(file)]
                #                 #     subprocess.call(addcmd + sys.argv)
                tree = etree.parse('source_eads/{}'.format(file), parser=parser)
                ead_root = tree.getroot()
                ead = EADRecord(ead_root)
                clean_ead = ead.clean_suite(ead, ead_root, custom_clean)
                # insert line here to check for filename and rename to have ms1234 or RBRL-123 in front
                clean_ead_file_root = 'clean_eads/{}'.format(file)
                with open(clean_ead_file_root, "wb") as CLEANED_EAD:
                    CLEANED_EAD.write(clean_ead)
                    CLEANED_EAD.close()
                print("\n" + "-" * 50)
            if keep_raw_exports is False:
                for file in os.listdir("source_eads/"):  # prevents program from rerunning cleanup on cleaned files
                    path = "source_eads/" + file
                    os.remove(path)
        else:
            print("Input for custom_clean was invalid. Must be a list.\n"
                  "Input: {}".format(custom_clean))
            return None
    else:
        print("Input for custom_clean was invalid. Must be a list.\n"
              "Input: {}".format(custom_clean))
        return None
    return '\source_eads'


# search for existance of a schema folder for ArchivesSpace EAD records
current_directory = os.getcwd()
for root, directories, files in os.walk(current_directory):
    # if "schema_eads" not in directories:
    #     print("No schema_eads folder found, creating new one...", end='', flush=True)
    #     current_directory = os.getcwd()
    #     folder = "schema_eads"
    #     schema_path = os.path.join(current_directory, folder)
    #     os.mkdir(schema_path)
    #     print(" Done.")
    if "source_eads" not in directories:
        print("No source_eads folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "source_eads"
        source_path = os.path.join(current_directory, folder)
        os.mkdir(source_path)
        print(" Done.")
    if "clean_eads" not in directories:
        print("No clean_eads folder found, creating new one...", end='', flush=True)
        current_directory = os.getcwd()
        folder = "clean_eads"
        clean_path = os.path.join(current_directory, folder)
        os.mkdir(clean_path)
        print(" Done.")
        break
    else:
        break
