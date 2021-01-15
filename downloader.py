import click
import warnings
import requests
from misc import *
from pydub import AudioSegment
warnings.filterwarnings('ignore')


class Downloader():
    def __init__(self, songinfo, config, session=None, **kwargs):
        self.songinfo = songinfo
        self.config = config
        self.session = requests.Session() if session is None else session
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',}

    def start(self):
        songinfo, session, headers = self.songinfo, self.session, self.headers
        if not os.path.isdir(os.path.join(songinfo['savedir'], songinfo['album_artist'], songinfo['album'])):
            os.makedirs(os.path.join(songinfo['savedir'], songinfo['album_artist'], songinfo['album']))
        checkDir(songinfo['savedir'])
        album_dir = os.path.join(songinfo['savedir'], songinfo['album_artist'], songinfo['album'])
        if not os.path.isfile(os.path.join(album_dir, self.config['coverartname'] + '.jpg')) and songinfo['album_cover_url'] != None:
            with session.get(songinfo['album_cover_url'], headers=headers, stream=True, verify=False) as response:
                with open(os.path.join(album_dir, self.config['coverartname'] + '.jpg'), 'wb') as cfp:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            cfp.write(chunk)
        if songinfo['is_multi_disc']:
            disc_dir = os.path.join(album_dir, 'Disc ' + songinfo['disc_number'])
            if not os.path.isdir(disc_dir):
                os.mkdir(disc_dir)
        else:
            disc_dir = album_dir
        track_file_name = songinfo['track_number'] + '. ' + songinfo['artist'] + ' - ' + songinfo['track_name']
        if songinfo['lyrics'] != None and not os.path.isfile(os.path.join(disc_dir, track_file_name + '.lrc')):
            with open(os.path.join(disc_dir, track_file_name + '.lrc'), 'w') as lfp:
                lfp.write(songinfo['lyrics'])
        try:
            is_success = False
            if songinfo['ext'] == 'wav' and self.config['wav2flac']:
                track_final_path = os.path.join(disc_dir, track_file_name + '.flac')
            else:
                track_final_path = os.path.join(disc_dir, track_file_name + '.' + songinfo['ext'])
            if not os.path.isfile(track_final_path):
                with session.get(songinfo['download_url'], headers=headers, stream=True, verify=False) as response:
                    if response.status_code == 200:
                        total_size, chunk_size = int(response.headers['content-length']), 1024
                        label = '%s. %s.%s [%0.2fMB]' % (songinfo['track_number'], songinfo['track_name'], songinfo['ext'], total_size / 1024 / 1024)
                        with click.progressbar(length=total_size, label=label) as progressbar:
                            with open(os.path.join(disc_dir, track_file_name + '.' + songinfo['ext']), 'wb') as fp:
                                for chunk in response.iter_content(chunk_size=chunk_size):
                                    if chunk:
                                        fp.write(chunk)
                                        progressbar.update(len(chunk))
                        if songinfo['ext'] == 'wav' and self.config['wav2flac']:
                            self.compress_wav(os.path.join(disc_dir, track_file_name), self.config['embedtags'], songinfo)
                        elif self.config['embedtags']:
                            self.tag_file(os.path.join(disc_dir, track_file_name + '.' + songinfo['ext']), songinfo['ext'], songinfo)
                        is_success = True
            else:
                print('Track already downloaded, skipping...')
                is_success = True
        except Exception as e:
            print(e)
            is_success = False
        return is_success

    def compress_wav(self, wavpath, add_tags, songinfo):
        track = AudioSegment.from_file(wavpath + '.wav', format = 'wav')
        if add_tags:
            print('Compressing to flac with tags...')
            tagset = {'albumartist': songinfo['album_artist'],
                      'album': songinfo['album'],
                      'artist': songinfo['artist'],
                      'title': songinfo['track_name'],
                      'discnumber': songinfo['disc_number'],
                      'tracknumber': songinfo['track_number'],
                      'date': songinfo['album_date'],
                      }
        else:
            print('Compressing to flac...')
            tagset = {}
        track.export(wavpath + '.flac', format = 'flac',
            parameters = ['-compression_level', '8'],
            tags = tagset,
            id3v2_version = "3")
        os.remove(wavpath + '.wav')

    def tag_file(self, filepath, formatext, songinfo):
        print('Adding tags...')
        if formatext == 'm4a':
            formatext = 'mp4'
        track = AudioSegment.from_file(filepath, format = formatext)
        tagset = {'albumartist': songinfo['album_artist'],
                  'album': songinfo['album'],
                  'artist': songinfo['artist'],
                  'title': songinfo['track_name'],
                  'discnumber': songinfo['disc_number'],
                  'tracknumber': songinfo['track_number'],
                  'date': songinfo['album_date'],
                  }
        track.export(filepath, format=formatext, tags = tagset)
