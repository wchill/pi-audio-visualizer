import youtube_dl
import os

# create directory
savedir = "audio"
if not os.path.exists(savedir):
    os.makedirs(savedir)

def make_savepath(filename, savedir=savedir):
    return os.path.join(savedir, "%s.mp3" % (filename))

# create YouTube downloader
options = {
    'format': 'bestaudio/best', # choice of quality
    'extractaudio' : True,      # only keep the audio
    'audioformat' : "mp3",      # convert to mp3
    'outtmpl': '%(id)s',        # name the file the ID of the video
    'noplaylist' : True,}       # only download single song, not playlist
ydl = youtube_dl.YoutubeDL(options)

with ydl:

    link = 'https://www.youtube.com/watch?v=WuvSzfaMXNI'
    # for each row, download
    print "Downloading: %s from %s..." % ('Test1', link)
    result = ydl.extract_info(link, download=False)
    savepath = make_savepath(result['id'])

    # download location, check for progress
    try:
        os.stat(savepath)
        print "%s already downloaded, continuing..." % savepath

    except OSError:
        # download video
        try:
            print 'Downloading {}'.format(result['title'])
            result = ydl.extract_info(link, download=True)
            print result['title']
            os.rename(result['id'], savepath)
            print "Downloaded and converted %s successfully!" % savepath

        except Exception as e:
            print "Can't download audio! %s\n" % traceback.format_exc()
