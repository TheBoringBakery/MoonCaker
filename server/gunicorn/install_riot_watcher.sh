#! /usr/bin/env sh

wget https://github.com/pseudonym117/Riot-Watcher/archive/refs/heads/master.zip
unzip master.zip -d .
cd Riot-Watcher-master
python setup.py install
cd ..
# rm -r -f Riot-Watcher-master/