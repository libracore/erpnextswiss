# -*- coding: utf-8 -*-
# Copyright (c) 2025, libracore (https://www.libracore.com) and contributors
# For license information, please see license.txt

from lxml import etree

def validate_xml_against_xsd(xml_string, xsd_file_path):
    """
    Validate an XML string against an XSD schema file using lxml.
    
    Args:
        xml_string (str): The XML string to be validated.
        xsd_file_path (str): Path to the XSD schema file.
        
    Returns:
        bool: True if the XML is valid, False otherwise.
    """
    # Parse the XML and XSD files
    try:
        # Parse the XML from the string
        xml_tree = etree.fromstring(xml_string.encode('utf-8'))
    except Exception as e:
        return False, "Error parsing XML: {0}".format(e)

    try:
        # Read the XSD file
        with open(xsd_file_path, 'rb') as f:
            xsd_content = f.read()
    except FileNotFoundError:
        return False, "XSD schema file not found."
    except Exception as e:
        return False, "Error reading XSD file: {0}".format(e)

    try:
        # Create an XSD schema object
        xsd_schema = etree.XMLSchema(etree.fromstring(xsd_content))
    except Exception as e:
        return False, "Error parsing XSD file: {0}".format(e)

    # Validate the XML tree against the XSD schema
    try:
        xsd_schema.assertValid(xml_tree)
        return True, []
    except etree.DocumentInvalid as e:
        return False, e
    except etree.XMLSyntaxError as e:
        return False, "Invalid XML syntax: {0}".format(e)
