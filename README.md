This repository contains the source code of the website [paulcousin.net/graph-rewriting-automata](https://paulcousin.net/graph-rewriting-automata/).

It was made using [Jupyter Book](https://jupyterbook.org/) and uses of the code present in the following repositories :
* [paulcousin/gra-python](https://github.com/paulcousin/gra-python)
* [paulcousin/gra-mathematica](https://github.com/paulcousin/gra-mathematica)

### Build the Jupyter Book from a virtual environment
In your terminal, run the following commands.
``` bash
python3.9 -m venv .venv	
```
``` bash
source .venv/bin/activate
```
``` bash
pip install --upgrade pip
```
``` bash
pip install -r requirements.txt
```
``` bash
jupyter-book build .
```
To deactivate the virtual environment, simply run:
``` bash
deactivate
```

### Publish to the gh-pages branch
``` bash
ghp-import -n -p -f _build/html
```