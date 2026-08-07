# Json-Notebook-Converter (notebookify.py)
A small script to convert between valid jupyter python notebooks (.ipynb) and their Azure Synapse equivalent json file. 

## Installation
Save the script to your machine. Then you can either add its folder to your path variable or create an alias to it for easy access.

## Aliasing
### In git bash
Add this to your `aliases.sh` file:

    alias notebookify='python C:/Path/To/Script/notebookify.py'

### In Powershell
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

#### To convert synapse json files to valid notebooks:

    python notebookify.py file1.json file2.json file3.json ...

or to convert all (could be a little excessive):

    python notebookify.py *.json


#### To convert _LOCAL.ipynb notebooks back to synapse json:

Named notebooks only:

    python notebookify.py -j Aggregation

The name can be given in whatever form is handy - `Aggregation`, `Aggregation.json` and
`Aggregation_LOCAL.ipynb` all mean the same pair, and a path works too:

    python notebookify.py -j notebook/Aggregation notebook/DatabaseUtils_LOCAL.ipynb

If a named notebook has no matching `_METADATA.json` the script says so and writes nothing at all,
rather than half-processing the list.

Or every pair in the working dir:

    python notebookify.py -j

With no names it will list the json files it is about to rewrite and ask first (when there's more
than one), so a stale `_LOCAL.ipynb` sitting in the folder can't quietly clobber a notebook you
weren't working on. Add `-y` to skip the prompt in scripts.
 
## Git Ignore
When converting to ipynb, the script saves the notebook as `[filename]_LOCAL.ipynb`, which you can then edit as needed. The synapse-specific metadata (spark configuration and the like) will be stored as `[filename]_METADATA.json`. 
If you wish you can include the following lines in your `.gitignore` to easily keep these out of the repo:

    *_LOCAL.ipynb
    *_METADATA.json

## File Creation
This util is handy for existing files, but if you want to create a new notebook you should still create and commit it through the Synapse Analytics web editor. Synapse tracks a bunch of fields in the metadata that VSCode won't know to populate (and will actively meddle with if allowed).
