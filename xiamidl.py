#!/usr/bin/python3
import sys
import copy
import threading
from logger import Logger
from xiami import xiami
from misc import dealInput, loadConfig

OPTIONS = '''************************************************************
1) Search for artist
2) Download by artist ID
3) Search for album
4) Download by album ID
5) Download lots of stuff starting with a set of albums (not yet implemented)
q) Quit
************************************************************'''

class xiamidl():
    def __init__(self, config=None, **kwargs):
        self.config = self.config = loadConfig('config.json') if config is None else config
        self.logger_handle = Logger(self.config['logfilepath'])
        supported_sources = {
            'xiami': xiami,
        }
        for key, value in supported_sources.items():
            setattr(self, key, value(copy.deepcopy(self.config), self.logger_handle))
    
    def run(self):
        while True:
            print(OPTIONS)
            option_no = dealInput('Select option #: ')
            if option_no == '1':
                artist_query = dealInput('Search for artist: ')
                self.xiami.searchArtist(artist_query)
            elif option_no == '2':
                artist_id = dealInput('Enter artist ID: ')
                self.xiami.getArtist(artist_id)
            elif option_no == '3':
                album_query = dealInput('Search for album: ')
                self.xiami.searchAlbum(album_query)
            elif option_no == '4':
                album_id = dealInput('Enter album ID: ')
                self.xiami.getAlbum(album_id)

if __name__ == '__main__':
    dl_client = xiamidl()
    dl_client.run()

