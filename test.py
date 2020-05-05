from flask import Flask

app = Flask (__name__)


@app.route ('/test', methods=['GET'])
def route_heart_beat ():
	return 'alive'


app.run (host='0.0.0.0', port=8888, threaded=True, )
