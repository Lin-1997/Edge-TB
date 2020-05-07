import getopt
import sys

n = 0
try:
	options, args = getopt.getopt (sys.argv [1:], 'n:', ['number='])
except getopt.GetoptError:
	sys.exit ()

for option, value in options:
	if option in ('-n', '--number'):
		n = int (value)

string = \
	"version: \"2\"\n" \
	+ "services:\n" \
	+ "  \"0\":\n" \
	+ "    extends:\n" \
	+ "      file: ./etree.yml\n" \
	+ "      service: etree\n" \
	+ "    container_name: \"node0\"\n" \
	+ "    env_file:\n" \
	+ "      - env/0.env\n" \
	+ "    ports:\n" \
	+ "      - \"8888:8888\"\n"

for i in range (1, n):
	string += "  \"" + str (i) + "\":\n" \
	          + "    extends:\n" \
	          + "      file: ./etree.yml\n" \
	          + "      service: etree\n" \
	          + "    container_name: \"node" + str (i) + "\"\n" \
	          + "    env_file:\n" \
	          + "      - env/" + str (i) + ".env\n"

with open ('run.yml', 'w') as f:
	f.write (string)
