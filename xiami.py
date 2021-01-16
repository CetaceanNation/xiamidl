import re
import time
import json
import requests
from datetime import datetime
from hashlib import md5
from misc import *
from downloader import Downloader

ALBUM_PAGE_RESULTS = 30
SEARCH_RESULTS = 8

class xiami():
    def __init__(self, config, logger_handle, **kwargs):
        self.session = requests.Session()
        self.session.proxies.update(config['proxies'])
        self.config = config
        self.logger_handle = logger_handle
        self.source = 'xiami'
        self.__initialize()

    def searchArtist(self, artist_query):
        search_url = self.base_url.format(action=self.actions['searchartists'])
        params = {'key': artist_query, 'pagingVO': {'page': str(1), 'pageSize': SEARCH_RESULTS}}
        response = self.session.get(search_url, headers=self.headers, params=self.__xiamiSign(params, self.__getToken()))
        artist_list = response.json()['data']['data']['artists']
        print('Search results for "%s":' % (artist_query))
        selectionNum = 0
        selections = {}
        for artist_result in artist_list:
            selections[str(selectionNum)] = artist_result['artistId']
            if artist_result['alias'] != '':
                artist_string = '%s (%s)' % (artist_result['artistName'], artist_result['alias'])
            else:
                artist_string = artist_result['artistName']
            print('%d) %s' % (selectionNum + 1, artist_string))
            selectionNum+=1
        while True:
            artist_option = dealInput('Option #: ')
            if not int(artist_option) - 1 > len(artist_list) and not int(artist_option) - 1 < 0:
                self.getArtist(selections[str(int(artist_option) - 1)])
                return

    def searchAlbum(self, album_query):
        search_url = self.base_url.format(action=self.actions['searchalbums'])
        params = {'key': album_query, 'pagingVO': {'page': str(1), 'pageSize': SEARCH_RESULTS}}
        response = self.session.get(search_url, headers=self.headers, params=self.__xiamiSign(params, self.__getToken()))
        album_list = response.json()['data']['data']['albums']
        print('Search results for "%s":' % (album_query))
        selectionNum = 0
        selections = {}
        for album_result in album_list:
            selections[str(selectionNum)] = album_result['albumId']
            print('%d) %s - %s [%s tracks]' % (selectionNum + 1, album_result['artistName'], album_result['albumName'], album_result['songCount']))
            selectionNum+=1
        while True:
            album_option = dealInput('Option #: ')
            if not int(album_option) - 1 > len(album_list) and not int(album_option) - 1 < 0:
                self.getAlbum(selections[str(int(album_option) - 1)])
                return

    def getArtist(self, artist_id):
        artist_url = self.base_url.format(action=self.actions['getartistalbums'])
        pageNum = 1
        while True:
            params = {'artistId': artist_id, 'category': 0, 'pagingVO': {'page': str(pageNum), 'pageSize': ALBUM_PAGE_RESULTS}}
            response = self.session.get(artist_url, headers=self.headers, params=self.__xiamiSign(params, self.__getToken()))
            album_page = response.json()['data']['data']
            print('Getting albums from artist %s...' % (album_page['albums'][0]['artistName']))
            for album in album_page['albums']:
                self.getAlbum(album['albumId'])
            if album_page['more'] == 'false':
                break
            pageNum+=1

    def getAlbum(self, album_id):
        album_url = self.base_url.format(action=self.actions['getalbumdetail'])
        params = {'albumId': album_id}
        response = self.session.get(album_url, headers=self.headers, params=self.__xiamiSign(params, self.__getToken()))
        album_detail = response.json()['data']['data']['albumDetail']
        print('Getting album "%s"' % (album_detail['albumName']))
        for song in album_detail['songs']:
            is_multi_disc = int(album_detail['cdCount']) > 1
            album_date = datetime.utcfromtimestamp(int(album_detail['gmtPublish']) / 1000).strftime('%Y-%m-%d')
            self.getSong(song['songId'], album_detail['artistName'], is_multi_disc, album_date)
    
    def getSong(self, song_id, album_artist, is_multi_disc, album_date):
        cfg = self.config.copy()
        song_url = self.base_url.format(action=self.actions['getsongdetail'])
        params = {'songId': song_id}
        response = self.session.get(song_url, headers=self.headers, params=self.__xiamiSign(params, self.__getToken()))
        song_detail = response.json()['data']['data']['songDetail']
        download_url = ''
        for file_info in song_detail['listenFiles']:
            if not file_info['filesize']: continue
            download_url = file_info['url']
            ext = file_info['format']
            break
        if not download_url:
            print('Cannot download track "%s. %s", not available.' % (song_detail.get('track', 0), song_detail.get('songName', 'No Title')))
            return
        lyric_url, lyrics = song_detail.get('lyricInfo', {}).get('lyricFile', ''), None
        if lyric_url:
            response = self.session.get(lyric_url, headers=self.headers)
            response.encoding = 'utf-8'
            lyrics = response.text
        songinfo = {
            'songid': str(song_detail['songId']),
            'artist': filterBadCharacter(song_detail['artistName']),
            'album_cover_url': song_detail.get('albumLogo', None),
            'album': filterBadCharacter(song_detail.get('albumName', 'Non-album Track')),
            'album_artist': filterBadCharacter(album_artist),
            'album_date': album_date,
            'disc_number': song_detail.get('cdSerial', 1),
            'is_multi_disc': is_multi_disc,
            'track_number': song_detail.get('track', 0),
            'track_name': filterBadCharacter(song_detail.get('songName', 'No Title')).split('–')[0].strip(),
            'savedir': cfg['savedir'],
            'download_url': download_url,
            'lyrics': lyrics,
            'ext': ext,
        }
        if not songinfo['album']: songinfo['album'] = 'Non-Album Tracks'
        self.download(songinfo)

    def download(self, songinfo):
        task = Downloader(songinfo, self.config, self.session)
        if task.start():
            self.logger_handle.info('Downloaded track "%s. %s - %s" successfully.' % (songinfo['track_number'], songinfo['artist'], songinfo['track_name']))
        else:
            self.logger_handle.info('Failed to download track "%s. %s - %s".' % (songinfo['track_number'], songinfo['artist'], songinfo['track_name']))

    def __xiamiSign(self, params, token=''):
        appkey = '23649156'
        t = str(int(time.time() * 1000))
        request_str = {
            'header': {'appId': '200', 'platformId': 'h5'},
            'model': params
        }
        data = json.dumps({'requestStr': json.dumps(request_str)})
        sign = '%s&%s&%s&%s' % (token, t, appkey, data)
        sign = md5(sign.encode('utf-8')).hexdigest()
        params = {
            't': t,
            'appKey': appkey,
            'sign': sign,
            'data': data
        }
        return params

    def __getToken(self):
        action = self.actions['getsongdetail']
        url = self.base_url.format(action=action)
        params = {'songId': '1'}
        response = self.session.get(url, params=self.__xiamiSign(params))
        cookies = response.cookies.get_dict()
        return cookies['_m_h5_tk'].split('_')[0]

    def __initialize(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
            'Referer': 'http://h.xiami.com',
            'Connection': 'keep-alive',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept': '*/*'
        }
        self.base_url = 'https://acs.m.xiami.com/h5/{action}/1.0/'
        self.actions = {
            # 'pagingVO': {'page': 1, 'pageSize': #}
            'searchsongs': 'mtop.alimusic.search.searchservice.searchsongs', # {'key': keyword, 'pagingVO': {}}
            'searchalbums': 'mtop.alimusic.search.searchservice.searchalbums', # {'key': keyword, 'pagingVO': {}}
            'searchartists': 'mtop.alimusic.search.searchservice.searchartists', # {'key': keyword, 'pagingVO': {}}
            'getartistdetail': 'mtop.alimusic.music.artistservice.getartistdetail',
            'getartistalbums': 'mtop.alimusic.music.albumservice.getartistalbums', # {'artistId': artist_id, 'category': 0, 'pagingVO': {}}
            'getsimilarartists': 'mtop.alimusic.recommend.artistservice.getsimilarartists',
            'getalbumdetail': 'mtop.alimusic.music.albumservice.getalbumdetail', # {'albumId': album_id}
            'getsongdetail': 'mtop.alimusic.music.songservice.getsongdetail',
            'getsongs': 'mtop.alimusic.music.songservice.getsongs',
            'getsonglyrics': 'mtop.alimusic.music.lyricservice.getsonglyrics'
        }