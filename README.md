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
## Usage

#### Synapse json to .ipynb:

    notebookify file1.json file2.json file3.json ...
This will create a `[filename]_LOCAL.ipynb` file, which you can edit in your IDE of choice.

#### .ipynb notebooks to synapse json:

    notebookify -j
 This will convert all `_LOCAL.ipynb` files in the current directory back to `[filename].json`, ready to git add, commit, and push.
 
## Git Ignore
When converting to ipynb, the script saves synapse-specific metadata (spark configuration and the like) as `[filename]_METADATA.json`. 
If you wish you can include the following lines in your `.gitignore` to easily keep these out of the repo:

    *_LOCAL.ipynb
    *_METADATA.json

## File Creation
If you want to create a new notebook you should still create and commit it through the Synapse Analytics web editor. Synapse tracks a bunch of fields in the metadata that VSCode won't know to populate (and will actively meddle with if allowed).
