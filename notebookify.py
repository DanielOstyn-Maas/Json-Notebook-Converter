import argparse
import json
import re
from json import *
import sys
from pathlib import Path
import os



LOCAL_NOTEBOOK_FILE_ENDING = "_LOCAL.ipynb"
JSON_METADATA_FILE_ENDING = "_METADATA.json"
#the same markers without their extensions, so a target typed as "Name_LOCAL" still resolves
LOCAL_NOTEBOOK_MARKER = "_LOCAL"
JSON_METADATA_MARKER = "_METADATA"

#Fabric git integration stores each notebook as a 'notebook-content.py' in a
#'<DisplayName>.Notebook' folder, next to a '.platform' file holding the display name.
FABRIC_SOURCE_FILE_NAME = "notebook-content.py"
FABRIC_PLATFORM_FILE_NAME = ".platform"
FABRIC_NOTEBOOK_FOLDER_ENDING = ".Notebook"
FABRIC_HEADER = "# Fabric notebook source"
FABRIC_META_PREFIX = "# META "
FABRIC_MAGIC_MARKER = "# MAGIC"
FABRIC_MAGIC_PREFIX = "# MAGIC "
FABRIC_COMMENT_PREFIX = "# "
#cells are separated by banner comments like '# CELL ********************'
FABRIC_MARKER_PATTERN = re.compile(r"^# (CELL|MARKDOWN|PARAMETERS CELL|METADATA) \*+\s*$")


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


def resolveFabricSource(target):
    """Resolve a fabric target to the notebook-content.py file it refers to.
    Fabric git integration stores every notebook as 'notebook-content.py' inside a
    '<DisplayName>.Notebook' folder, so the folder is just as natural a thing to name
    as the file itself."""
    path = Path(target)
    if path.is_dir():
        candidate = path / FABRIC_SOURCE_FILE_NAME
        if not candidate.exists():
            return None
        return candidate
    return path


def fabricNotebookName(sourcePath):
    """Work out what to call the notebook. Every fabric source file is named
    'notebook-content.py', so the real name lives either in the sibling .platform
    file or in the '<DisplayName>.Notebook' folder holding it."""
    platformPath = sourcePath.parent / FABRIC_PLATFORM_FILE_NAME
    if platformPath.exists():
        try:
            with open(platformPath, 'r', encoding="utf-8") as file:
                platform = json.load(file)
            displayName = platform.get('metadata', {}).get('displayName')
            if displayName:
                return displayName
        except (ValueError, OSError):
            print(f"could not read a display name out of {platformPath}. Falling back to the folder name.")

    folderName = sourcePath.parent.name
    if folderName.endswith(FABRIC_NOTEBOOK_FOLDER_ENDING):
        return folderName[:-len(FABRIC_NOTEBOOK_FOLDER_ENDING)]
    return sourcePath.stem


def parseFabricMetaBlock(lines, sourceName):
    """A fabric METADATA block is json with every line prefixed by '# META '."""
    stripped = []
    for line in lines:
        if line.startswith(FABRIC_META_PREFIX):
            stripped.append(line[len(FABRIC_META_PREFIX):])
        elif line.rstrip() == FABRIC_META_PREFIX.rstrip():
            stripped.append("")
        elif line.strip():
            #a stray line inside a metadata block would break the json, so drop it loudly
            print(f"{sourceName}: unexpected line in a METADATA block, ignoring it: {line.strip()!r}")
    if not stripped:
        return {}
    try:
        return json.loads("\n".join(stripped))
    except ValueError as error:
        print(f"{sourceName}: could not parse a METADATA block ({error}). Using an empty one.")
        return {}


def splitFabricBlocks(lines):
    """Chop the file into (marker, body lines) blocks. Everything before the first
    marker is the '# Fabric notebook source' header, which carries no cell content."""
    blocks = []
    current = None
    for line in lines:
        match = FABRIC_MARKER_PATTERN.match(line)
        if match:
            current = (match.group(1), [])
            blocks.append(current)
            continue
        if current is not None:
            current[1].append(line)
    return blocks


def stripFormatPadding(lines):
    """Fabric puts exactly one blank line after each marker and one before the next one
    (for the last block, the file's own trailing newline stands in for the second).
    Strip just those two - blank lines beyond them are the author's own, and dropping
    them would put whitespace-only noise in the next diff, which is the whole thing
    this script exists to avoid."""
    if lines and not lines[0].strip():
        lines = lines[1:]
    if lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def toSourceList(lines):
    """nbformat wants source as a list of lines, each keeping its newline except the last."""
    if not lines:
        return []
    return [line + "\n" for line in lines[:-1]] + [lines[-1]]


def uncommentMarkdown(lines, sourceName):
    """Fabric comments out every line of a markdown cell with '# '."""
    uncommented = []
    warned = False
    for line in lines:
        if line.startswith(FABRIC_COMMENT_PREFIX):
            uncommented.append(line[len(FABRIC_COMMENT_PREFIX):])
        elif line.rstrip() == "#":
            uncommented.append("")
        else:
            if not warned:
                print(f"{sourceName}: a MARKDOWN line wasn't commented out, keeping it as-is: {line.strip()!r}")
                warned = True
            uncommented.append(line)
    return uncommented


def uncommentMagic(lines):
    """A fabric cell in a non-default language (%%sql and friends) has every line
    prefixed with '# MAGIC '. Returns None when this isn't one of those cells."""
    contentLines = [line for line in lines if line.strip()]
    if not contentLines or not all(line.startswith(FABRIC_MAGIC_MARKER) for line in contentLines):
        return None
    uncommented = []
    for line in lines:
        if line.startswith(FABRIC_MAGIC_PREFIX):
            uncommented.append(line[len(FABRIC_MAGIC_PREFIX):])
        elif line.startswith(FABRIC_MAGIC_MARKER):
            uncommented.append(line[len(FABRIC_MAGIC_MARKER):])
        else:
            uncommented.append("")
    return uncommented


def buildFabricCell(marker, bodyLines, sourceName):
    lines = stripFormatPadding(bodyLines)

    if marker == "MARKDOWN":
        return {
            'cell_type': 'markdown',
            'metadata': {},
            'source': toSourceList(uncommentMarkdown(lines, sourceName)),
        }

    magicLines = uncommentMagic(lines)
    if magicLines is not None:
        lines = magicLines

    cell = {
        'cell_type': 'code',
        'metadata': {},
        'source': toSourceList(lines),
        'outputs': [],
        'execution_count': None,
    }
    if marker == "PARAMETERS CELL":
        #the tag papermill and the wider notebook ecosystem use for a parameters cell
        cell['metadata']['tags'] = ['parameters']
    return cell


def fabricNotebookMetadata(fabricMeta):
    """Keep the fabric metadata verbatim so nothing is lost, and add the kernelspec and
    language_info that make this a complete nbformat notebook."""
    metadata = dict(fabricMeta)
    kernelName = fabricMeta.get('kernel_info', {}).get('name', 'synapse_pyspark')
    metadata['kernelspec'] = {
        'name': kernelName,
        'display_name': kernelName,
        'language': 'python',
    }
    metadata['language_info'] = {'name': 'python'}
    return metadata


def parseFabricNotebook(sourcePath):
    """Turn a fabric notebook-content.py into (notebook metadata, cells)."""
    try:
        with open(sourcePath, 'r', encoding="utf-8") as file:
            text = file.read()
    except OSError as error:
        print(f"error reading {sourcePath}: {error}")
        return None, []
    lines = text.replace("\r\n", "\n").split("\n")

    if not lines or not lines[0].startswith(FABRIC_HEADER):
        print(f"warning: {sourcePath} doesn't start with '{FABRIC_HEADER}'. Trying to parse it anyway.")

    sourceName = str(sourcePath)
    notebookMetadata = {}
    cells = []
    for marker, bodyLines in splitFabricBlocks(lines):
        if marker == "METADATA":
            metaBlock = parseFabricMetaBlock(bodyLines, sourceName)
            if cells:
                #a METADATA block sitting after a cell describes that cell
                cells[-1]['metadata'].update(metaBlock)
            else:
                #the first one, before any cell, describes the notebook
                notebookMetadata = metaBlock
            continue
        cells.append(buildFabricCell(marker, bodyLines, sourceName))

    return fabricNotebookMetadata(notebookMetadata), cells


def exportIpynb(notebookPath, metadata, cells):
    #unlike the synapse path this is a standalone notebook, so it carries the nbformat
    #version fields. nbformat_minor 4 rather than 5, since 5 wants an id on every cell.
    notebook = {
        'cells': cells,
        'metadata': metadata,
        'nbformat': 4,
        'nbformat_minor': 4,
    }
    print(f"Writing to {notebookPath}")
    try:
        with open(notebookPath, 'w', newline="\n", encoding="utf-8") as file:
            json.dump(notebook, file, indent='\t', sort_keys=False)
    except OSError as error:
        print(f"error writing to notebook file {notebookPath}: {error}")


def notebookifyFabricFiles(targets, assumeYes=False):
    for target in targets:
        sourcePath = resolveFabricSource(target)
        if sourcePath is None:
            print(f"'{target}' is a folder with no {FABRIC_SOURCE_FILE_NAME} in it. Skipping.")
            continue
        if not sourcePath.exists():
            print(f"File '{sourcePath}' not found. Skipping.")
            continue

        notebookPath = sourcePath.parent / (fabricNotebookName(sourcePath) + LOCAL_NOTEBOOK_FILE_ENDING)
        if notebookPath.exists():
            print(f"Warning! This process will replace {notebookPath}.")
            #anything but yes we skip this file.
            if not confirm("Do you wish to continue? (y/n):", assumeYes):
                continue

        metadata, cells = parseFabricNotebook(sourcePath)
        if not cells:
            print(f"No cells found in {sourcePath}. Is it a fabric notebook source file?")
            continue
        exportIpynb(notebookPath, metadata, cells)


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
                                          several targets at once, in any directory
  notebookify -f notebook-content.py      convert a fabric notebook source file into a
                                          standalone .ipynb, named from its .platform file
  notebookify -f DimClusterLoad.Notebook  naming the fabric notebook folder works too""")
    parser.add_argument('-j', '-jsonify', '--jsonify', dest='jsonify', action='store_true',
                        help="recombine _LOCAL.ipynb + _METADATA.json pairs back into synapse json")
    parser.add_argument('-f', '-fabric', '--fabric', dest='fabric', action='store_true',
                        help="treat the files as fabric notebook source (notebook-content.py) "
                             "and convert them into standalone .ipynb notebooks")
    parser.add_argument('-y', '--yes', action='store_true',
                        help="answer yes to every prompt (for non-interactive use)")
    parser.add_argument('files', nargs='*',
                        help="files to process. Without -j or -f these are synapse .json notebooks. "
                             "With -j they name the pairs to recombine, and may be given as 'Name', "
                             "'Name.json' or 'Name_LOCAL.ipynb'. Omit to process every pair in the working directory. "
                             "With -f they are fabric notebook-content.py files, or the "
                             "'<Name>.Notebook' folders holding them.")
    return parser


def main(argv):
    parser = buildParser()
    args = parser.parse_args(argv)

    if args.jsonify and args.fabric:
        parser.error("-j and -f convert in opposite directions, so they can't be combined.")

    if args.jsonify:
        jsonifyNotebooks(args.files, assumeYes=args.yes)
        return

    if not args.files:
        parser.print_help()
        return

    if args.fabric:
        notebookifyFabricFiles(args.files, assumeYes=args.yes)
        return

    notebookifyJsonFiles(args.files, assumeYes=args.yes)


if __name__ == "__main__":
    main(sys.argv[1:])
