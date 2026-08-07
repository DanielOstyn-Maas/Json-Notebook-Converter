import argparse
import json
from json import *
import sys
from pathlib import Path
import os



LOCAL_NOTEBOOK_FILE_ENDING = "_LOCAL.ipynb"
JSON_METADATA_FILE_ENDING = "_METADATA.json"
#the same markers without their extensions, so a target typed as "Name_LOCAL" still resolves
LOCAL_NOTEBOOK_MARKER = "_LOCAL"
JSON_METADATA_MARKER = "_METADATA"


def confirm(question, assumeYes=False):
    #input() raises EOFError when there is no terminal attached (piped/scripted runs),
    #so treat that as "no" rather than blowing up mid-conversion.
    if assumeYes:
        return True
    try:
        answer = input(question)
    except EOFError:
        print("\nNo interactive terminal available to answer that. Re-run with -y/--yes (or name the files explicitly) to proceed.")
        return False
    return answer.lower().startswith('y')


def resolveTarget(target):
    """Resolve a loosely typed file argument into the trio of paths it refers to.
    'Name', 'Name.json', 'Name_LOCAL.ipynb', 'Name_METADATA.json' and any of those
    with a directory in front all resolve to the same (json, notebook, metadata) set."""
    path = Path(target)
    name = path.name
    if not name:
        return None
    #longest/most specific endings first: _LOCAL.ipynb must win over .ipynb
    for ending in (LOCAL_NOTEBOOK_FILE_ENDING, JSON_METADATA_FILE_ENDING,
                   LOCAL_NOTEBOOK_MARKER, JSON_METADATA_MARKER, ".json", ".ipynb"):
        if name.endswith(ending) and len(name) > len(ending):
            name = name[:-len(ending)]
            break
    base = str(path.with_name(name))
    return (Path(base + ".json"),
            Path(base + LOCAL_NOTEBOOK_FILE_ENDING),
            Path(base + JSON_METADATA_FILE_ENDING))


def exportMetadata(metadataPath, metadata):
    print(f"Writing to {metadataPath}")
    try:
        with open(metadataPath, 'w', newline="\n") as file:
            json.dump(metadata, file, indent='\t', sort_keys=False)
    except:
        print("error writing metadata file")


def exportNotebook(notebookPath, cells):
    notebook = {"metadata":{}, "cells": cells}
    print(f"Writing to {notebookPath}")
    try:
        with open(notebookPath, 'w', newline="\n") as file:
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
        #remove fields that aren't synapse-friendly before we convert to synapse json
        cell['id'] = []
        cell.pop('id')
        cell['outputs'] = []
        cell.pop('outputs')
        #clear empty metadata fields to simplify diff
        if cell['metadata'] == {} and not cell['metadata'].keys():
            cell.pop('metadata')
        #NotebookEdit (and some editors) can store a cell's source as a single string
        #instead of a list of lines. Iterating a string yields characters, which would
        #split the cell 1 char per line below. Normalize to a list of lines first.
        if isinstance(cell['source'], str):
            cell['source'] = cell['source'].splitlines(keepends=True)
        #normalize line endings
        modifiedLines = []
        for line in cell['source']:
                    #print(repr(line))
            modifiedLine = line.replace("""\r\n""","""\n""")
            modifiedLine = modifiedLine.replace("""\n""","""\r\n""")
                    #print(repr(modifiedLine))
            modifiedLines.append(modifiedLine)
        #Synapse allows the last line of a code cell to be an empty string, VSCode does not.
        # VSCode represents an empty code cell as having no lines, but Synapse prefers to include a single empty string line. #smh
        if cell['cell_type'] == 'code':
            if modifiedLines == []:
                modifiedLines.append("")
            #Synapse allows the last line of a code cell to be an empty string, VSCode does not.
            #We previously swapped trailing empty lines for a single space, so swap it back now.
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


def collectNamedPairs(targets):
    """Resolve explicitly named jsonify targets. Every target must exist as a complete
    pair; if any of them doesn't we write nothing at all, so a typo can't half-run."""
    pairs = []
    seen = set()
    problems = []
    for target in targets:
        resolved = resolveTarget(target)
        if resolved is None:
            problems.append(f"'{target}' is not a file name")
            continue
        jsonPath, localPath, metaPath = resolved
        if not localPath.exists():
            problems.append(f"'{target}': no notebook file at {localPath}")
            continue
        if not metaPath.exists():
            problems.append(f"'{target}': found {localPath} but no metadata file at {metaPath}")
            continue
        key = str(jsonPath.resolve())
        if key in seen:
            continue
        seen.add(key)
        pairs.append((jsonPath, localPath, metaPath))

    if problems:
        print("error: could not resolve every target, so nothing was written:")
        for problem in problems:
            print(f"\t{problem}")
        sys.exit(1)
    return pairs


def discoverPairs():
    """Find every _LOCAL.ipynb / _METADATA.json pair in the working directory."""
    print(f"searching for LOCAL files in {os.getcwd()}")
    allFiles = os.listdir('.')
    localFiles = [file for file in allFiles if file.endswith(LOCAL_NOTEBOOK_FILE_ENDING)]
    metaFiles = [file for file in allFiles if file.endswith(JSON_METADATA_FILE_ENDING)]

    pairs = []
    for localFile in localFiles:
        origFileName = localFile[0:-len(LOCAL_NOTEBOOK_FILE_ENDING)]
        metaFile = origFileName + JSON_METADATA_FILE_ENDING
        if metaFile not in metaFiles:
            print(f"missing metadata file for {origFileName}. Skipping")
            continue
        pairs.append((Path(origFileName + ".json"), Path(localFile), Path(metaFile)))
    return pairs


def jsonifyNotebook(jsonPath, localPath, metaPath):
    notebook = importJson(localPath)
    metaJson = importJson(metaPath)

    if 'name' not in metaJson.keys():
        metaJson['name'] = jsonPath.stem
        print(f'No name field for {localPath}. Generating from filename.')

    if 'properties' not in metaJson.keys():
        print(f"error: no properties found on metadata object in {metaPath}")
        return

    metaJson['properties']['cells'] = cleanupCells(notebook['cells'])

    exportJson(jsonPath, metaJson)


def jsonifyNotebooks(targets=None, assumeYes=False):
    if targets:
        pairs = collectNamedPairs(targets)
    else:
        pairs = discoverPairs()
        #with no arguments we're rewriting whatever happens to be lying around, which is
        #easy to do by accident when several notebooks are checked out at once.
        if len(pairs) > 1:
            print("These json files will be rewritten from the local notebooks in this directory:")
            for jsonPath, _, _ in pairs:
                print(f"\t{jsonPath}")
            if not confirm("Rewrite all of them? (y/n):", assumeYes):
                print("Nothing written. Name the notebooks you want (e.g. 'jsonify Aggregation') to rewrite only those.")
                return

    if not pairs:
        print("No _LOCAL.ipynb / _METADATA.json pairs found.")
        return

    for jsonPath, localPath, metaPath in pairs:
        jsonifyNotebook(jsonPath, localPath, metaPath)


def notebookifyJsonFiles(targets, assumeYes=False):
    for target in targets:
        if Path(target).name.endswith(JSON_METADATA_FILE_ENDING):
            print(f"METADATA file {target} found. Skipping.")
            continue

        resolved = resolveTarget(target)
        if resolved is None:
            print(f"'{target}' is not a file name. Skipping.")
            continue
        jsonPath, localPath, metaPath = resolved

        if localPath.exists():
            print(f"Warning! This process will replace {localPath}.")
            #anything but yes we skip this file.
            if not confirm("Do you wish to continue? (y/n):", assumeYes):
                continue

        currentJson = importJson(jsonPath)

        cells = currentJson['properties'].pop('cells')
        for cell in cells:
            if 'metadata' not in cell.keys():
                cell['metadata'] = {}
            #VSCode (again, reasonably) strips an empty-string row from the end of code cells. Synapse does not. This makes VSCode leave it alone.
            if "source" in cell.keys() and cell["source"] and cell["source"][-1] == "":
                cell["source"][-1] = " "
        #cells go to the notebook object, everything else to the metadata object
        exportMetadata(metaPath, currentJson)
        exportNotebook(localPath, cells)


def buildParser():
    parser = argparse.ArgumentParser(
        prog="notebookify.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Convert Azure Synapse notebook json into editable .ipynb notebooks and back again.",
        epilog="""examples:
  notebookify Aggregation.json            split into Aggregation_LOCAL.ipynb + Aggregation_METADATA.json
  notebookify *.json                      split every notebook in the folder
  jsonify                                 recombine every pair in the working directory (asks first if there's more than one)
  jsonify Aggregation                     recombine just that pair; 'Aggregation.json' and
                                          'Aggregation_LOCAL.ipynb' name the same pair
  jsonify notebook/Aggregation DatabaseUtils
                                          several targets at once, in any directory""")
    parser.add_argument('-j', '-jsonify', '--jsonify', dest='jsonify', action='store_true',
                        help="recombine _LOCAL.ipynb + _METADATA.json pairs back into synapse json")
    parser.add_argument('-y', '--yes', action='store_true',
                        help="answer yes to every prompt (for non-interactive use)")
    parser.add_argument('files', nargs='*',
                        help="files to process. Without -j these are synapse .json notebooks. "
                             "With -j they name the pairs to recombine, and may be given as 'Name', "
                             "'Name.json' or 'Name_LOCAL.ipynb'. Omit to process every pair in the working directory.")
    return parser


def main(argv):
    parser = buildParser()
    args = parser.parse_args(argv)

    if args.jsonify:
        jsonifyNotebooks(args.files, assumeYes=args.yes)
        return

    if not args.files:
        parser.print_help()
        return

    notebookifyJsonFiles(args.files, assumeYes=args.yes)


if __name__ == "__main__":
    main(sys.argv[1:])
