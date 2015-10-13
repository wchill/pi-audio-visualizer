from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from flask import Flask, request, jsonify
from youtube_dl import YoutubeDL

app = Flask(__name__)

@app.route('/next-track')
def next_track():
    return send_file('audio/sample.mp3')

from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
site = Site(resource)

class SocketServer(LineReceiver):

    def __init__(self):
        pass

    def lineReceived(self, data):
        pass

    def connectionMade(self):
        peer = self.transport.getPeer()
        print 'Client {0}:{1} connected'.format(peer.host, peer.port)

    def connectionLost(self, reason):
        peer = self.transport.getPeer()
        print 'Client {0}:{1} disconnected'.format(peer.host, peer.port)

class SocketServerFactory(Factory):

    protocol = SocketServer

if __name__ == '__main__':
    reactor.listenTCP(9001, site)
    reactor.listenTCP(9002, SocketServerFactory())
    reactor.run()
    # app.run(host='0.0.0.0', port=9001)
