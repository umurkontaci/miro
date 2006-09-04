import re
import httpclient
import urlparse
import cgi
from xml.dom import minidom
from urllib import unquote_plus

# =============================================================================

def tryScrapingURL(url, callback):
    scrape =_getScrapeFunctionFor(url)
    if scrape is not None:
        scrape(url,lambda x:_actualURLCallback(url,callback,x))
    else:
        # print "Not scraping %s" % url
        callback(url)
    
# =============================================================================

# The callback is wrapped in this for flv videos
def _actualURLCallback(url, callback, newURL):
    #print "Changed:"
    #print url
    #print "   to"
    #print newURL
    callback(newURL, contentType = "video/x-flv")


def _getScrapeFunctionFor(url):
    for scrapeInfo in scraperInfoMap:
        if re.compile(scrapeInfo['pattern']).match(url) is not None:
            return scrapeInfo['func']
    return None

def _scrapeYouTubeURL(url, callback):
    httpclient.grabHeaders(url, lambda x:_youTubeCallback(x,callback),
                           lambda x:_youTubeErrback(x,callback))

def _youTubeCallback(info, callback):
    url = info['redirected-url']
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        videoID = params['video_id'][0]
        t = params['t'][0]
        url = "http://youtube.com/get_video.php?video_id=%s&t=%s" % (videoID, t)
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape You Tube Video URL: %s" % url
        callback(None)

def _youTubeErrback(err, callback):
    print "DTV: WARNING, network error scraping You Tube Video URL"
    callback(None)

def _scrapeGoogleVideoURL(url, callback):
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        url = unquote_plus(params['videoUrl'][0])
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape Google Video URL: %s" % url
        callback(None)

def _scrapeLuLuVideoURL(url, callback):
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        url = unquote_plus(params['file'][0])
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape LuLu.tv Video URL: %s" % url
        callback(None)

def _scrapeVMixVideoURL(url, callback):
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        t = params['type'][0]
        ID = params['id'][0]
        l = params['l'][0]
        url = "http://sdstage01.vmix.com/videos.php?type=%s&id=%s&l=%s" % (t,ID,l)
        httpclient.grabURL(url, lambda x:_scrapeVMixCallback(x,callback),
                           lambda x:_scrapeVMixErrback(x,callback))

    except:
        print "DTV: WARNING, unable to scrape VMix Video URL: %s" % url
        callback(None)

def _scrapeVMixCallback(info, callback):
    try:
        doc = minidom.parseString(info['body'])
        url = doc.getElementsByTagName('file').item(0).firstChild.data
        callback(url)
    except:
        print "DTV: WARNING, unsable to scrape XML for VMix Video URL %s" % info['redirected-url']
        callback(None)

def _scrapeVMixErrback(err, callback):
    print "DTV: WARNING, network error scraping VMix Video URL"
    callback(None)

def _scrapeDailyMotionVideoURL(url, callback):
    httpclient.grabHeaders(url, lambda x:_scrapeDailyMotionCallback(x,callback),
                           lambda x:_scrapeDailyMotionErrback(x,callback))

def _scrapeDailyMotionCallback(info, callback):
    url = info['redirected-url']
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        url = unquote_plus(params['url'][0])
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape Daily Motion URL: %s" % url
        callback(None)

def _scrapeDailyMotionErrback(info, callback):
    print "DTV: WARNING, network error scraping Daily Motion Video URL"
    callback(None)

# http://static.vsocial.com/flash/vp.swf?v=5b80f107fce621fad9d059f93f438d85
def _scrapeVSocialVideoURL(url, callback):
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        v = params['v'][0]
        url = 'http://static.vsocial.com/varmedia/vsocial/flv/%s_out.flv' % v
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape VSocial URL: %s" % url
        callback(None)

# http://www.veoh.com/multiplayer.swf?type=v&permalinkId=e106120at7fEmJG&id=244754
def _scrapeVeohTVVideoURL(url, callback):
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        t = params['type'][0]
        permalinkId= params['permalinkId'][0]
        url = 'http://www.veoh.com/movieList.html?type=%s&permalinkId=%s&numResults=45' % (t, permalinkId)
        httpclient.grabURL(url, lambda x: _scrapeVeohTVCallback(x, callback),
                           lambda x:_scrapeVeohTVErrback(x, callback))
    except:
        print "DTV: WARNING, unable to scrape Veoh URL: %s" % url
        callback(None)

def _scrapeVeohTVCallback(info, callback):
    url = info['redirected-url']
    try:
        params = cgi.parse_qs(info['body'])
        fileHash = params['previewHashLow'][0]
        if fileHash[-1] == ",":
            fileHash=fileHash[:-1]
        url = 'http://ll-previews.veoh.com/previews/get.jsp?fileHash=%s' % fileHash
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape Veoh URL data: %s" % url
        callback(None)

def _scrapeVeohTVErrback(err):
    print "DTV: WARNING, network error scraping Veoh TV Video URL"
    callback(None)

def _scrapeBreakVideoURL(url, callback):
    httpclient.grabHeaders(url, lambda x:_scrapeBreakCallback(x,callback),
                           lambda x:_scrapeBreakErrback(x,callback))

def _scrapeBreakCallback(info, callback):
    url = info['redirected-url']
    try:
        components = urlparse.urlsplit(url)
        params = cgi.parse_qs(components[3])
        url = unquote_plus(params['sVidLoc'][0])
        callback(url)
    except:
        print "DTV: WARNING, unable to scrape Break URL: %s" % url
        callback(None)

def _scrapeBreakErrback(info, callback):
    print "DTV: WARNING, network error scraping Break Video URL"
    callback(None)

def _scrapeGreenPeaceVideoURL(url, callback):
    print "DTV: Warning, unable to scrape Green peace Video URL %s" % url
    print callback(None)

# =============================================================================

scraperInfoMap = [
    {'pattern': 'http://([^/]+\.)?youtube.com/',         'func': _scrapeYouTubeURL},
    {'pattern': 'http://video.google.com/googleplayer.swf', 'func': _scrapeGoogleVideoURL},
    {'pattern': 'http://([^/]+\.)?lulu.tv/wp-content/flash_play/flvplayer', 'func': _scrapeLuLuVideoURL},
    {'pattern': 'http://([^/]+\.)?vmix.com/flash/super_player.swf', 'func': _scrapeVMixVideoURL},
    {'pattern': 'http://([^/]+\.)?dailymotion.com/swf', 'func': _scrapeDailyMotionVideoURL},
    {'pattern': 'http://([^/]+\.)?vsocial.com/flash/vp.swf', 'func': _scrapeVSocialVideoURL},
    {'pattern': 'http://([^/]+\.)?veoh.com/multiplayer.swf', 'func': _scrapeVeohTVVideoURL},
    {'pattern': 'http://([^/]+\.)?greenpeaceweb.org/GreenpeaceTV1Col.swf', 'func': _scrapeGreenPeaceVideoURL},
    {'pattern': 'http://([^/]+\.)?break.com/', 'func': _scrapeBreakVideoURL},

]
