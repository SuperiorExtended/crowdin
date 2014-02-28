#!/usr/bin/python2
#
# cm_crowdin_sync.py
#
# Updates Crowdin source translations and pulls translations
# directly to CyanogenMod's Git.
#
# Copyright (C) 2014 The CyanogenMod Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import git
import mmap
import os
import os.path
import re
import shutil
import subprocess
import sys
from urllib import urlretrieve
from xml.dom import minidom

def get_caf_additions(strings_base, strings_cm):
    # Load AOSP file and resources
    xml_base = minidom.parse(strings_base)
    list_base_string = xml_base.getElementsByTagName('string')
    list_base_string_array = xml_base.getElementsByTagName('string-array')
    list_base_plurals = xml_base.getElementsByTagName('plurals')
    # Load CM file and resources
    xml_cm = minidom.parse(strings_cm)
    list_cm_string = xml_cm.getElementsByTagName('string')
    list_cm_string_array = xml_cm.getElementsByTagName('string-array')
    list_cm_plurals = xml_cm.getElementsByTagName('plurals')

    # All names from CM
    names_cm_string = []
    names_cm_string_array = []
    names_cm_plurals = []
    # All names from AOSP
    names_base_string = []
    names_base_string_array = []
    names_base_plurals = []

    # Get all names from CM
    for s in list_cm_string :
        if not s.hasAttribute('translatable') and not s.hasAttribute('translate'):
            names_cm_string.append(s.attributes['name'].value)
    for s in list_cm_string_array :
        if not s.hasAttribute('translatable') and not s.hasAttribute('translate'):
            names_cm_string_array.append(s.attributes['name'].value)
    for s in list_cm_plurals :
        if not s.hasAttribute('translatable') and not s.hasAttribute('translate'):
            names_cm_plurals.append(s.attributes['name'].value)
    # Get all names from AOSP
    for s in list_base_string :
        if not s.hasAttribute('translatable') and not s.hasAttribute('translate'):
            names_base_string.append(s.attributes['name'].value)
    for s in list_base_string_array :
        if not s.hasAttribute('translatable') and not s.hasAttribute('translate'):
            names_base_string_array.append(s.attributes['name'].value)
    for s in list_base_plurals :
        if not s.hasAttribute('translatable') and not s.hasAttribute('translate'):
            names_base_plurals.append(s.attributes['name'].value)

    # Store all differences in this list
    caf_additions = []

    # Add all CAF additions to the list 'caf_additions'
    for z in names_cm_string:
        if not z in names_base_string:
            caf_additions.append('    ' + list_cm_string[names_cm_string.index(z)].toxml())
    for z in names_cm_string_array:
        if not z in names_base_string_array:
            caf_additions.append('    ' + list_cm_string_array[names_cm_string_array.index(z)].toxml())
    for z in names_cm_plurals:
        if not z in names_base_plurals:
            caf_additions.append('    ' + list_cm_plurals[names_cm_plurals.index(z)].toxml())

    # Done :-)
    return caf_additions

def push_as_commit(path, name):
    # Get path
    path = os.getcwd() + '/' + path

    # Create git commit
    repo = git.Repo(path)
    repo.git.add(path)
    try:
        repo.git.commit(m='DO NOT MERGE: Automatic translation import test commit')
#        repo.git.push('ssh://cobjeM@review.cyanogenmod.org:29418/' + name, 'HEAD:refs/for/cm-11.0')
        print 'Succesfully pushed commit for ' + name
    except:
        # If git commit fails, it's probably because of no changes.
        # Just continue.
        print 'No commit pushed (probably empty?) for ' + name
        print 'WARNING: If the repository name was not obtained from default.xml, the name might be wrong!'

print('Welcome to the CM Crowdin sync script!')

print('\nSTEP 0: Checking dependencies')
if subprocess.check_output(['rvm', 'all', 'do', 'gem', 'list', 'crowdin-cli', '-i']) == 'true':
    sys.exit('You have not installed crowdin-cli. Terminating.')
else:
    print('Found: crowdin-cli')
if not os.path.isfile('caf.xml'):
    sys.exit('You have no caf.xml. Terminating.')
else:
    print('Found: caf.xml')
if not os.path.isfile('default.xml'):
    sys.exit('You have no default.xml. Terminating.')
else:
    print('Found: default.xml')

print('\nSTEP 1: Create cm_caf.xml')
# Load caf.xml
xml = minidom.parse('caf.xml')
items = xml.getElementsByTagName('item')

# Store all created cm_caf.xml files in here.
# Easier to remove them afterwards, as they cannot be committed
cm_caf = []

for item in items:
    # Create tmp dir for download of AOSP base file
    path_to_values = item.attributes["path"].value
    subprocess.call(['mkdir', '-p', 'tmp/' + path_to_values])
    # Create cm_caf.xml - header
    f = open(path_to_values + '/cm_caf.xml','w')
    f.write('<?xml version="1.0" encoding="utf-8"?>\n')
    f.write('<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">\n')
    # Create cm_caf.xml - contents
    # This means we also support multiple base files (e.g. checking if strings.xml and arrays.xml are changed)
    contents = []
    item_aosp = item.getElementsByTagName('aosp')
    for aosp_item in item_aosp:
        url = aosp_item.firstChild.nodeValue
        xml_file = aosp_item.attributes["file"].value
        path_to_base = 'tmp/' + path_to_values + '/' + xml_file
        path_to_cm = path_to_values + '/' + xml_file
        urlretrieve(url, path_to_base)
        contents = contents + get_caf_additions(path_to_base, path_to_cm)
    for addition in contents:
        f.write(addition + '\n')
    # Create cm_caf.xml - the end
    f.write('</resources>')
    f.close()
    cm_caf.append(path_to_values + '/cm_caf.xml')
    print('Created ' + path_to_values + '/cm_caf.xml')

print('\nSTEP 2: Upload Crowdin source translations')
# Execute 'crowdin-cli upload sources' and show output
print(subprocess.check_output(['crowdin-cli', 'upload', 'sources']))

print('STEP 3: Download Crowdin translations')
# Execute 'crowdin-cli download' and show output
print(subprocess.check_output(['crowdin-cli', "download"]))

print('STEP 4A: Clean up of source cm_caf.xmls')
# Remove all cm_caf.xml files, which you can find in the list 'cm_caf'
for cm_caf_file in cm_caf:
    print ('Removing ' + cm_caf_file)
    os.remove(cm_caf_file)

print('\nSTEP 4B: Clean up of temp dir')
# We are done with cm_caf.xml files, so remove tmp/
shutil.rmtree(os.getcwd() + '/tmp')

print('\nSTEP 4C: Clean up of empty translations')
# Some line of code that I found to find all XML files
result = [os.path.join(dp, f) for dp, dn, filenames in os.walk(os.getcwd()) for f in filenames if os.path.splitext(f)[1] == '.xml']
for xml_file in result:
    # We hate empty, useless files. Crowdin exports them with <resources/> (sometimes with xliff).
    # That means: easy to find
    if '<resources/>' in open(xml_file).read():
        print ('Removing ' + xml_file)
        os.remove(xml_file)
    elif '<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2"/>' in open(xml_file).read():
        print ('Removing ' + xml_file)
        os.remove(xml_file)    

print('\nSTEP 5: Push translations to Git')
# Get all files that Crowdin pushed
proc = subprocess.Popen(['crowdin-cli', 'list', 'sources'],stdout=subprocess.PIPE)
xml = minidom.parse('default.xml')
items = xml.getElementsByTagName('project')
all_projects = []

for path in iter(proc.stdout.readline,''):
    # Remove the \n at the end of each line
    path = path.rstrip()
    # Get project root dir from Crowdin's output
    m = re.search('/(.*Superuser)/Superuser.*|/(.*LatinIME).*|/(frameworks/base).*|/(.*CMFileManager).*|/(device/.*/.*)/.*/res/values.*|/(hardware/.*/.*)/.*/res/values.*|/(.*)/res/values.*', path)
    for good_path in m.groups():
        # When a project has multiple translatable files, Crowdin will give duplicates.
        # We don't want that (useless empty commits), so we save each project in all_projects
        # and check if it's already in there.
        if good_path is not None and not good_path in all_projects:
            all_projects.append(good_path)
            working = 'false'
            for project_item in items:
                # We need to have the Github repository for the git push url. Obtain them from
                # default.xml based on the project root dir.
                if project_item.attributes["path"].value == good_path:
                    working = 'true'
                    push_as_commit(good_path, project_item.attributes['name'].value)
                    print 'Committing ' + project_item.attributes['name'].value + ' (based on default.xml)'
            # We also translate repositories that are not downloaded by default (e.g. device parts).
            # This is just a fallback.
            # WARNING: If the name is wrong, this will not stop the script.
            if working == 'false':
                push_as_commit(good_path, 'CyanogenMod/android_' + good_path.replace('/', '_'))
                print 'Committing ' + project_item.attributes['name'].value + ' (workaround)'

print('STEP 6: Done!')