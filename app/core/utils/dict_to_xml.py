def dict_to_xml_str(data: dict, exclude_keys: list[str] = []) -> str:
    xml_str = "<item>"
    for key, value in data.items():
        if key not in exclude_keys:
            xml_str += f"<{key}>{value}</{key}>"
    xml_str += "</item>"
    return xml_str
