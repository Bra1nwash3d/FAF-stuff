# FA Forever - IRC bot

A fun-chatbot for the [Forged Alliance Forever](http://www.faforever.com/) Community, based on [QAI](https://github.com/FAForever/QAI) code.

## Installation

Install Python 3.4 or a later 3.x version.

Install the package dependencies:

    windows:	pip install -r requirements.txt
    linux:		pip3 install -r requirements.txt

Create the config file and modify the settings as appropriate:

    cp config.ini.example config.ini

## Usage

    irc3 config.ini

## Comment

    Like any fun project this has turned into some spaghetti code that should be reworked proplerly
    (especially using lightsql/mysql instead of json objects), but any single minor change does not seem
    to make it necessary...
