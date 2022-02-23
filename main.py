import sys
import logging
import lxml.etree
import re
import os
import json
import xml.dom.minidom

# import argparse

def main(argv):
  # based on https://stackoverflow.com/questions/2302315/how-can-info-and-debug-logging-message-be-sent-to-stdout-and-higher-level-messag/31459386#comment113314476_31459386
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.DEBUG)
  # all messages below logging.WARNING level will NOT be redirected to stdout
  stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)

  stderr_handler = logging.StreamHandler(sys.stderr)
  stderr_handler.setLevel(logging.WARNING)

  logger = logging.getLogger()
  logger.addHandler(stdout_handler)
  logger.addHandler(stderr_handler)

  # if args.debug is True:
  logger.setLevel(logging.DEBUG)
  # logger.setLevel(logging.INFO)

  # TODO make this settable via input argument
  project_root_dirname = 'project'

  for root, dirs, files in os.walk(project_root_dirname):
    # https://stackoverflow.com/questions/6670029/can-i-force-os-walk-to-visit-directories-in-alphabetical-order/6670926#6670926
    # need to sort dirs to make sure access order is consistent 
    dirs.sort()

    logger.debug('root = ' + root)

    elem_tag_filepath = os.path.join(root, 'tag.txt')
    elem_attrib_filepath = os.path.join(root, 'attrib.txt')
    elem_nsmap_filepath = os.path.join(root, 'nsmap.txt')
    elem_prefix_filepath = os.path.join(root, 'prefix.txt')
    elem_text_filepath = os.path.join(root, 'text.txt')
    elem_tail_filepath = os.path.join(root, 'tail.txt')

    with open(elem_tag_filepath, 'r') as elem_tag_file:
      elem_tag_str = elem_tag_file.read()
    with open(elem_attrib_filepath, 'r') as elem_attrib_file:
      elem_attrib_str = elem_attrib_file.read()
    with open(elem_nsmap_filepath, 'r') as elem_nsmap_file:
      elem_nsmap_str = elem_nsmap_file.read()
    with open(elem_prefix_filepath, 'r') as elem_prefix_file:
      elem_prefix_str = elem_prefix_file.read()
    with open(elem_text_filepath, 'r') as elem_text_file:
      elem_text_str = elem_text_file.read()
    with open(elem_tail_filepath, 'r') as elem_tail_file:
      elem_tail_str = elem_tail_file.read()

    # tag must exist otherwise cannot create element
    if not elem_tag_str:
      raise ValueError('elem_tag_str is empty!')
    # need to use QName to split tag that contains both namespace and localname e.g. {http://www.plcopen.org/xml/tc6_0200}fileHeader
    elem_tag_data = lxml.etree.QName(elem_tag_str)
    # attrib should have been stored as json str so load it as dict
    elem_attrib_data = json.loads(elem_attrib_str)
    # nsmap should have been stored as json str so load it as dict
    elem_nsmap_data = json.loads(elem_nsmap_str)
    # have to convert 'null' to None otherwise namespace key will not be empty (which is what 'null' actually represents)
    if 'null' in elem_nsmap_data.keys():
      elem_nsmap_data[None] = elem_nsmap_data.pop('null')

    # check if root element otherwise create subelement
    if root == project_root_dirname:
      # nsmap property cannot be set so must be used in constructor
      elem = lxml.etree.Element(elem_tag_data.localname, nsmap=elem_nsmap_data)
      # temp attribute for helping find parent_elem, MUST be deleted before writing to file
      elem.attrib['temp'] = root
      # need to set as root_elem otherwise will lose track of it
      root_elem = elem

    else:
      # use XPath expression to determine existing parent element via temp attribute (use wildcard to search all elements)
      parent_elem_list = root_elem.xpath('//*[@temp="' + os.path.dirname(root) + '"]')

      if len(parent_elem_list) == 1:
        parent_elem = parent_elem_list[0]
      else:
        logger.debug(parent_elem_list)
        raise ValueError('len(parent_elem_list) = ' + str(len(parent_elem_list)))

      # nsmap property cannot be set so must be used in constructor
      elem = lxml.etree.SubElement(parent_elem, elem_tag_data.localname, nsmap=elem_nsmap_data)
      # temp attribute for helping find parent_elem, MUST be deleted before writing to file
      elem.attrib['temp'] = root

    # assign attributes 
    for key, val in elem_attrib_data.items():
      elem.attrib[key] = val
    # need to check if elem_text_str is empty otherwise will add unnecessary closing tag
    if elem_text_str:
      elem.text = elem_text_str
    # prevent unnecessary writes
    if elem_tail_str:
      elem.tail = elem_tail_str

  project_tree = lxml.etree.ElementTree(root_elem)
  # REMOVE temp attribute from all elements
  for elem in project_tree.iter():
    elem.attrib.pop('temp')

  # lxml.etree.indent(project_tree, space='  ')
  project_tree.write('test.xml', encoding='utf-8', method='xml', pretty_print=True, xml_declaration=True)

  # with open('test.xml', 'r') as test_xml:
    # xml_str = test_xml.read()

  # with open('test.xml', 'w') as test_xml:
    # test_xml.write(re.sub('>\n', '>\r\n', xml_str)) 

def main_old(argv):

  # based on https://stackoverflow.com/questions/2302315/how-can-info-and-debug-logging-message-be-sent-to-stdout-and-higher-level-messag/31459386#comment113314476_31459386
  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.DEBUG)
  # all messages below logging.WARNING level will NOT be redirected to stdout
  stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)

  stderr_handler = logging.StreamHandler(sys.stderr)
  stderr_handler.setLevel(logging.WARNING)

  logger = logging.getLogger()
  logger.addHandler(stdout_handler)
  logger.addHandler(stderr_handler)

  # if args.debug is True:
  logger.setLevel(logging.DEBUG)

  project_tree = lxml.etree.parse('test/example_project.xml')
  project_root_elem = project_tree.getroot()

  def create_dirs_and_files(elem_list, parent_dirpath=''):
    # used for default naming of elements that have no name attribute
    child_counter = 1

    for elem in elem_list:
      # check is parent exists and throw error if it does but parent_dirpath is empty
      if elem.getparent() is not None:
        if not parent_dirpath:
          raise ValueError('parent_dirpath is empty!')

      # pad child_counter with zeros to make sure order is preserved when sorting
      child_counter_str = str(child_counter).zfill(3) + '_'

      # use name attribute as child_dirname otherwise use zero padded tag
      if 'name' in elem.attrib.keys():
        # take only last substring after / as it usually comes in url form e.g. http://www.3s-software.com/plcopenxml/globalvars
        child_dirname = child_counter_str + re.sub('.*/', '', elem.attrib['name'])
      else:
        # need to use QName to split tag that contains both namespace and localname e.g. {http://www.plcopen.org/xml/tc6_0200}fileHeader
        elem_tag_data = lxml.etree.QName(elem.tag)

        if elem.getparent() is None:
          # TODO make this settable via input argument
          # only case this can happen is for project tag so replace child_dirname
          child_dirname = elem_tag_data.localname
        else:
          # need to use QName to split tag that contains both namespace and localname e.g. {http://www.plcopen.org/xml/tc6_0200}fileHeader
          elem_tag_data = lxml.etree.QName(elem.tag)
          # do not include namespace as part of child_dirname
          child_dirname = child_counter_str + elem_tag_data.localname

      # concatenate parent_dirpath with child_dirpath if parent exists
      if elem.getparent() is None:
        child_dirpath = child_dirname
      else:
        child_dirpath = os.path.join(parent_dirpath, child_dirname)

      logger.debug('child_dirpath = ' + child_dirpath + ', child_counter = ' + str(child_counter))
      child_counter += 1

      try:
        os.mkdir(child_dirpath)
      except OSError as os_err:
        logger.debug(os_err)

      tag_filepath = os.path.join(child_dirpath, 'tag.txt')
      with open(tag_filepath, 'w') as tag_file:
        if elem.tag:
          tag_file.write(elem.tag)
        else:
          # this should never happen since tag should always exists
          raise ValueError('elem.tag is empty!')

      attrib_filepath = os.path.join(child_dirpath, 'attrib.txt')
      with open(attrib_filepath, 'w') as attrib_file:
        # need to set indent otherwise all attributes on single line
        json.dump(dict(elem.attrib), attrib_file, indent=2)

      nsmap_filepath = os.path.join(child_dirpath, 'nsmap.txt')
      with open(nsmap_filepath, 'w') as nsmap_file:
        # need to set indent otherwise all mappings on single line
        json.dump(elem.nsmap, nsmap_file, indent=2)

      # not actually used when recreating xml
      prefix_filepath = os.path.join(child_dirpath, 'prefix.txt')
      with open(prefix_filepath, 'w') as prefix_file:
        # writing only works if data exists
        if elem.prefix:
          prefix_file.write(elem.prefix)

      text_filepath = os.path.join(child_dirpath, 'text.txt')
      with open(text_filepath, 'w') as text_file:
        # writing only works if data exists
        if elem.text:
          text_file.write(elem.text)

      tail_filepath = os.path.join(child_dirpath, 'tail.txt')
      with open(tail_filepath, 'w') as tail_file:
        # writing only works if data exists
        if elem.tail:
          tail_file.write(elem.tail)

      # recursively create directory for child elements
      create_dirs_and_files(elem.getchildren(), child_dirpath)

  # project_root_elem needs to be placed in a list for recursion to work
  create_dirs_and_files([project_root_elem])

  # # XPath expressions at https://www.w3schools.com/xml/xpath_syntax.asp
  # # return child element that contains 'projectstructure' in name attribute
  # project_structure_list = project_tree.xpath("//*[contains(@name, 'projectstructure')]")
  # if len(project_structure_list) != 1:
    # for elem in project_structure_list:
      # logger.debug(elem)
    # raise ValueError('There is more than one element with \'projectstructure\' in its name attribute!') 

  # def create_project_structure(elem_list):
    # for elem in elem_list:
      # print(elem.attrib)
      # print(elem.tag)
      # create_project_structure(elem.findall('.{*}*')

  # project_structure_elem = project_structure_list[0]
  # # use wildcard to get list of child elements in project structure (but limited to one level deep)
  # create_project_structure(project_structure_elem.findall('.{*}*'))

  # parser = argparse.ArgumentParser(
      # description='Exports CODESYS .project as PLCopenXML and saves it as .projectarchive',
      # formatter_class=CustomFormatter)
  # parser.add_argument('-d', '--debug', default=False, type=bool, help='Enable debugging messages')
  # required_arg_group = parser.add_argument_group('required arguments')
  # required_arg_group.add_argument('-p',
                                  # '--projectPath',
                                  # type=str,
                                  # required=True,
                                  # help='Path to CODESYS .project')
  # required_arg_group.add_argument('-x',
                                  # '--xmlPath',
                                  # type=str,
                                  # required=True,
                                  # help='Path to export CODESYS PLCopenXML')
  # required_arg_group.add_argument('-a',
                                  # '--archivePath',
                                  # type=str,
                                  # required=True,
                                  # help='Path to save CODESYS .projectarchive')

  # logger = init_logger()

  # args = parser.parse_args(argv)
  # if args.debug is True:
    # logger.addHandler(debug_handler)
    # logger.setLevel(logging.DEBUG)

  # project_path = os.path.abspath(args.projectPath)
  # if not os.path.isfile(project_path):
    # raise IOError(project_path + ' is not a valid file!')

  # xml_path = os.path.abspath(args.xmlPath)
  # if os.path.splitext(os.path.basename(xml_path))[1] != ".xml":
    # raise ValueError(xml_path + ' does not contain .xml extension!')

  # archive_path = os.path.abspath(args.archivePath)
  # if os.path.splitext(os.path.basename(archive_path))[1] != ".projectarchive":
    # raise ValueError(archive_path + ' does not contain .projectarchive extension!')

  # codesys_proj = projects.open(project_path)
  # logger.info("Opened " + project_path + " !")

  # logger.info("Opened " + project_path + " !")

  # # use recursive argument for .get_children() instead of that for .export_xml() since the latter does not seem to work for directories at root level
  # codesys_proj.export_xml(objects=codesys_proj.get_children(recursive=True),
                          # path=xml_path,
                          # export_folder_structure=True,
                          # declarations_as_plaintext=True)
  # logger.info("Exported " + xml_path + " !")

  # codesys_proj.save_archive(archive_path)
  # logger.info("Saved " + archive_path + " !")

if __name__ == "__main__":
  main(sys.argv[1:])

