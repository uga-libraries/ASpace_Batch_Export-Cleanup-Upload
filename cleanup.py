import os
import re

from pathlib import Path
from lxml import etree

extent_regex = re.compile(r"(\D)")
barcode_regex = re.compile(r"\[(.*?)\]")
atid_regex = re.compile(r"Archivists Toolkit Database")
dao_regex = re.compile(r"(\bdao\b)")


class EADRecord:
    cert_attrib = ["circa", "ca.", "c", "approximately", "probably", "c.", "between", "after"]

    def __init__(self, file_root):
        self.root = file_root
        self.results = ""
        self.eadid = file_root[0][0].text
        self.daos = False

    def add_eadid(self):
        if self.eadid is None:
            for child in self.root[1][0]:
                if "unitid" in str(child.tag):
                    if "type" in child.attrib:
                        if "Archivists Toolkit Database::RESOURCE" != child.attrib["type"]:
                            self.eadid = child.text
                            self.root[0][0].text = self.eadid
                    else:
                        self.eadid = child.text
                        self.root[0][0].text = self.eadid
        self.results += "Added " + str(self.eadid) + " as eadid\n"

    def delete_empty_notes(self):
        count1_notes = 0
        count2_notes = 0
        for child in self.root.findall(".//*"):
            if child.tag == '{urn:isbn:1-931666-22-9}p':  # {urn:isbn:1-931666-22-9}p dependency on using urn:isbn:
                count1_notes += 1
                if child.text is None and list(child) is None:
                    parent = child.getparent()
                    parent.remove(child)
                    count2_notes += 1
        self.results += "We found " + str(count1_notes) + " <p>'s in " + str(self.eadid) + " and removed " + str(
            count2_notes) + " empty notes\n"

    def edit_extents(self):
        count_ext1 = 0
        count_ext2 = 0
        count_ext3 = 0
        for child in self.root.iter():
            if "extent" in child.tag:
                count_ext1 += 1
                if child.text is not None:  # got "NoneType" object for RBRL/044/CFH
                    child.text.strip()
                    # TODO replace with '[\W_]+' to really remove all non-alphanumeric characters
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
                        self.results += ("Could not remove empty extent field, error:\n" + str(e) + "\n")
                    count_ext2 += 1
        self.results += "We found " + str(count_ext1) + " <extent>'s in " + str(self.eadid) + " and removed " + str(
            count_ext2) + " empty extents and corrected " + str(
            count_ext3) + " extent descriptions starting with non-numeric character\n"
        # delete empty extents
        # remove non-alphanumeric starter characters (ex. (49.5 linear feet, 5.8 gigabytes, 39 audiovisual items))

    def add_certainty_attr(self):
        count_ud = 0
        count_appr = 0
        for child in self.root.findall(".//*"):
            if "unitdate" in child.tag:
                count_ud += 1
                unitdate_text = child.text.split()
                for date in unitdate_text:
                    if date in EADRecord.cert_attrib:
                        child.set("certainty", "approximate")
                        count_appr += 1
        self.results += "We found " + str(count_ud) + " unitdates in " + str(self.eadid) + " and set " + str(
            count_appr) + " certainty attributes\n"

    def add_label_attr(self):
        count_lb = 0
        count_cont = 0
        for child in self.root.iter():
            if "container" in child.tag:
                if "label" not in child.attrib:
                    child.attrib["label"] = "Mixed Materials"
                    count_lb += 1
                    count_cont += 1
                else:
                    count_cont += 1
        self.results += "We found " + str(count_cont) + " containers in " + str(self.eadid) + " and set " + str(
            count_lb) + " label attributes\n"

    def delete_empty_containers(self):
        count1_notes = 0
        count2_notes = 0
        for child in self.root.iter():
            if "container" in child.tag:
                count1_notes += 1
                if child.text is None:
                    self.results += "Found empty container, deleting..."
                    parent = child.getparent()
                    parent.remove(child)
                    self.results += "Removed empty container\n"
                    count2_notes += 1
        self.results += "We found " + str(count1_notes) + " <container>'s in " + str(self.eadid) + " and removed " + \
                        str(count2_notes) + " empty containers\n"

    def update_barcode(self):
        count1_barcodes = 0
        count2_barcodes = 0
        for child in self.root.iter():
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
        self.results += "We found " + str(count1_barcodes) + " <container labels>'s in " + str(self.eadid) + \
                        " and added " + str(count2_barcodes) + " barcodes in the physloc tag\n"

    def remove_at_leftovers(self):
        count1_at = 0
        count2_at = 0
        for element in self.root.iter():
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
                        self.results += "'Archivists Toolkit Database' not found in: " + str(attributes["label"]) + "\n"
        self.results += "We found " + str(count1_at) + " unitids in " + str(self.eadid) + " and removed " + str(
            count2_at) + " Archivists Toolkit legacy ids\n"

    def count_xlinks(self):
        count1_xlink = 0
        count2_xlink = 0
        for element in self.root.iter():  # following counts xlink prefixes in EAD.xml file
            search = dao_regex.search(element.tag)
            if search:
                self.daos = True
                count1_xlink += 1
                attributes = element.attrib
                count2_xlink += len(attributes)
        self.results += "We found " + str(count1_xlink) + " digital objects in " + str(self.eadid) + " and there are " \
                        + str(count2_xlink) + " xlink prefaces in attributes\n"
        ead_string = etree.tostring(self.root, encoding="unicode", pretty_print=True,
                                    doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
        if "xlink" in ead_string:  # remove xlink prefixes if found in EAD.xml file
            del_xlink_attrib = ead_string.replace('xlink:', '')
            clean_xlinks = del_xlink_attrib.encode(encoding="UTF-8")
            self.root = etree.fromstring(clean_xlinks)

    def clean_unused_ns(self):
        # objectify.deannotate(self.root, cleanup_namespaces=True) # doesn't work
        for element in self.root.getiterator():
            element.tag = etree.QName(element).localname
        etree.cleanup_namespaces(self.root)  # https://lxml.de/api/lxml.etree-module.html#cleanup_namespaces

    def clean_do_dec(self):
        ead_string = etree.tostring(self.root, encoding="unicode", pretty_print=True,
                                    doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')  # encoding="unicode" allows non-byte string to be made
        if "xlink" in ead_string:
            del_xlink_attrib = ead_string.replace('xlink:', '')
            if del_xlink_attrib.find('audience="internal"', 0, 62) != -1:  # check if audience="internal" at beginning of <ead>
                xml_string = del_xlink_attrib.replace(
                    '<ead audience="internal" xmlns="urn:isbn:1-931666-22-9" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                    '<ead>')
            elif 'audience="internal"' in del_xlink_attrib:
                xml_string = del_xlink_attrib.replace(
                    '<ead xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" audience="internal" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                    '<ead>')
            else:
                xml_string = del_xlink_attrib.replace(
                    '<ead xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                    '<ead>')
        else:
            if 'audience="internal"' in ead_string:
                xml_string = ead_string.replace(
                    '<ead xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" audience="internal" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                    '<ead>')
            else:
                xml_string = ead_string.replace(
                    '<ead xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd">',
                    '<ead>')
        clean_xml = xml_string.encode(encoding="UTF-8")
        return clean_xml

    def clean_suite(self, ead, custom_clean):
        cleaned_root = None
        if custom_clean:
            if "_ADD_EADID_" in custom_clean:
                ead.add_eadid()
            if "_DEL_NOTES_" in custom_clean:
                ead.delete_empty_notes()
            if "_CLN_EXTENTS_" in custom_clean:
                ead.edit_extents()
            if "_ADD_CERTAIN_" in custom_clean:
                ead.add_certainty_attr()
            if "_ADD_LABEL_" in custom_clean:
                ead.add_label_attr()
            if "_DEL_CONTAIN_" in custom_clean:
                ead.delete_empty_containers()
            if "_ADD_PHYSLOC_" in custom_clean:
                ead.update_barcode()
            if "_DEL_ATIDS_" in custom_clean:
                ead.remove_at_leftovers()
            if "_CNT_XLINKS_" in custom_clean:
                ead.count_xlinks()
            if "_DEL_NMSPCS_" in custom_clean:
                ead.clean_unused_ns()
            if "_DEL_ALLNS_" in custom_clean:
                cleaned_root = ead.clean_do_dec()
            if cleaned_root is None:
                ead_string = etree.tostring(self.root, encoding="unicode", pretty_print=True,
                                            doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
                clean_xml = ead_string.encode(encoding="UTF-8")
                return clean_xml, self.results
            else:
                return cleaned_root, self.results
        else:
            ead_string = etree.tostring(self.root, encoding="unicode", pretty_print=True,
                                        doctype='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
            clean_xml = ead_string.encode(encoding="UTF-8")
            return clean_xml, self.results


# cycle through EAD files in source directory
def cleanup_eads(filepath, custom_clean, output_dir="clean_eads", keep_raw_exports=False):
    filename = Path(filepath).name  # get file name + extension
    fileparent = str(Path(filepath).parent)  # get file's parent folder
    parser = etree.XMLParser(remove_blank_text=True, ns_clean=True)  # clean up redundant namespace declarations
    tree = etree.parse(filepath, parser=parser)
    ead_root = tree.getroot()
    ead = EADRecord(ead_root)
    clean_ead, results = ead.clean_suite(ead, custom_clean)
    results += "\n" + "-" * 135
    clean_ead_file_root = str(Path(output_dir, '{}'.format(filename)))
    with open(clean_ead_file_root, "wb") as CLEANED_EAD:
        CLEANED_EAD.write(clean_ead)
        CLEANED_EAD.close()
    if keep_raw_exports is False:
        for file in os.listdir(fileparent):  # prevents program from rerunning cleanup on cleaned files
            path = Path(fileparent, file)
            os.remove(path)
        return results
    else:
        results += "\nKeeping raw ASpace exports in {}\n".format(output_dir)
        return results
