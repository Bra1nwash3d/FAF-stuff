# FA Forever - IRC bot

A fork of https://github.com/Petricpwnz/NyAI, refactored, modified and (currently) deweebified.

## Installation

Install Python 3.6 or higher.
`pip install pipenv` to install pipenv.

Create the config file and modify the settings as appropriate:

    cp config.ini.example config.ini

Install the package dependencies:

    pipenv install
    
I honestly don't know what's exactly needed to run this, and whether the pipenv is complete -
I'll figure it out at some point!

But here's a pip freeze:

    aiohttp==3.5.4
    async-timeout==3.0.1
    attrs==18.2.0
    BTrees==4.5.1
    chardet==3.0.4
    configobj==5.0.6
    docopt==0.6.2
    idna==2.8
    irc3==1.1.1
    multidict==4.5.2
    numpy==1.15.3
    pandas==0.23.4
    persistent==4.4.3
    python-dateutil==2.7.5
    pytz==2018.7
    six==1.11.0
    transaction==2.4.0
    venusian==1.2.0
    websockets==7.0
    yarl==1.3.0
    zc.lockfile==1.4
    ZConfig==3.4.0
    ZODB==5.5.1
    zodbpickle==1.0.3
    zope.interface==4.6.0


## Usage

    pipenv run irc3 config.ini
