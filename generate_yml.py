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
	"version: \"2\"\r\n" \
	+ "services:\r\n" \
	+ "  \"1\":\r\n" \
	+ "    extends:\r\n" \
	+ "      file: ./etree.yml\r\n" \
	+ "      service: etree\r\n" \
	+ "    container_name: \"n1\"\r\n" \
	+ "    environment:\r\n" \
	+ "      HOSTNAME: \"n1\"\r\n" \
	+ "    ports:\r\n" \
	+ "      - \"8888:8888\"\r\n"

for i in range (2, n + 1):
	string += "  \"" + str (i) + "\":\r\n" \
	          + "    extends:\r\n" \
	          + "      file: ./etree.yml\r\n" \
	          + "      service: etree\r\n" \
	          + "    container_name: \"n" + str (i) + "\"\r\n" \
	          + "    environment:\r\n" \
	          + "      HOSTNAME: \"n" + str (i) + "\"\r\n"

with open ('run.yml', 'w') as f:
	f.write (string)
