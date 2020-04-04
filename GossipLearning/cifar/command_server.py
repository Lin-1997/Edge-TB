import requests
from flask import Flask
import getopt
import sys

client_num = 3
start_address = 9990

try:
    options, args = getopt.getopt(sys.argv[1:], "n:", ["client_num="])
except getopt.GetoptError:
    sys.exit()


for option, value in options:
    if option in ("-n", "--client_num"):
        client_num = int(value)
if len(args) > 0:
    print("error args: {0}".format(args))

app = Flask(__name__)

all_addresses = []
for client_index in range(client_num):
    all_addresses.append(9990 + client_index)

@app.route('/start', methods=['GET'])
def start():
    for client_index in range(len(all_addresses)):
        requests.post("http://localhost:" + str(all_addresses[client_index]) + "/start_training")
    return 'start'

app.run(port=8888)