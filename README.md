![GitHub release (latest by date)](https://img.shields.io/github/v/release/devfred78/domichess)
![GitHub license](https://img.shields.io/github/license/devfred78/domichess)
![GitHub issues](https://img.shields.io/github/issues/devfred78/domichess)
![GitHub pull requests](https://img.shields.io/github/issues-pr/devfred78/domichess)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# DomiChess

A simple chess game for Windows, written in Python.

## About the project

This project aims to develop and provide the simplest, the most intuitive and user-friendly interface for playing chess on Windows. If you are a casual user of this platform, then playing a game should be as simple as putting a real chess board on a table !

![DomiChess 0.1.0 in action \!](assets/DomiChess_Anim.gif)

### Main features

- Only one click needed to start a game between 2 human, local opponents
- Possibility to personalize the name of the game and the opponent's names
- Display the move capabilities when a piece is clicked
- Chessmate detection
- Detection of automatic draws: stalemate, insufficient material, seventy-five-move rule, fivefold repetition
- Detection of claimable draws: fifty-move rule, threefold repetition
- Ability to add UCI-compliant chess engines (see below what it means)
- With at least one engine installed:
	- Possibility to be helped for the next move
	- Basic engine configuration that can be different for each opponent, even if the engine chosen is the same one
	- Play against the computer
	- Let play the computer against itself (with the same or between different engines if at least two are installed)
- **(Planned, not yet implemented)** Play against a remote opponent, on the same local network or on Internet

### Built with

This project is mainly based on the 2 following libraries:

- [python-chess](https://python-chess.readthedocs.io/en/latest/index.html): a chess library for Python. This library provides tools for move validation, end-game condition check, board rendering and communication with chess engines.
- [pySimpleGUI](https://www.pysimplegui.org/en/latest/): Python GUIs for humans. This library makes the build of Graphical User Interfaces (GUI) easier and funnier than ever. All displayed elements of the project are built using this library.

## Getting Started

### Prerequisites

DomiChess is only compatible with Windows version 10 or above. However, it can be executed on 32-bit or 64-bit variation of this operationg system (you have to download the matching file though).

Even if not strictly required for a basic usage of DomiChess, it is highly recommended to add at least one **[chess engine](https://en.wikipedia.org/wiki/Chess_engine)**. With this additional program, not distributed alongside DomiChess, you are able to play alone against your computer, to ask for help during your game against a human or computarized opponent, or even to see your computer playing against itself.

Since the appearance of the first chess engines as computer programs independant from their graphical interface counterparts (in 90's), protocols have been developped to rule the communications between the two program families. Nowadays, the **[Universal Chess Interface](https://en.wikipedia.org/wiki/Universal_Chess_Interface)** (UCI) is one of the most popular protocols.

The UCI protocol is natively supported by DomiChess, that is, in that way, theorically compatible with all UCI-compliant chess engines.

Here are some examples of UCI-compliant chess engines available for Windows (list in alphabetical order):

- [Ethereal](https://github.com/AndyGrant/Ethereal) (Open-source, standard version: free, NNUE (Efficiently-Updated Neural Network) version: commercial)
- [MadChess](https://www.madchess.net/) (open-source, free)
- [Monolith](https://github.com/cimarronOST/Monolith) (open-source, free)
- [Rybka](http://rybkachess.com/) (proprietary, commercial, old version available for free)
- [Shredder](https://www.shredderchess.com/) (proprietary, commercial)
- [Stockfish](https://stockfishchess.org/) (open-source, free)

Of course, there are plenty of other UCI-compliant chess engines ! Some web sites attempt to list them. Try the following ones to begin your search:

- [UCI-engine list on the ChessProgramming Wiki](https://www.chessprogramming.org/Category:UCI)
- [Top UCI engines](http://www.sdchess.ru/engines_uci_top.htm) (a bit old, though)

Alternatively, you can search ["UCI chess engine" on Github](https://github.com/search?q=UCI+chess+engine).

### Installation

#### First installation

The installation of DomiChess is very easy: download the suitable executable from the [latest release page](https://github.com/devfred78/domichess/releases/latest), and put it in the folder of your choice. And that's it !

The first time you execute DomiChess, an `engines` folder is created in the same location as where you place the program. Copy here your favorite chess engines (consisting of at least an `*.exe` file, occasionally along with configuration or database file(s)). During the next launch, DomiChess will automatically detect the compatible engines.

#### Update

For updating DomiChess, just replace the older release by the most recent one, in the installation folder. You can let in place the chess engines you previously copied in the `engines` folder.

### Usage

Basically, you can start a chess game between two local, human opponents by just clicking on the following button: ![Start](assets/Start_Button.PNG)

But if you wish to personnalize your game, or if you want to play against a customized AI, you needs to deal a little bit more with your mouse and your keyboard... Nothing complicated though, the DomiChess interface has been designed to be as intuitive as possible.

See the [USAGE.md](https://github.com/devfred78/domichess/blob/main/USAGE.md) file for more detailed explanations about the usage.

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement" or "bug", according to whether you want to share a proposal of a new function, or to record an anomaly.

Don't forget to give the project a star! Thanks again!

See the [CONTRIBUTING.md](https://github.com/devfred78/domichess/blob/main/CONTRIBUTING.md) file for deeper instructions about contribution on DomiChess. 

## License

Distributed under the GNU GPLv3 license. Check out [LICENSE.md](https://github.com/devfred78/domichess/blob/main/LICENSE.md) file for more information.

## Acknowledgments

I would like greatfully to thank:

[Niklas Fiekas](https://github.com/niklasf) for his powerful [chess library for Python](https://github.com/niklasf/python-chess).

pySimpleGUI [authors](https://github.com/PySimpleGUI) for making **ALL** Python programmers (even the less experienced !) able to make GUI programs.

[Kozea](https://github.com/Kozea) for choosing to freely share (under LGPL license) its very interesting [CairoSVG](https://github.com/Kozea/CairoSVG) library, that helps to display all the SVG files generated by python-chess.

Developers of [Cairo](https://www.cairographics.org/), on which CairoSVG is based, for providing their rich 2D graphics library.

Authors of [PyInstaller](https://github.com/pyinstaller/pyinstaller) for this remarkable program able to bundle a Python application and all its dependencies into a single package.

[Python Software Foundation](https://github.com/psf) for [black](https://github.com/psf/black), their "uncompromising Python code formatter", making your whole code source compliant with [PEP 8](https://peps.python.org/pep-0008/) in only one simple command.

[Make a README](https://www.makeareadme.com/), [Sayan Mondal](https://medium.com/swlh/how-to-make-the-perfect-readme-md-on-github-92ed5771c061), [Hillary Nyakundi](https://www.freecodecamp.org/news/how-to-write-a-good-readme-file/) and [othneildrew](https://github.com/othneildrew/Best-README-Template) for providing very interesting materials to write good README files (far better than I can write by myself !).

[Choose an open source license](https://choosealicense.com/) for helping to choose the best suitable license for this project.

[Semantic Versioning](https://semver.org/) for providing clear specifications for versioning projects.

[Real Python](https://realpython.com/) for contributing really increasing skills in Python for everyone, novices or veterans.

[GitHub](https://github.com/) for hosting this project, and helping to share it.

And, of course, all the former, current and further contributors of this project !