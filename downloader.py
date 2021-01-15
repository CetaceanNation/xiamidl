import click
import warnings
import requests
from misc import *
warnings.filterwarnings('ignore')


class Downloader():
    def __init__(self, songinfo, is_multi_disc, session=None, **kwargs):
        self.songinfo = songinfo
        self.is_multi_disc = is_multi_disc
        self.session = requests.Session() if session is None else session
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',}
    def start(self):
        songinfo, is_multi_disc, session, headers = self.songinfo, self.is_multi_disc, self.session, self.headers
        if not os.path.isdir(os.path.join(songinfo['savedir'], songinfo['artist'], songinfo['album'])):
            os.makedirs(os.path.join(songinfo['savedir'], songinfo['artist'], songinfo['album']))
        checkDir(songinfo['savedir'])
        album_dir = os.path.join(songinfo['savedir'], songinfo['album_artist'], songinfo['album'])
        if not os.path.isfile(os.path.join(album_dir, 'cover.jpg')) and songinfo['album_cover_url'] != None:
            with session.get(songinfo['album_cover_url'], headers=headers, stream=True, verify=False) as response:
                with open(os.path.join(album_dir, 'cover.jpg'), 'wb') as cfp:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            cfp.write(chunk)
        if is_multi_disc:
            disc_dir = os.path.join(album_dir, 'Disc ' + songinfo['disc_number'])
        else:
            disc_dir = album_dir
        track_file_name = songinfo['track_number'] + '. ' + songinfo['artist'] + ' - ' + songinfo['track_name']
        if songinfo['lyrics'] != None:
            with open(os.path.join(disc_dir, track_file_name + '.lrc'), 'w') as lfp:
                lfp.write(songinfo['lyrics'])
        try:
            is_success = False
            with session.get(songinfo['download_url'], headers=headers, stream=True, verify=False) as response:
                if response.status_code == 200:
                    total_size, chunk_size = int(response.headers['content-length']), 1024
                    label = '%s. %s [%0.2fMB]' % (songinfo['track_number'], songinfo['track_name'], total_size / 1024 / 1024)
                    with click.progressbar(length=total_size, label=label) as progressbar:
                        with open(os.path.join(disc_dir, track_file_name + '.' + songinfo['ext']), 'wb') as fp:
                            for chunk in response.iter_content(chunk_size=chunk_size):
                                if chunk:
                                    fp.write(chunk)
                                    progressbar.update(len(chunk))
                    is_success = True
        except:
            is_success = False
        return is_success
        