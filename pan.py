import argparse
from datetime import datetime, timedelta
from enum import Enum
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

class DayType(Enum):
	work = 1
	weekend = 2
	vacation = 3
	holiday = 4
	illness = 5
	overtime_free = 6
	business_trip = 7
	
	def __str__(self):
		mapping={'work': 'Arbeitstag',
		'weekend':'Wochenende', 
		'vacation':'Urlaub', 
		'holiday': 'Feiertag', 
		'illness': 'Krankschreibung', 
		'overtime_free': 'Überstundenausgleich', 
		'business_trip': 'Dienstreise'}
		
		ret = mapping[self.name]
		return ret


class WorkDay(object):
	
	def __init__(self, daytype, timeblocks):
		self.daytype = daytype
		self.timeblocks=timeblocks
	
	def __str__(self):
		return "{0} {1}".format(str(self.daytype),str(self.timeblocks))
		


class WorkMonth(object):
	
	def __init__(self, workdays):
		self.workdays = workdays
	
	def __str__(self):
		ret = ""
		for daynumber in self.workdays:
			ret+=('{0}. {1}\n'.format(daynumber, self.workdays[daynumber]))
		return ret
		
			


class PAN(object):

	def __init__(self):
		parser = argparse.ArgumentParser(
				description='Read & analyse XML files of Persönlicher Arbeitszeit-Nachweis (PAN)',
				usage='''pan.py <command> [<args>]
Supported commands are
	check     Check schedule validity for work rules 
''')
		parser.add_argument('command', help='Subcommand to run')
		parser.add_argument('--panconf', help='absolute filepath to pan.xml configfile', required=False)
		parser.add_argument('--xmlmonth', help='absolute filepath to pan_....xml monthfile', required=False)
		
		args = parser.parse_args()
		if not hasattr(self, args.command):
			print('Unrecognized command')
			parser.print_help()
			exit(1)
		if hasattr(args, 'panconf'):
			getattr(self, args.command)(confFilename=args.panconf)
		if hasattr(args, 'xmlmonth'):
			getattr(self, args.command)(monthXMLFilename=args.xmlmonth)
		else:
			getattr(self, args.command)()
	
	def check(self, confFilename=None, monthXMLFilename=None):
		print('\n-----Prüfung-----')
		if monthXMLFilename is None:
			settings = self.__getPanSettings(confFilename)
			if settings is not None:
				print('{}'.format(settings['fullname']))
		else:
			print('{}'.format(monthXMLFilename))
			xml = self.__openMonthXMLFile(monthXMLFilename)
			month = self.__getMonth(xml)
			print(month)
		
	
	def __getPanSettings(self, confFilename = None):
		if confFilename is None:
			confFilename = Path.home() / 'pan.xml'
		try:
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
		except FileNotFoundError:
			print('No pan.xml config file found: {0}\nPlease start PAN application for a first run.'.format(confFilename))
			settings = None
		return settings
	
	def __openMonthXMLFile(self, filename):
		tree = ET.parse(filename)
		return tree.getroot()
	
	def __getMonth(self,xml):
		"""Parse PAN XML month file and get internal representation of day items"""
		#TODO: Monat, Jahr, SollStunden, Urlaub,ZeitdiffAkt, ZeitdiffVor, erweitert
		dayTypeMapping = {'Arbeitstag': DayType.work,
						'Wochenende': DayType.weekend,
						'Urlaub': DayType.vacation,
						'Feiertag': DayType.holiday,
						'Krankheit': DayType.illness,
						'Überstunden genommen': DayType.overtime_free,
						'Dienstreise': DayType.business_trip}
		workdays = {}
		for panday in xml.findall('Tag'):
			# parse
			numday = int(panday.find('Datum').text)
			daytype = panday.find('TagesTyp').text
			description = panday.find('Bemerkung').text
			morning = panday.find('Vormittag').text
			afternoon = panday.find('Nachmittag').text
			third = panday.find('Dritte').text
			fourth = panday.find('Vierte').text
			# convert
			daytype = dayTypeMapping[daytype]
			morning = self. _parsePANTimeRange(morning)
			afternoon = self. _parsePANTimeRange(afternoon)
			third = self. _parsePANTimeRange(third)
			fourth = self. _parsePANTimeRange(fourth)			
			timeblocks = [morning, afternoon, third, fourth]
			timeblocks = list(filter(None, timeblocks))
			# save
			day = WorkDay(daytype, timeblocks)
			workdays[numday] = day
		month = WorkMonth(workdays)
		return month
			
	
	def _parsePANTimeRange(self,strDayRange):
		#deconstruct '09:00 - 12:30'
		FMT = '%H:%M'
		try:
			begin, end = strDayRange.split(' - ')
			begin = datetime.strptime(begin, FMT)
			end = datetime.strptime(end, FMT)
			return begin, end
		except AttributeError:
			return None
			
		
		

if __name__ == '__main__':
	PAN()
