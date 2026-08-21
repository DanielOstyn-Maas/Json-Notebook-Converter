# Json-Notebook-Converter (notebookify.py)
A small script to convert between jupyter notebooks (.ipynb) and their Azure Synapse equivalent json file. 
Designed to help minimize diff static between locally edited commits and commits coming from the Synapse web editor, meaning cleaner, more readable pull requests.   

## Installation and Aliasing
Save the script to your machine, ideally somewhere the path won't change.

### Bash or Git Bash
Add this to your `bash.rc` file, or your `aliases.sh` file, for git bash:

    alias notebookify='python C:/Path/To/Script/notebookify.py'

### Powershell
Run this to open your powershell profile script:
```powershell
notepad $PROFILE
```
Add this to the script and save it.
```powershell
function notebookify {
    & python "C:/Path/To/Script/notebookify.py" @args
}
```

Then it's just `notebookify` instead of `python notebookify.py` to use.

A second alias for the reverse direction is handy too - make sure any extra arguments are forwarded
after the `-j`:

```powershell
function jsonify { python "C:/Path/To/Script/notebookify.py" -j @args }
```

## Usage

#### Synapse json to .ipynb:

    notebookify file1.json file2.json file3.json ...
This will create a `[filename]_LOCAL.ipynb` file, which you can edit in your IDE of choice.
Or, to convert every notebook in the folder (could be a little excessive):

    notebookify *.json

#### .ipynb notebooks to synapse json:

    notebookify -j
 This will convert all `_LOCAL.ipynb` files in the current directory back to `[filename].json`, ready to git add, commit, and push.
 With no names it lists the json files it is about to rewrite and asks first (when there's more than
 one), so a stale `_LOCAL.ipynb` sitting in the folder can't quietly clobber a notebook you weren't
 working on. Add `-y` to skip that prompt in scripts.

Or name just the notebooks you want:

    notebookify -j Aggregation

The name can be given in whatever form is handy - `Aggregation`, `Aggregation.json` and
`Aggregation_LOCAL.ipynb` all mean the same pair, and a path works too:

    notebookify -j notebook/Aggregation notebook/DatabaseUtils_LOCAL.ipynb

If a named notebook has no matching `_METADATA.json` the script says so and writes nothing at all,
rather than half-processing the list.
 
#### Fabric notebook source to .ipynb:

    notebookify -f notebook-content.py

Microsoft Fabric's git integration stores each notebook as a `notebook-content.py` inside a
`[DisplayName].Notebook` folder, with the cells separated by `# CELL ********************` banner
comments. `-f` turns one of those files into a standalone, fully valid `.ipynb`.

Since every one of those files is named `notebook-content.py`, the output is named from the
`displayName` in the sibling `.platform` file (falling back to the folder name), so the example
above writes `[DisplayName]_LOCAL.ipynb` next to the source. You can also just name the folder:

    notebookify -f DimClusterLoad.Notebook

Markdown cells are un-commented, `%%sql` and other magic cells have their `# MAGIC ` prefixes
stripped, parameters cells keep a `parameters` tag, and the Fabric metadata (lakehouse
dependencies, per-cell language) is preserved in the notebook's own `metadata` fields. Unlike the
synapse path there's no `_METADATA.json` sidecar - the `.ipynb` holds everything.

Note this direction is one-way for now: there's no converter back from `.ipynb` to
`notebook-content.py`, so treat the result as read-only-ish, for reading and diffing rather than
as the file you edit and commit.

## Git Ignore
When converting to ipynb, the script saves synapse-specific metadata (spark configuration and the like) as `[filename]_METADATA.json`. 
If you wish you can include the following lines in your `.gitignore` to easily keep these out of the repo:

    *_LOCAL.ipynb
    *_METADATA.json

## File Creation
If you want to create a new notebook you should still create and commit it through the Synapse Analytics web editor. Synapse tracks a bunch of fields in the metadata that VSCode won't know to populate (and will actively meddle with if allowed).
