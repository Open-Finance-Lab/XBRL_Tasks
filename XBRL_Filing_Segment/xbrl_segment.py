from lxml import etree
import os

KEYWORDS = {
    "balance_sheets": {
        "and": ["balance", "sheet"],
        "or": [],
        "not": ["note", "parenthetical"]
    },
    "balance_sheets_parenthetical": {
        "and": ["balance", "sheet", "parenthetical"],
        "or": [],
        "not": ["note"]
    },
    "income_statements": {
        "and": ["statement"],
        "or": ["operation","income","incomeloss"],
        "not": ["note", "comprehensive"]
    },
    "comprehensive_income_statements": {
        "and": ["comprehensive", "statement"],
        "or": ["operation","income","incomeloss"],
        "not": ["note"]
    },
    "statements_of_cash_flows": {
        "and": ["statement", "cash", "flow"],
        "or": [],
        "not": ["note"]
    },
    "statements_of_equity": {
        "and": ["statement"],
        "or": ["equity", "change","stockholder"],
        "not": ["note"]
    }
}

def keyword_checking(str, keywords=None):
    """
    Check if a string satisfies the keyword rules:
    1. Must contain all keywords in `and_keywords`.
    2. Must contain at least one keyword in `or_keywords`.
    3. Must not contain any keywords in `not_keywords`.

    :param string: The input string to check.
    :param and_keywords: List of keywords that must all be present in the string.
    :param or_keywords: List of keywords where at least one must be present in the string.
    :param not_keywords: List of keywords that must not be present in the string.
    :return: True if the string satisfies the rules, False otherwise.
    """
    and_keywords = keywords['and'] or []
    or_keywords = keywords['or'] or []
    not_keywords = keywords['not'] or []

    string = str.lower()
    if not all(keyword in string for keyword in and_keywords):
        return False

    if or_keywords and not any(keyword in string for keyword in or_keywords):
        return False

    if any(keyword in string for keyword in not_keywords):
        return False

    return True

def filter_pre_xml(input_file, output_file, keywords=None):
    """
    Process the input pre.xml file to extract and include specified sections:
    1. Keep the first two lines.
    2. Include <link:roleRef> with roleURI containing "balance" and "sheet", but not "note" or "parenthetical".
    3. Include <link:presentationLink> corresponding to the extracted roleURI.
    4. Keep the last line.

    Return:
    1. Matched roleURI.
    2. List of unique xlink:label values from <link:loc> within <link:presentationLink>.

    :param input_file: Path to the input pre.xml file.
    :param output_file: Path to save the processed XML file.
    :return: Tuple (matched_role_uris, unique_labels).
    """
    tree = etree.parse(input_file)
    root = tree.getroot()

    namespaces = root.nsmap

    # Find roleRef elements with the specified criteria
    role_refs = root.findall('.//link:roleRef', namespaces)
    matching_role_uris = []

    for role_ref in role_refs:
        role_uri = role_ref.get('roleURI')
        if role_uri and keyword_checking(role_uri, keywords):
            matching_role_uris.append(role_uri)
            print(f"    {role_uri}")

    if matching_role_uris==[]:
        return [], []
    
    # Create a new root element for the output XML
    new_root = etree.Element(root.tag, root.attrib, nsmap=root.nsmap)

    # Add matching <link:roleRef> elements
    for role_ref in role_refs:
        role_uri = role_ref.get('roleURI')
        if role_uri in matching_role_uris:
            new_root.append(role_ref)

    # Add corresponding <link:presentationLink> elements
    presentation_links = root.findall('.//link:presentationLink', namespaces)
    labels = list()
    for presentation_link in presentation_links:
        role = presentation_link.get('{http://www.w3.org/1999/xlink}role')
        if role in matching_role_uris:
            new_root.append(presentation_link)
            # Extract xlink:label from <link:loc> elements
            loc_elements = presentation_link.findall('link:loc', namespaces)
            for loc in loc_elements:
                href = loc.get('{http://www.w3.org/1999/xlink}href')
                if href:
                    label = href.rsplit('#', 1)[-1]
                    labels.append(label)


    new_tree = etree.ElementTree(new_root)
    with open(output_file, 'wb') as f:
        new_tree.write(f, xml_declaration=True, encoding='US-ASCII', pretty_print=True)

    return matching_role_uris, labels

def filter_cal_xml(input_file, output_file, matching_role_uris):
    """
    Process the input cal.xml file to extract and include specified sections:
    1. Keep the first two lines.
    2. Include <link:roleRef> with roleURI matching those obtained from pre.xml.
    3. Include <link:calculationLink> corresponding to the matched roleURI.
    4. Keep the last line.

    :param input_file: Path to the input pre.xml file.
    :param output_file: Path to save the processed XML file.
    :param matching_role_uris: List of roleURI values obtained from pre.xml.
    """
    tree = etree.parse(input_file)
    root = tree.getroot()
    namespaces = root.nsmap

    # Create a new root element for the output XML
    new_root = etree.Element(root.tag, root.attrib, nsmap=root.nsmap)

    # Add matching <link:roleRef> elements
    role_refs = root.findall('.//link:roleRef', namespaces)
    for role_ref in role_refs:
        role_uri = role_ref.get('roleURI')
        if role_uri in matching_role_uris:
            new_root.append(role_ref)

    # Add corresponding <link:calculationLink> elements
    calculation_links = root.findall('.//link:calculationLink', namespaces)
    for calculation_link in calculation_links:
        role = calculation_link.get('{http://www.w3.org/1999/xlink}role')
        if role in matching_role_uris:
            new_root.append(calculation_link)

    new_tree = etree.ElementTree(new_root)
    with open(output_file, 'wb') as f:
        new_tree.write(f, xml_declaration=True, encoding='US-ASCII', pretty_print=True)


def filter_def_xml(input_file, output_file, matching_role_uris):
    """
    Process the input def.xml file to extract and include specified sections:
    1. Keep the first two lines.
    2. Keep all <link:arcroleRef> lines.
    3. Include <link:roleRef> with roleURI matching those obtained from pre.xml.
    4. Include <link:definitionLink> corresponding to the matched roleURI.
    5. Keep the last line.

    :param input_file: Path to the input pre.xml file.
    :param output_file: Path to save the processed XML file.
    :param matching_role_uris: List of roleURI values obtained from pre.xml.
    """
    tree = etree.parse(input_file)
    root = tree.getroot()
    namespaces = root.nsmap
    new_root = etree.Element(root.tag, root.attrib, nsmap=root.nsmap)

    # Add all <link:arcroleRef> elements
    arcrole_refs = root.findall('.//link:arcroleRef', namespaces)
    for arcrole_ref in arcrole_refs:
        new_root.append(arcrole_ref)

    # Add matching <link:roleRef> elements
    role_refs = root.findall('.//link:roleRef', namespaces)
    for role_ref in role_refs:
        role_uri = role_ref.get('roleURI')
        if role_uri in matching_role_uris:
            new_root.append(role_ref)

    # Add corresponding <link:definitionLink> elements
    definition_links = root.findall('.//link:definitionLink', namespaces)
    for definition_link in definition_links:
        role = definition_link.get('{http://www.w3.org/1999/xlink}role')
        if role in matching_role_uris:
            new_root.append(definition_link)

    new_tree = etree.ElementTree(new_root)
    with open(output_file, 'wb') as f:
        new_tree.write(f, xml_declaration=True, encoding='US-ASCII', pretty_print=True)


def filter_xsd(input_file, output_file, role_uris):
    """
    Process the input xsd file to extract and include specified sections:
    1. Keep the first two lines.
    2. Include all <xsd:import>, <xs:import>, <import> lines.
    3. Include all lines within <xsd:annotation><xsd:appinfo>, <xs:annotation><xs:appinfo>, or <annotation><appinfo>, 
       including <link:linkbaseRef>.
    4. Include <link:roleType> elements matching roleURI from pre.xml.
    5. Include <xsd:element>, <xs:element>, <element> elements where id matches id from <link:roleType>.
    6. Ensure <xsd:annotation>, <xs:annotation>, or <annotation> and their child <appinfo> sections are kept intact.
    7. Keep the last line.

    :param input_file: Path to the input xsd file.
    :param output_file: Path to save the processed XML file.
    :param role_uris: List of roleURI values obtained from pre.xml.
    """
    # Parse the input XML file
    tree = etree.parse(input_file)
    root = tree.getroot()
    namespaces = root.nsmap

    new_root = etree.Element(root.tag, root.attrib, nsmap=root.nsmap)

    prefix_annotation = ''
    if 'xsd' in namespaces:
        prefix_annotation = 'xsd:'
    elif 'xs' in namespaces:
        prefix_annotation = 'xs:'

    annotation_tag = f'{prefix_annotation}annotation'
    appinfo_tag = f'{prefix_annotation}appinfo'
    import_tag = f'{prefix_annotation}import'
    element_tag = f'{prefix_annotation}element'

    # Add all <xsd:import>, <xs:import>, <import> lines
    # import_tags = ['xsd:import', 'import']
    # for tag in import_tags:
    imports = root.findall(f'.//{import_tag}', namespaces)
    for imp in imports:
        new_root.append(imp)

    matching_ids = []

    
    # annotation_tags = ['xsd:annotation', 'annotation']
    # for tag in annotation_tags:
    annotations = root.findall(f'.//{annotation_tag}', namespaces)
    for annotation in annotations:
        # appinfo_tags = ['xsd:appinfo','appinfo']
        # for appinfo_tag in appinfo_tags:
        appinfo = annotation.find(f'.//{appinfo_tag}', namespaces)
        if appinfo is not None:
            filtered_appinfo = etree.Element(appinfo.tag, appinfo.attrib, nsmap=appinfo.nsmap)
            # Add <link:roleType> elements matching roleURI from pre.xml
            filtered_appinfo.tail = '\n'
            role_types = root.findall('.//link:roleType', namespaces)
            for role_type in role_types:
                role_uri = role_type.get('roleURI')
                if role_uri in role_uris:
                    filtered_appinfo.append(role_type)
                    matching_ids.append(role_type.get('id'))
                    
            if len(filtered_appinfo):
                filtered_annotation = etree.Element(annotation.tag, annotation.attrib, nsmap=annotation.nsmap)
                filtered_annotation.append(filtered_appinfo)
                new_root.append(filtered_annotation)


    # Add <link:roleType> elements matching roleURI from pre.xml
    # matching_ids = []
    # role_types = root.findall('.//link:roleType', namespaces)
    # for role_type in role_types:
    #     role_uri = role_type.get('roleURI')
    #     if role_uri in role_uris:
    #         new_root.append(role_type)
    #         matching_ids.append(role_type.get('id'))

    # Add <xsd:element>, <xs:element>, <element> elements where id matches id from <link:roleType>
    # element_tags = ['xsd:element','element']
    # for tag in element_tags:
    elements = root.findall(f'.//{element_tag}', namespaces)
    for element in elements:
        element_id = element.get('id')
        if element_id in matching_ids:
            new_root.append(element)

    new_tree = etree.ElementTree(new_root)
    with open(output_file, 'wb') as f:
        new_tree.write(f, xml_declaration=True, encoding='UTF-8', pretty_print=True)

def filter_htm_xml(input_file, output_file, labels):
    """
    Process the input htm.xml file to extract and include specified sections:
    1. Keep the first three lines.
    2. For each label in the labels list, substitute the first '-' with ':' and include matching lines.
    3. Include <context> lines where id matches contextRef from the selected labels.
    4. Include all <unit> lines.
    5. Ensure the final order is: first lines, context, unit, labels, and the last line.
    6. Keep the last line.
    
    :param input_file: Path to the input htm.xml file.
    :param output_file: Path to save the processed XML file.
    :param labels: List of labels from pre.xml with the first '-' replaced with ':'.
    """

    tree = etree.parse(input_file)
    root = tree.getroot()
    namespaces = root.nsmap

    new_root = etree.Element(root.tag, root.attrib, nsmap=root.nsmap)
    new_root.tail = '\n'
    schema_ref = root.find('.//link:schemaRef', namespaces)
    if schema_ref is not None:
        schema_ref.tail = '\n\t'
        new_root.append(schema_ref)

    # Step 2: Process labels and collect contextRefs
    processed_facts = []
    context_refs = []

    for label in labels:
        substituted_label = label.replace('_', ':', 1)
        facts = root.findall(f'.//{substituted_label}', namespaces)
        for fact in facts:
            fact_str = etree.tostring(fact, encoding='unicode', pretty_print=True)
            if fact_str not in processed_facts:
                processed_facts.append(fact_str)
                context_ref = fact.get('contextRef')
                if context_ref:
                    context_refs.append(context_ref)

        # for label_element in label_elements:
        #     fact = etree.tostring(label_element, encoding='unicode',pretty_print=True)
        #     if label_str not in processed_labels:
        #         processed_labels.add(label_str)
        #         context_ref = label_element.get('contextRef')
        #         if context_ref:
        #             context_refs.add(context_ref)

    # Step 3: Include <context> lines where id matches contextRef from step 2
    included_contexts = []
    context_labels = []
    for context_id in context_refs:
        context_elements = root.findall(f".//context[@id='{context_id}']", namespaces)

        for context_element in context_elements:

            for prefix in namespaces:
                if prefix:
                    # Search for any string matching "{prefix}:..."
                    for element in context_element.iter():
                        if element.tag.startswith(f"{{{namespaces[prefix]}}}"):
                            dimension = element.get("dimension")
                            tag_text = element.text or ""
                            if dimension:
                                dimension = dimension.replace(':', '_', 1)
                                context_labels.append(dimension)
                            if tag_text:
                                tag_text = tag_text.replace(':', '_', 1)
                                context_labels.append(tag_text)

            context_str = etree.tostring(context_element, encoding='unicode',pretty_print=True)
            if context_str not in included_contexts:
                included_contexts.append(context_str)

    # Step 4: Include all <unit> lines
    unit_elements = root.findall('.//unit', namespaces)
    included_units = [etree.tostring(unit, encoding='unicode',pretty_print=True) for unit in unit_elements]

    # Step 5: Add content to the new root in order
    for context_str in included_contexts:
        context_element = etree.fromstring(context_str)
        context_element.tail = '\n\t'
        new_root.append(context_element)
    
    for unit_str in included_units:
        unit_element = etree.fromstring(unit_str)
        unit_element.tail = '\n\t'
        new_root.append(unit_element)

    for label_str in processed_facts:
        label_element = etree.fromstring(label_str)
        label_element.tail = '\n\t'
        new_root.append(label_element)

    new_tree = etree.ElementTree(new_root)
    with open(output_file, 'wb') as f:
        new_tree.write(f, xml_declaration=True, encoding='utf-8', pretty_print=True)
    
    return context_labels

def filter_lab_xml(input_file, output_file, context_labels, pre_labels):
    """
    Process the input lab.xml file to extract and include specified sections:
    1. Keep the first two lines.
    2. Keep all <link:roleRef> lines (should be 7 lines).
    3. Include the <link:labelLink> section with filtered content:
       - Use labels from context_labels and pre_labels.
       - For each label:
         1. Search <link:loc> where xlink:href matches the label.
         2. Search <link:labelArc> where xlink:from matches the xlink:label obtained from <link:loc>.
         3. Search <link:label> where xlink:label matches the xlink:to obtained from <link:labelArc>.
       - Include these lines in order.
    4. Keep the last lines </link:labelLink> and </link:linkbase>.

    :param input_file: Path to the input lab.xml file.
    :param output_file: Path to save the processed XML file.
    :param context_labels: Labels obtained from htm.xml.
    :param pre_labels: Labels obtained from pre.xml.
    """
    tree = etree.parse(input_file)
    root = tree.getroot()
    namespaces = root.nsmap

    new_root = etree.Element(root.tag, root.attrib, nsmap=root.nsmap)
    new_root.tail = '\n'

    # Step 2: Keep all <link:roleRef> lines
    role_refs = root.findall('.//link:roleRef', namespaces)
    for role_ref in role_refs:
        new_root.append(role_ref)

    # Step 3: Include <link:labelLink> section with filtered content
    label_link = root.find('.//link:labelLink', namespaces)
    if label_link is not None:
        filtered_label_link = etree.Element(label_link.tag, label_link.attrib, nsmap=root.nsmap)
        valid_labels = set(context_labels + pre_labels)

        for label in valid_labels:
            # Step 3.1: Find <link:loc> matching the label
            loc_elements = label_link.findall('./link:loc', namespaces)
            included_labels = set()

            for loc in loc_elements:
                href = loc.get('{http://www.w3.org/1999/xlink}href', '')
                if '#' in href and href.split('#')[-1] == label:
                    filtered_label_link.append(loc)
                    included_labels.add(loc.get('{http://www.w3.org/1999/xlink}label'))

            # Step 3.2: Find <link:labelArc> matching xlink:from from <link:loc>
            label_arcs = label_link.findall('./link:labelArc', namespaces)
            included_tos = set()

            for label_arc in label_arcs:
                label_from = label_arc.get('{http://www.w3.org/1999/xlink}from')
                if label_from in included_labels:
                    filtered_label_link.append(label_arc)
                    included_tos.add(label_arc.get('{http://www.w3.org/1999/xlink}to'))

            # Step 3.3: Find <link:label> matching xlink:to from <link:labelArc>
            label_elements = label_link.findall('./link:label', namespaces)
            for label_element in label_elements:
                label_attr = label_element.get('{http://www.w3.org/1999/xlink}label')
                if label_attr in included_tos:
                    filtered_label_link.append(label_element)
        filtered_label_link.tail = '\n'
        new_root.append(filtered_label_link)

    new_tree = etree.ElementTree(new_root)
    with open(output_file, 'wb') as f:
        new_tree.write(f, xml_declaration=True, encoding='utf-8', pretty_print=True)

def batch_process_folder(folder_path, results_folder):

    for subfolder_name in os.listdir(folder_path):
        subfolder_path = os.path.join(folder_path, subfolder_name)

        if os.path.isdir(subfolder_path):
            subfolder_results_path = os.path.join(results_folder, subfolder_name)
            os.makedirs(subfolder_results_path, exist_ok=True)
            print(subfolder_name)
            for statement_name in KEYWORDS.keys():
                statement_path = os.path.join(subfolder_results_path, statement_name)
                os.makedirs(statement_path, exist_ok=True)
                for file_name in os.listdir(subfolder_path):
                    file_path = os.path.join(subfolder_path, file_name)

                    if file_name.endswith("pre.xml"):
                        output_path = os.path.join(statement_path, file_name)
                        # print(f"   {file_path}")
                        # print(f"   {output_path}")
                        print(f"   {statement_name}")
                        matching_role_uris, pre_labels = filter_pre_xml(file_path, output_path, KEYWORDS[statement_name])
                        print()
                        context_labels = []

                        if matching_role_uris == []:
                            continue

                        calc_file_path = file_path.replace("pre.xml", "cal.xml")
                        calc_output_path = output_path.replace("pre.xml", "cal.xml")
                        def_file_path = file_path.replace("pre.xml", "def.xml")
                        def_output_path = output_path.replace("pre.xml", "def.xml")
                        xsd_file_path = file_path.replace("_pre.xml", ".xsd")
                        xsd_output_path = output_path.replace("_pre.xml", ".xsd")
                        lab_file_path = file_path.replace("pre.xml", "lab.xml")
                        lab_output_path = output_path.replace("pre.xml", "lab.xml")

                        filter_cal_xml(calc_file_path, calc_output_path, matching_role_uris)
                        filter_def_xml(def_file_path, def_output_path, matching_role_uris)
                        filter_xsd(xsd_file_path, xsd_output_path, matching_role_uris)

                        for f_name in os.listdir(subfolder_path):
                            f_path= os.path.join(subfolder_path, f_name)
                            if f_name.endswith("htm.xml"):
                                htm_output_path = os.path.join(statement_path, f_name)
                                context_labels = filter_htm_xml(f_path, htm_output_path, pre_labels)
                                break
                        
                        filter_lab_xml(lab_file_path, lab_output_path, context_labels, pre_labels)
                        break


if __name__ == "__main__":
    batch_process_folder("sample_case", "sample_case_segmentation")