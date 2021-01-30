import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import sys


"""
PAN.py - Read & analyse XML files of Persönlicher Arbeitszeit-Nachweis (PAN)

PAN is a JAVA desktop software to log your working times.
Data is stored in a custom XML file format.


#TODO:
- pan.py check (current, month/year, xmlfilename)
- pan.py show (current, month/year, xmlfilename)
- pan.py email-lock-import imapserver imapaccount imappassword imapfolder - manual sync with all 
- pan.py pdf (current, month/year, xmlfilename)- generate PDF with original PAN layout
- pan.py plot (current, month/year, xmlfilename)

"""

class PAN(object):

	def __init__(self):
		parser = argparse.ArgumentParser(
				description='Read & analyse XML files of Persönlicher Arbeitszeit-Nachweis (PAN)',
				usage='''pan.py <command> [<args>]
Supported commands are
	check     Check schedule validity for work rules 
''')
		parser.add_argument('command', help='Subcommand to run')
		args = parser.parse_args(sys.argv[1:2])
		if not hasattr(self, args.command):
			print('Unrecognized command')
			parser.print_help()
			exit(1)
		getattr(self, args.command)()
	
	def check(self):
		print('\n\n------Prüfung-----')
		try:
			settings = self.__getPanSettings()
		except FileNotFoundError:
			print('No pan.xml config file found! Please start PAN application for a first run.')
		
	
	def __getPanSettings(self, confFilename = Path.home() / 'pan.xml'):
		confTree = ET.parse(confFilename)
		properties = confTree.getroot()
		settings = {}
		for entry in properties.findall('entry'):
			key = entry.get('key')
			if key == 'verzeichnis':
				settings['schedulepath'] = Path(entry.text) / '\pan'
			elif key == 'username':
				settings['fullname'] = entry.text
			elif key == 'abteilung':
				settings['department'] = entry.text
			elif key == 'uid':
				settings['userlogin'] = entry.text
		return settings

if __name__ == '__main__':
	PAN()
