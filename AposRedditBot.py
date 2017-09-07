import praw
import time
import sys
import simplejson as json
import pycurl
from io import BytesIO
import arrow
import requests

from AposRedditBotSettings import APP_ID, APP_SECRET, APP_URI, APP_REFRESH, USERAGENT, SUBREDDIT, CLIENTID, PASSWORD
from AposStreamerRules import streamerList, gameName, textInTitle, offlineMessage, onlineMessage

def login():
    r = praw.Reddit(client_id=APP_ID, client_secret=APP_SECRET, refresh_token=APP_REFRESH, user_agent=USERAGENT)

    print("Logged in")

    return r

def getStreamInfo(channel):
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://api.twitch.tv/kraken/streams/{}?oauth_token={}'.format(channel, PASSWORD))
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()

    parsed = json.loads(body.decode('utf8'))

    #print (json.dumps(parsed, indent=4, sort_keys=True))

    return parsed

def isStreamOnline(stream):
    try:
        if stream['stream'] is not None:
            streamUptime = stream['stream']['created_at']
            dt = arrow.get(streamUptime)
            uptime = arrow.utcnow() - dt
            hourString = "hour" if (uptime.seconds // 3600) == 1 else "hours"
            minuteString = "minute" if ((uptime.seconds // 60) % 60) == 1 else "minutes"
            secondString = "second" if (uptime.seconds % 60) == 1 else "seconds"

            dateMessage = "The stream has been up for {} {}, {} {} and {} {}!".format(uptime.seconds // 3600, hourString,
                                                                                      (uptime.seconds // 60) % 60,
                                                                                      minuteString, (uptime.seconds % 60),
                                                                                      secondString)
            print(dateMessage)
            print(stream['stream']['preview']['medium'])
            print(stream['stream']['channel']['status'])
            return True
            #writeMessage(dateMessage, channel)
        else:
            #print ("Stream is offline")
            return False
            #writeMessage("Stream is offline", channel)
    except:
        print("Stream is offline")
        return False

def changeSidebar(r, s, t):
    r.subreddit(s).mod.update(description=t)
    print("Sidebar updated")

def loadSidebar():
    with open('Sidebar.txt', 'r', encoding='utf-8') as sidebartext:
        data = sidebartext.read()
        return data

def loadStylesheet():
    with open('Stylesheet.txt', 'r', encoding='utf-8') as stylesheetText:
        data = stylesheetText.read()
        return data

def downloadTwitchThumb(stream, index):
    f = open('thumb%s.jpg' % index,'wb')
    f.write(requests.get(stream['stream']['preview']['medium']).content)
    f.close()

def uploadImage(r, s, name, path):
    r.subreddit(s).stylesheet.upload(name, path)

def setStreamThumb(r, s, stream, index):
    downloadTwitchThumb(stream, index)
    print("Got new thumb.")
    try:
        uploadImage(r, s, 'thumb%s' % index, 'thumb%s.jpg' % index)
        print("Uploaded new thumb!")
    except:
        print("Couldn't upload the new thumb...", sys.exc_info()[0])

r = login()

sidebar = loadSidebar()
stylesheet = loadStylesheet()

while True:
    newSidebar = ""

    streamList = []

    index = 0

    for i in streamerList:
        try:
            streamer = getStreamInfo(i)

            if isStreamOnline(streamer):
                stream_game = streamer['stream']['channel']['game']
                stream_name = streamer['stream']['channel']['display_name']
                stream_status = streamer['stream']['channel']['status']
                stream_url = streamer['stream']['channel']['url']
                stream_viewers = streamer['stream']['viewers']

                if stream_game == gameName and textInTitle in stream_status.lower():
                    setStreamThumb(r, SUBREDDIT, streamer, index)
                    streamList.append("  * [%s: %s](%s) %s viewers" % (stream_name, stream_status, stream_url, stream_viewers))
                    index += 1
        except:
            print("Couldn't reach Twitch API.")
    print("Checked all streamers.")

    if len(streamList) == 0:
        newSidebar = "%s\n%s" % (sidebar, offlineMessage)
    else:
        newSidebar = "%s\n%s" % (sidebar, onlineMessage) 
    try:
        changeSidebar(r, SUBREDDIT, "%s\n%s" % (newSidebar, "\n".join(streamList)))
    except:
        print("Errored out of the Sidebar.")

    if len(streamList) != 0:
        try:
            print("Trying to reset Stylesheet.")
            r.subreddit(SUBREDDIT).stylesheet.update(stylesheet)
            print("Stylesheet was reset!")
        except:
            print("Error trying to reset Stylesheet.")

    print("Loop done")
    time.sleep(90)

print("Done")
