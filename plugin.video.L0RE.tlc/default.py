﻿#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import re
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY2:
	from urllib import quote, unquote, quote_plus, unquote_plus, urlencode  # Python 2.X
	from urllib2 import build_opener, HTTPCookieProcessor, Request, urlopen  # Python 2.X
	from cookielib import LWPCookieJar  # Python 2.X
	from urlparse import urljoin, urlparse, urlunparse  # Python 2.X
elif PY3:
	from urllib.parse import quote, unquote, quote_plus, unquote_plus, urlencode, urljoin, urlparse, urlunparse  # Python 3+
	from urllib.request import build_opener, HTTPCookieProcessor, Request, urlopen  # Python 3+
	from http.cookiejar import LWPCookieJar  # Python 3+
import json
import xbmcvfs
import shutil
import socket
import time
from datetime import datetime, timedelta
import io
import gzip


global debuging
pluginhandle = int(sys.argv[1])
addon = xbmcaddon.Addon()
addonPath = xbmc.translatePath(addon.getAddonInfo('path')).encode('utf-8').decode('utf-8')
dataPath = xbmc.translatePath(addon.getAddonInfo('profile')).encode('utf-8').decode('utf-8')
temp        = xbmc.translatePath(os.path.join(dataPath, 'temp', '')).encode('utf-8').decode('utf-8')
channelFavsFile = os.path.join(dataPath, 'my_TLC_favourites.txt').encode('utf-8').decode('utf-8')
defaultFanart = os.path.join(addonPath, 'fanart.jpg')
icon = os.path.join(addonPath, 'icon.png')
spPIC = os.path.join(addonPath, 'resources', 'media', '').encode('utf-8').decode('utf-8')
useThumbAsFanart = addon.getSetting("useThumbAsFanart") == "true"
enableAdjustment = addon.getSetting("show_settings") == "true"
enableInputstream = addon.getSetting("inputstream") == "true"
baseURL = "https://www.tlc.de/"

xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')

if xbmcvfs.exists(temp) and os.path.isdir(temp):
	shutil.rmtree(temp, ignore_errors=True)
	xbmc.sleep(500)
xbmcvfs.mkdirs(temp)
cookie = os.path.join(temp, 'cookie.lwp')
cj = LWPCookieJar()

if xbmcvfs.exists(cookie):
	cj.load(cookie, ignore_discard=True, ignore_expires=True)

def py2_enc(s, encoding='utf-8'):
	if PY2 and isinstance(s, unicode):
		s = s.encode(encoding)
	return s

def py2_uni(s, encoding='utf-8'):
	if PY2 and isinstance(s, str):
		s = unicode(s, encoding)
	return s

def py3_dec(d, encoding='utf-8'):
	if PY3 and isinstance(d, bytes):
		d = d.decode(encoding)
	return d

def translation(id):
	LANGUAGE = addon.getLocalizedString(id)
	LANGUAGE = py2_enc(LANGUAGE)
	return LANGUAGE

def failing(content):
	log(content, xbmc.LOGERROR)

def debug(content):
	log(content, xbmc.LOGDEBUG)

def log(msg, level=xbmc.LOGNOTICE):
	msg = py2_enc(msg)
	xbmc.log("["+addon.getAddonInfo('id')+"-"+addon.getAddonInfo('version')+"]"+msg, level)

def getUrl(url, header=None):
	global cj
	opener = build_opener(HTTPCookieProcessor(cj))
	try:
		if header:
			opener.addheaders = header
		else:
			opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36')]
			opener.addheaders = [('Accept-Encoding', 'gzip, deflate')]
		response = opener.open(url, timeout=30)
		if response.info().get('Content-Encoding') == 'gzip':
			content = py3_dec(gzip.GzipFile(fileobj=io.BytesIO(response.read())).read())
		else:
			content = py3_dec(response.read())
	except Exception as e:
		failure = str(e)
		if hasattr(e, 'code'):
			failing("(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} ##########".format(url, failure))
		elif hasattr(e, 'reason'):
			failing("(getUrl) ERROR - ERROR - ERROR : ########## {0} === {1} ##########".format(url, failure))
		content = ""
		return sys.exit(0)
	opener.close()
	try: cj.save(cookie, ignore_discard=True, ignore_expires=True)
	except: pass
	return content

def ADDON_operate(TESTING):
	js_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": {"addonid":"'+TESTING+'", "properties": ["enabled"]}, "id":1}')
	if '"enabled":false' in js_query:
		try:
			xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid":"'+TESTING+'", "enabled":true}, "id":1}')
			failing("(ADDON_operate) ERROR - ERROR - ERROR :\n##### Das benötigte Addon : *"+TESTING+"* ist NICHT aktiviert !!! #####\n##### Es wird jetzt versucht die Aktivierung durchzuführen !!! #####")
		except: pass
	if '"error":' in js_query:
		xbmcgui.Dialog().ok(addon.getAddonInfo('id'), translation(30501).format(TESTING))
		failing("(ADDON_operate) ERROR - ERROR - ERROR :\n##### Das benötigte Addon : *"+TESTING+"* ist NICHT installiert !!! #####")
		return False
	if '"enabled":true' in js_query:
		return True

def index():
	addDir(translation(30601), baseURL+"api/search?query=*&limit=50", "listseries", icon, nosub="overview_all")
	addDir(translation(30602), "", "listthemes", icon)
	addDir(translation(30603), baseURL+"api/shows/highlights?limit=50", "listseries", icon, nosub="featured")
	addDir(translation(30604), baseURL+"api/shows/neu?limit=50", "listseries", icon, nosub="recently_added")
	addDir(translation(30605), baseURL+"api/shows/beliebt?limit=50", "listseries", icon, nosub="most_popular")
	addDir(translation(30606), "", "listShowsFavs", icon)
	if enableAdjustment:
		addDir(translation(30607), "", "aSettings", icon)
		if enableInputstream:
			if ADDON_operate('inputstream.adaptive'):
				addDir(translation(30608), "", "iSettings", icon)
			else:
				addon.setSetting("inputstream", "false")
	xbmcplugin.endOfDirectory(pluginhandle)

def listthemes():
	debug("-------------------------- LISTTHEMES --------------------------")
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
	html = getUrl(baseURL+"themen")
	content = html[html.find('href="/themen">Themen</a><div class="header__nav__dd-wrapper">')+1:]
	content = content[:content.find('</ul></div>')]
	result = re.compile('<a href="(.*?)">(.*?)</a>').findall(content)
	for link, name in result:
		url = baseURL+"api/genres/"+link.split('/')[-1]+"?limit=100"
		name = py2_enc(name).replace('&amp;', '&').strip()
		debug("(listthemes) ### NAME : "+str(name)+" || LINK : "+str(link)+" || URL : "+str(url)+" ###")
		if "themen" in link:
			addDir(name, url, "listseries", icon, nosub="overview_themes")
	xbmcplugin.endOfDirectory(pluginhandle)

def listseries(url, PAGE, POS, ADDITION):
	debug("-------------------------- LISTSERIES --------------------------")
	debug("(listseries) ### URL : "+str(url)+" ### PAGE : "+str(PAGE)+" ### POS : "+str(POS)+" ### ADDITION : "+str(ADDITION)+" ###")
	count = int(POS)
	readyURL = url+"&page="+str(PAGE)
	content = getUrl(readyURL)
	debug("(listseries) ##### CONTENT : "+str(content)+" #####")
	DATA = json.loads(content)
	if "search?query" in url:
		elements = DATA['shows']
	else:
		elements = DATA['items']
	for elem in elements:
		debug("(listseries) ##### ELEMENT : "+str(elem)+" #####")
		title = py2_enc(elem['title']).strip()
		name = title
		idd = ""
		if 'id' in elem and elem['id'] != "" and elem['id'] != None:
			idd = elem['id']
		plot = ""
		if 'description' in elem and elem['description'] != "" and elem['description'] != None:
			plot = py2_enc(elem['description']).replace('\n\n\n', '\n\n').strip()
		image = ""
		if 'image' in elem and 'src' in elem['image'] and elem['image']['src'] != "" and elem['image']['src'] != None:
			image = elem['image']['src']
		debug("(listseries) noFilter ### NAME : "+ str(name) +" || IDD : "+ str(idd) +" || IMAGE : "+ str(image) +" ###")
		if idd !="" and len(idd) < 9 and plot != "" and image != "":
			count += 1
			if 'beliebt' in url:
				name = "[COLOR chartreuse]"+str(count)+" •  [/COLOR]"+title
			try: 
				if elem['hasNewEpisodes']: name = name+translation(30609)
			except: pass
			debug("(listseries) Filtered ### NAME : "+str(name)+" || IDD : "+str(idd)+" || IMAGE : "+str(image)+" ###")
			addType=2
			if os.path.exists(channelFavsFile):
				with open(channelFavsFile, 'r') as output:
					lines = output.readlines()
					for line in lines:
						if line.startswith('###START'):
							part = line.split('###')
							idd_FS = part[2]
							if idd == idd_FS: addType=1
			addDir(name, idd, "listepisodes", image, plot, nosub=ADDITION, originalSERIE=title, addType=addType)
	currentRESULT = count
	debug("(listseries) ##### currentRESULT : "+str(currentRESULT)+" #####")
	try:
		currentPG = DATA['meta']['currentPage']
		totalPG = DATA['meta']['totalPages']
		debug("(listseries) ##### currentPG : "+str(currentPG)+" from totalPG : "+str(totalPG)+" #####")
		if int(currentPG) < int(totalPG):
			addDir(translation(30610), url, "listseries", spPIC+"nextpage.png", page=int(currentPG)+1, position=int(currentRESULT), nosub=ADDITION)
	except: pass
	xbmcplugin.endOfDirectory(pluginhandle)

def listepisodes(idd, originalSERIE):
	debug("-------------------------- LISTEPISODES --------------------------")
	COMBI = []
	SELECT = []
	pos1 = 0
	url = baseURL+"api/show-detail/"+str(idd)
	debug("(listepisodes) ### URL : "+str(url)+" ### originalSERIE : "+str(originalSERIE)+" ###")
	try:
		content = getUrl(url)
		debug("(listepisodes) ##### CONTENT : "+str(content)+" #####")
		DATA = json.loads(content)
	except: return xbmcgui.Dialog().notification(translation(30521).format(str(idd)), translation(30522), icon, 12000)
	genstr = ""
	genreList=[]
	if 'genres' in DATA['show']:
		for item in DATA['show']['genres']:
			gNames = py2_enc(item['name'])
			genreList.append(gNames)
		genstr =' / '.join(genreList)
	if 'episode' in DATA['videos'] or 'standalone' in DATA['videos']:
		if 'episode' in DATA['videos']:
			subelement = DATA['videos']['episode']
			if PY2: makeITEMS = subelement.iteritems # for (key, value) in subelement.iteritems():  # Python 2x
			elif PY3: makeITEMS = subelement.items # for (key, value) in subelement.items():  # Python 3+
			for number,videos in makeITEMS():
				for vid in videos:
					if 'isPlayable' in vid and vid['isPlayable'] == True:
						debug("(listepisodes) ##### subelement-1-vid : "+str(vid)+" #####")
						season = ""
						if 'season' in vid and vid['season'] != "" and vid['season'] != "0" and vid['season'] != None:
							season = str(vid['season']).zfill(2)
						episode = ""
						if 'episode' in vid and vid['episode'] != "" and vid['episode'] != "0" and vid['episode'] != None:
							episode = str(vid['episode']).zfill(2)
						title = py2_enc(vid['title'])
						if (season != "" and season in title) and (episode != "" and episode in title):
							title1 = "[COLOR chartreuse]"+title.split(':')[0].replace('{S}', 'S').replace('.{E}', 'E')+":[/COLOR]"
							title2 = title.split(':')[1]
							number = title.split(':')[0].replace('{S}', 'S').replace('.{E}', 'E')
						else:
							title1 = title
							title2 = ""
							number = ""
						begins = None
						year = None
						startTIMES = None
						endTIMES = None
						Note_1 = ""
						Note_2 = ""
						Note_3 = ""
						if 'publishStart' in vid and vid['publishStart'] != "" and vid['publishStart'] != None and not str(vid['publishStart']).startswith('1970'):
							try:
								startDATES = datetime(*(time.strptime(vid['publishStart'], '%Y-%m-%dT%H:%M:%SZ')[0:6])) # 2019-06-23T14:10:00Z
								LOCALstart = utc_to_local(startDATES)
								startTIMES = LOCALstart.strftime('%d.%m.%y • %H:%M')
								begins =  LOCALstart.strftime('%d.%m.%Y')
							except: pass
						if 'publishEnd' in vid and vid['publishEnd'] != "" and vid['publishEnd'] != None and not str(vid['publishEnd']).startswith('1970'):
							try:
								endDATES = datetime(*(time.strptime(vid['publishEnd'], '%Y-%m-%dT%H:%M:%SZ')[0:6])) # 2019-06-23T14:10:00Z
								LOCALend = utc_to_local(endDATES)
								endTIMES = LOCALend.strftime('%d.%m.%y • %H:%M')
							except: pass
						if 'airDate' in vid and vid['airDate'] != "" and vid['airDate'] != None and not str(vid['airDate']).startswith('1970'):
							year = vid['airDate'][:4]
						if startTIMES: Note_1 = translation(30611).format(str(startTIMES))
						if endTIMES: Note_2 = translation(30612).format(str(endTIMES))
						if 'description' in vid and vid['description'] != "" and vid['description'] != None:
							Note_3 = py2_enc(vid['description']).replace('\n\n\n', '\n\n')
						plot = Note_1+Note_2+Note_3
						image = ""
						if 'image' in vid and 'src' in vid['image'] and vid['image']['src'] != "" and vid['image']['src'] != None:
							image = vid['image']['src']
						idd2 = ""
						if 'id' in vid and vid['id'] != "" and vid['id'] != None:
							idd2 = vid['id']
						else: continue
						duration = int(vid['videoDuration']/1000)
						COMBI.append([number, title1, title2, idd2, image, plot, duration, season, episode, genstr, year, begins])
		if 'standalone' in DATA['videos']:
			subelement = DATA['videos']['standalone']
			for item in subelement:
				if 'isPlayable' in item and item['isPlayable'] == True:
					debug("(listepisodes) ##### subelement-2-item : "+str(item)+" #####")
					season = "00"
					if 'season' in item and item['season'] != "" and item['season'] != "0" and item['season'] != None:
						season = str(item['season']).zfill(2)
					episode = ""
					if 'episode' in item and item['episode'] != "" and item['episode'] != "0" and item['episode'] != None:
						episode = str(item['episode']).zfill(2)
					title = py2_enc(item['title'])
					begins = None
					year = None
					airdate = None
					startTIMES = None
					endTIMES = None
					Note_1 = ""
					Note_2 = ""
					Note_3 = ""
					if 'publishStart' in item and item['publishStart'] != "" and item['publishStart'] != None and not str(item['publishStart']).startswith('1970'):
						try:
							startDATES = datetime(*(time.strptime(item['publishStart'], '%Y-%m-%dT%H:%M:%SZ')[0:6])) # 2019-06-23T14:10:00Z
							LOCALstart = utc_to_local(startDATES)
							startTIMES = LOCALstart.strftime('%d.%m.%y • %H:%M')
							begins =  LOCALstart.strftime('%d.%m.%Y')
						except: pass
					if 'publishEnd' in item and item['publishEnd'] != "" and item['publishEnd'] != None and not str(item['publishEnd']).startswith('1970'):
						try:
							endDATES = datetime(*(time.strptime(item['publishEnd'], '%Y-%m-%dT%H:%M:%SZ')[0:6])) # 2019-06-23T14:10:00Z
							LOCALend = utc_to_local(endDATES)
							endTIMES = LOCALend.strftime('%d.%m.%y • %H:%M')
						except: pass
					if 'airDate' in item and item['airDate'] != "" and item['airDate'] != None and not str(item['airDate']).startswith('1970'):
						year = item['airDate'][:4]
						airdate = item['airDate'][:10]
					if startTIMES: Note_1 = translation(30611).format(str(startTIMES))
					if endTIMES: Note_2 = translation(30612).format(str(endTIMES))
					if 'description' in item and item['description'] != "" and item['description'] != None:
						Note_3 = py2_enc(item['description']).replace('\n\n\n', '\n\n')
					plot = Note_1+Note_2+Note_3
					image = ""
					if 'image' in item and 'src' in item['image'] and item['image']['src'] != "" and item['image']['src'] != None:
						image = item['image']['src']
					idd2 = ""
					if 'id' in item and item['id'] != "" and item['id'] != None:
						idd2 = item['id']
					else: continue
					duration = int(item['videoDuration']/1000)
					SELECT.append([title, idd2, image, plot, duration, season, episode, genstr, year, airdate, begins])
			if SELECT:
				for title, idd2, image, plot, duration, season, episode, genstr, year, airdate, begins in sorted(SELECT, key=lambda ad:ad[9], reverse=False):
					pos1 += 1
					if (season != "00" and season in title) and (episode != "" and episode in title):
						title1 = "[COLOR orangered]"+title.split(':')[0].replace('{S}', 'S').replace('.{E}', 'E')+":[/COLOR]"
						title2 = title.split(':')[1]
						number = title.split(':')[0].replace('{S}', 'S').replace('.{E}', 'E')
					else:
						episode = str(pos1).zfill(2)
						title1 = "[COLOR orangered]S00E"+episode+":[/COLOR]"
						title2 = title+"  (Special)"
						number = "S00E"+episode
					COMBI.append([number, title1, title2, idd2, image, plot, duration, season, episode, genstr, year, begins])
	else:
		debug("(listepisodes) ##### Keine COMBINATION-List - Kein Eintrag gefunden #####")
		return xbmcgui.Dialog().notification(translation(30523), translation(30524).format(originalSERIE), icon, 8000)
	if COMBI:
		if addon.getSetting("sorting") == "1":
			xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
			xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
			xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DURATION)
		else:
			COMBI = sorted(COMBI, key=lambda b:b[0], reverse=True)
		for number, title1, title2, idd2, image, plot, duration, season, episode, genstr, year, begins in COMBI:
			if addon.getSetting("sorting") == "1" and begins:
				xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
			name = title1.strip()+"  "+title2.strip()
			if title2 == "":
				name = title1.strip()
			debug("(listepisodes) ### NAME : "+str(name)+" || IDD : "+str(idd2)+" || GENRE : "+str(genstr)+" ###")
			debug("(listepisodes) ### IMAGE : "+str(image)+" || SEASON : "+str(season)+" || EPISODE : "+str(episode)+" ###")
			addLink(name, idd2, "playvideo", image, plot, duration, seriesname=originalSERIE, season=season, episode=episode, genre=genstr, year=year, begins=begins)
	xbmcplugin.endOfDirectory(pluginhandle)

def playvideo(idd2):
	debug("-------------------------- PLAYVIDEO --------------------------")
	content = getUrl(baseURL)
	for cookief in cj:
		debug("(playvideo) ##### COOKIE : "+str(cookief)+" #####")
		if "sonicToken" in str(cookief):
			key = re.compile('sonicToken=(.*?) for', re.DOTALL).findall(str(cookief))[0]
			break
	playurl = "https://sonic-eu1-prod.disco-api.com/playback/videoPlaybackInfo/"+str(idd2)
	header = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36'), ('Authorization', 'Bearer '+key)]
	result = getUrl(playurl, header=header)
	debug("(playvideo) ##### RESULT : "+str(result)+" #####")
	DATA = json.loads(result)
	videoURL = DATA['data']['attributes']['streaming']['hls']['url']
	log("(playvideo) StreamURL : "+videoURL)
	listitem = xbmcgui.ListItem(path=videoURL)
	listitem.setProperty('IsPlayable', 'true')
	if enableInputstream:
		if ADDON_operate('inputstream.adaptive'):
			licfile = DATA['data']['attributes']['protection']['schemes']['clearkey']['licenseUrl']
			debug("(playvideo) ##### LIC-FILE : "+str(licfile)+" #####")
			licurl = getUrl(licfile, header=header)
			lickey = re.compile('"kid":"(.*?)"', re.DOTALL).findall(licurl)[0]
			debug("(playvideo) ##### LIC-KEY : "+str(lickey)+" #####")
			listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
			listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
			listitem.setProperty('inputstream.adaptive.license_key', lickey)
			listitem.setContentLookup(False)
		else:
			addon.setSetting("inputstream", "false")
	xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)

def listShowsFavs():
	debug("-------------------------- LISTSHOWSFAVS --------------------------")
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
	if os.path.exists(channelFavsFile):
		with open(channelFavsFile, 'r') as textobj:
			lines = textobj.readlines()
			for line in lines:
				if line.startswith('###START'):
					part = line.split('###')
					addDir(name=part[3], url=part[2], mode="listepisodes", iconimage=part[4].strip(), plot=part[5].replace('#n#', '\n').strip(), originalSERIE=part[3], FAVdel=True)
					debug("(listShowsFavs) ##### NAME : "+str(part[3])+" | URL : "+str(part[2])+" #####")
	xbmcplugin.endOfDirectory(pluginhandle)

def favs(param):
	mode = param[param.find('MODE=')+5:+8]
	SERIES_entry = param[param.find('###START'):]
	SERIES_entry = SERIES_entry[:SERIES_entry.find('END###')]
	name = SERIES_entry.split('###')[3]
	url = SERIES_entry.split('###')[2]
	if mode == "ADD":
		if os.path.exists(channelFavsFile):
			with open(channelFavsFile, 'a+') as textobj:
				content = textobj.read()
				if content.find(SERIES_entry) == -1:
					textobj.seek(0,2) # change is here (for Windows-Error = "IOError: [Errno 0] Error") - because Windows don't like switching between reading and writing at same time !!!
					textobj.write(SERIES_entry+'END###\n')
		else:
			with open(channelFavsFile, 'a') as textobj:
				textobj.write(SERIES_entry+'END###\n')
		xbmc.sleep(500)
		xbmcgui.Dialog().notification(translation(30525), translation(30526).format(name), icon, 8000)
	elif mode == "DEL":
		with open(channelFavsFile, 'r') as output:
			lines = output.readlines()
		with open(channelFavsFile, 'w') as input:
			for line in lines:
				if url not in line:
					input.write(line)
		xbmc.executebuiltin('Container.Refresh')
		xbmc.sleep(1000)
		xbmcgui.Dialog().notification(translation(30525), translation(30527).format(name), icon, 8000)

def utc_to_local(dt):
	if time.localtime().tm_isdst: return dt - timedelta(seconds=time.altzone)
	else: return dt - timedelta(seconds=time.timezone)

def parameters_string_to_dict(parameters):
	paramDict = {}
	if parameters:
		paramPairs = parameters[1:].split('&')
		for paramsPair in paramPairs:
			paramSplits = paramsPair.split('=')
			if (len(paramSplits)) == 2:
				paramDict[paramSplits[0]] = paramSplits[1]
	return paramDict

def addDir(name, url, mode, iconimage, plot=None, page=1, position=0, nosub=0, originalSERIE="", addType=0, FAVdel=False):
	u = sys.argv[0]+"?url="+quote_plus(url)+"&name="+quote_plus(name)+"&page="+str(page)+"&position="+str(position)+"&nosub="+str(nosub)+"&originalSERIE="+quote_plus(originalSERIE)+"&mode="+str(mode)
	liz = xbmcgui.ListItem(name, iconImage=icon, thumbnailImage=iconimage)
	liz.setInfo(type='Video', infoLabels={'Title': name, 'Plot': plot})
	liz.setArt({'poster': iconimage})
	if useThumbAsFanart and iconimage != icon:
		liz.setArt({'fanart': iconimage})
	else:
		liz.setArt({'fanart': defaultFanart})
	entries = []
	if addType == 2 and FAVdel == False:
		playListInfos_1 = 'MODE=ADD###START###{0}###{1}###{2}###{3}###END###'.format(url, originalSERIE, iconimage, plot.replace('\n', '#n#'))
		entries.append([translation(30651), 'RunPlugin(plugin://'+addon.getAddonInfo('id')+'/?mode=favs&url='+quote_plus(playListInfos_1)+')'])
	if FAVdel == True:
		playListInfos_2 = 'MODE=DEL###START###{0}###{1}###{2}###{3}###END###'.format(url, name, iconimage, plot)
		entries.append([translation(30652), 'RunPlugin(plugin://'+addon.getAddonInfo('id')+'/?mode=favs&url='+quote_plus(playListInfos_2)+')'])
	liz.addContextMenuItems(entries, replaceItems=False)
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)

def addLink(name, url, mode, iconimage, plot=None, duration=None, seriesname=None, season=None, episode=None, genre=None, year=None, begins=None):
	u = sys.argv[0]+"?url="+quote_plus(url)+"&mode="+str(mode)
	liz = xbmcgui.ListItem(name, iconImage=icon, thumbnailImage=iconimage)
	ilabels = {}
	ilabels['Season'] = season
	ilabels['Episode'] = episode
	ilabels['Tvshowtitle'] = seriesname
	ilabels['Title'] = name
	ilabels['Tagline'] = None
	ilabels['Plot'] = plot
	ilabels['Duration'] = duration
	if begins != None:
		ilabels['Date'] = begins
	ilabels['Year'] = year
	ilabels['Genre'] = genre
	ilabels['Director'] = None
	ilabels['Writer'] = None
	ilabels['Studio'] = 'TLC'
	ilabels['Mpaa'] = None
	ilabels['Mediatype'] = 'episode'
	liz.setInfo(type='Video', infoLabels=ilabels)
	liz.setArt({'poster': iconimage})
	if useThumbAsFanart and iconimage != icon:
		liz.setArt({'fanart': iconimage})
	else:
		liz.setArt({'fanart': defaultFanart})
	liz.addStreamInfo('Video', {'Duration': duration})
	liz.setProperty('IsPlayable', 'true')
	liz.setContentLookup(False)
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)

params = parameters_string_to_dict(sys.argv[2])
name = unquote_plus(params.get('name', ''))
url = unquote_plus(params.get('url', ''))
mode = unquote_plus(params.get('mode', ''))
iconimage = unquote_plus(params.get('iconimage', ''))
page = unquote_plus(params.get('page', ''))
position = unquote_plus(params.get('position', ''))
nosub = unquote_plus(params.get('nosub', ''))
originalSERIE = unquote_plus(params.get('originalSERIE', ''))

if mode == 'aSettings':
	addon.openSettings()
elif mode == 'iSettings':
	xbmcaddon.Addon('inputstream.adaptive').openSettings()
elif mode == 'listthemes':
	listthemes()  
elif mode == 'listseries':
	listseries(url, page, position, nosub)
elif mode == 'listepisodes':
	listepisodes(url, originalSERIE)
elif mode == 'playvideo':
	playvideo(url)
elif mode == 'listShowsFavs':
	listShowsFavs()
elif mode == 'favs':
	favs(url)
else:
	index()