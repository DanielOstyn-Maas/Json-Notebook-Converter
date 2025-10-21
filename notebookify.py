import argparse
import json
from json import *
import sys
from pathlib import Path
import os



LOCAL_NOTEBOOK_FILE_ENDING = "_LOCAL.ipynb"
JSON_METADATA_FILE_ENDING = "_METADATA.json"

def exportMetadata(fileName, metadata):
    fileName = Path(fileName.split('.')[0] + JSON_METADATA_FILE_ENDING)
    print(f"Writing to {fileName}")
    try:
        with open(fileName, 'w', newline="\n") as file:
            json.dump(metadata, file, indent='\t', sort_keys=False)
    except:
        print("error writing metadata file")


def exportNotebook(fileName, cells):
    notebook = {"metadata":{}, "cells": cells}
    fileName = Path(fileName.split('.')[0] + LOCAL_NOTEBOOK_FILE_ENDING)
    print(f"Writing to {fileName}")
    try:
        with open(fileName, 'w', newline="\n") as file:
            json.dump(notebook, file, indent='\t', sort_keys=False)
    except:
        print("error writing to notebook file")


def exportJson(fileName, synapseJson):
    fileName = Path(fileName)
    print(f"Writing to {fileName}")
    try:
        with open(fileName, 'w', newline="\n") as file:
            json.dump(synapseJson, file, indent='\t', sort_keys=False)
    except:
        print(f"error writing to json file {fileName}")


def importJson(fileName):
    try:
        with open(fileName, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"File '{fileName}' not found. Please provide the correct file path.")
        sys.exit()


def cleanupCells(cells):
    newCells = []
    for cell in cells:
        if cell['cell_type'] == 'code':
            #remove fields that aren't synapse-friendly before we convert to synapse json
            cell['outputs'] = []
            cell.pop('outputs')
            cell['id'] = []
            cell.pop('id')
        #clear empty metadata fields to simplify diff
        if cell['metadata'] == {} and not cell['metadata'].keys():
            cell.pop('metadata')
        #normalize line endings
        modifiedLines = []
        for line in cell['source']:
                    #print(repr(line))
            modifiedLine = line.replace("""\r\n""","""\n""")
            modifiedLine = modifiedLine.replace("""\n""","""\r\n""")
                    #print(repr(modifiedLine))
            modifiedLines.append(modifiedLine)
        #Synapse allows the last line of a code cell to be an empty string, VSCode does not. 
        if cell['cell_type'] == 'code': 
            if modifiedLines == []:
                modifiedLines.append("")
            #We previously swapped it for a single space, so swap it back now.
            elif (modifiedLines[-1] == " "):
                modifiedLines[-1] = ""
        cell['source'] = modifiedLines

        newCell = {
            'cell_type': cell.pop('cell_type')
        }
        #VSCode automatically alphabetizes json keys after editing a json file. (annoying, but understandable.)
        #Synapse keeps them in a logical order instead (sources before outputs, etc.)
        #This tries to re-order things to match synapse.
        if 'metadata' in cell.keys():
            newCell['metadata'] = eval('''{"jupyter": {"source_hidden": False,"outputs_hidden": False},"nteract": {"transient": {"deleting": False}},"collapsed": False},''')
            #newCell['metadata'] = eval('''{"acollapsed": False, "jupyter": {"asource_hidden": False,"outputs_hidden": False},"nteract": {"transient": {"deleting": False}}},''')

        newCell['source'] = cell.pop('source')
        if 'execution_count' in cell.keys():
            newCell['execution_count'] = cell.pop('execution_count')
        for key in cell.keys():
            newCell[key] = cell[key]
        newCells.append(newCell)
    return newCells

def dealphabetizeJsonKeys(fileName):
    fileName = Path(fileName)
    print(f"Dealphabetizing {fileName}")
    try:
        lines = []
        with open(fileName, 'r', newline="\n") as file:
            print("not implemented")
            #read in line by line
            #lines.append(line.replace('acollapsed', 'collapsed').replace('asource_hidden','source_hidden'))
    except:
        print(f"error writing to json file {fileName}")


def jsonifyNotebooks():
    print(f"searching for LOCAL files in {os.getcwd()}")

    allFiles = os.listdir('.')
    localFiles = [file for file in allFiles if file.endswith(LOCAL_NOTEBOOK_FILE_ENDING)]
    metaFiles = [file for file in allFiles if file.endswith(JSON_METADATA_FILE_ENDING)]

    for localFile in localFiles:
        origFileName = localFile[0:-len(LOCAL_NOTEBOOK_FILE_ENDING)]
        metaFile = origFileName + JSON_METADATA_FILE_ENDING

        if metaFile in metaFiles:
            notebook = importJson(localFile)
            metaJson = importJson(metaFile)
            name = ''
            print(notebook.keys())
            print(metaJson.keys())
            if 'name' not in metaJson.keys():
                metaJson['name'] = origFileName
                print(f'No name field for {localFile}. Generating from filename.')

            if 'properties' not in metaJson.keys():
                print("error: no properties found on metadata object")
                continue

            metaJson['properties']['cells'] = cleanupCells(notebook['cells'])

            exportJson(origFileName + ".json", metaJson)
        else:
            print(f"missing metadata file for {origFileName}. Skipping")
            continue


##Program Start Point
i = 0
if len(sys.argv) == 1:
    print("USAGE:\n\tpython notebookify.py [json_file_1] [json_file_2] ... ")
    print("Or to convert notebooks to json:\n\tpython notebookify.py -j")
    print("\tThis will combine each file named *_LOCAL.ipynb with its _METADATA.json file")
elif (len(sys.argv) > 1 and sys.argv[1].startswith('-j')):
    jsonifyNotebooks()
    sys.exit()

workingDirFiles = os.listdir('.')
for arg in sys.argv:
    if i > 0: 
        existingLocalNotebook = arg.split('.')[0] + LOCAL_NOTEBOOK_FILE_ENDING
        if existingLocalNotebook in workingDirFiles:
            print(f"Warning! This process will replace {existingLocalNotebook}.")
            goOn = input("Do you wish to continue? (y/n):")
            #anything but yes we skip this file.
            if not goOn.lower().startswith('y'):
                continue #ironically, continuing the loop means skipping the file.

        if arg.endswith(JSON_METADATA_FILE_ENDING):
            print(f"METADATA file {arg} found. Skipping.")
            continue
        currentJson = importJson(arg)

        cells = currentJson['properties'].pop('cells')
        for cell in cells:
            if 'metadata' not in cell.keys():
                cell['metadata'] = {}
            #VSCode (again, reasonably) strips an empty-string row from the end of code cells. Synapse does not. This makes VSCode leave it alone.
            if "source" in cell.keys() and cell["source"] and cell["source"][-1] == "":
                cell["source"][-1] = " "
        #cells go to the notebook object, everything else to the metadata object
        exportMetadata(arg, currentJson)
        exportNotebook(arg, cells)

    else:
        i += 1



# def get_local_ipynb_files():
#     return [f for f in os.listdir('.') if f.endswith('_LOCAL.ipynb')]

# def main():
#     parser = argparse.ArgumentParser(description="Process JSON or _LOCAL.ipynb files.")
#     parser.add_argument('-jsonify', action='store_true', help='Switch to processing _LOCAL.ipynb files')
#     parser.add_argument('files', nargs='*', help='List of files to process')

#     args = parser.parse_args()

#     if args.jsonify:
#         if args.files:
#             files_to_process = [f for f in args.files if f.endswith('_LOCAL.ipynb')]
#         else:
#             files_to_process = get_local_ipynb_files()
#     else:
#         files_to_process = args.files

#     if not files_to_process:
#         print("No valid files provided.")
#         sys.exit(1)

#     print("Files to process:")
#     for file in files_to_process:
#         print(f" - {file}")

# if __name__ == "__main__":
#     main()
