#! /usr/bin/env sh

wget https://github.com/TheBoringBakery/Riot-Watcher/archive/refs/heads/master.zip
unzip master.zip -d .
cd Riot-Watcher-master
python setup.py install
cd ..
rm -r -f Riot-Watcher-master/
rm master.zip
