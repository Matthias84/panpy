import argparse
from datetime import datetime, timedelta
from enum import Enum
import xml.etree.ElementTree as ET
from pathlib import Path
from printy import printy
import re
import sys


"""
PAN.py - Read & analyse XML files of Persönlicher Arbeitszeit-Nachweis (PAN)

PAN is a JAVA desktop software to log your working times.
Data is stored in a custom XML file format.


#TODO:
- pan.py check (current, month/year, xmlfilename, path)
- pan.py show (current, month/year, xmlfilename, path)
- pan.py email-lock-import imapserver imapaccount imappassword imapfolder - manual sync with all 
- pan.py pdf (current, month/year, xmlfilename, path)- generate PDF with original PAN layout
- pan.py plot (current, month/year, xmlfilename, path)
- Error checking on time formats and logic ... asumptions

"""

def prRed(skk): print("\033[91m{}\033[00m" .format(skk)) 
def prGreen(skk): print("\033[92m{}\033[00m" .format(skk)) 
def prYellow(skk): print("\033[93m{}\033[00m" .format(skk)) 
def prLightPurple(skk): print("\033[94m{}\033[00m" .format(skk)) 
def prPurple(skk): print("\033[95m{}\033[00m" .format(skk)) 
def prCyan(skk): print("\033[96m{}\033[00m" .format(skk)) 
def prLightGray(skk): print("\033[97m{}\033[00m" .format(skk)) 
def prBlack(skk): print("\033[98m{}\033[00m" .format(skk)) 
def prBold(skk): print("\033[01m{}\033[00m" .format(skk)) 
def prItalic(skk): print("\33[3m{}\033[00m" .format(skk)) 

FMT = '%H:%M'

class DayType(Enum):
	work = 1
	weekend = 2
	vacation = 3
	holiday = 4
	illness = 5
	overtime_free = 6
	business_trip = 7
	unpaid_free = 8
	
	def __str__(self):
		mapping={'work': 'Arbeitstag',
		'weekend':'Wochenende', 
		'vacation':'Urlaub', 
		'holiday': 'Feiertag', 
		'illness': 'Krankschreibung', 
		'overtime_free': 'Überstundenausgleich', 
		'business_trip': 'Dienstreise',
		'unpaid_free': 'Freistellung'}
		
		ret = mapping[self.name]
		return ret


class WorkDay(object):
	
	def __init__(self, daytype, description, timeblocks):
		self.daytype = daytype
		self.description = description
		self.timeblocks=timeblocks
	
	def check(self, num):
		fails = 0
		worktime = self.getWorkingTime()
		pausetime = self.getPauseTime()
		# rule max. worktime day
		if worktime > timedelta(hours=10):
			prRed('{:02d}. max. Arbeitszeit überschritten ({} > 10hrs)'.format(num, worktime))
			fails += 1
		# rule min. pausetime day
		if worktime <= timedelta(hours=9):
			if pausetime < timedelta(minutes=30):
				prRed('{:02d}. min. Pausenzeit unterschritten ({} < 30mins)'.format(num, pausetime))
				fails += 1
		else:
			if pausetime < timedelta(minutes=45):
				prRed('{:02d}. min. Pausenzeit unterschritten ({} < 45mins)'.format(num, pausetime))
				fails += 1
		# Check servicetimes
		serviceBegin = datetime.strptime('09:00', FMT)
		serviceEnd = datetime.strptime('15:00', FMT)
		amBegin = self.timeblocks[0][0]
		pmEnd = self.timeblocks[-1][1]
		if not ((amBegin <= serviceBegin) and (pmEnd >= serviceEnd)):
			prCyan('! {:02d}. Servicezeit potentiell nicht eingehalten ({} - {})'.format(num, amBegin.strftime(FMT), pmEnd.strftime(FMT)))
		# rule max. homeoffice
		hotime = self.getHomeofficeTime()
		if (hotime > timedelta(hours=8)):
			prRed('! {:02d}. max. Heimarbeit überschritten ({} <= 8hrs)'.format(num, worktime))
			fails += 1
		return fails
	
	def getWorkingTime(self):
		worktime = timedelta(hours=0)
		for block in self.timeblocks:
			worktime += block[1] - block[0]
		return worktime

	def getPauseTime(self):
		pausetime = timedelta(hours=0)
		pausetime = self.timeblocks[1][0]-self.timeblocks[0][1]
		if len(self.timeblocks) > 2:
			pausetime += self.timeblocks[2][0]-self.timeblocks[1][1]
		if len(self.timeblocks) == 4:
			pausetime += self.timeblocks[3][0]-self.timeblocks[2][1]
		return pausetime
	
	def getHomeofficeTime(self):
		if self.description:
			if self.description.lower().find('homeoffice') != -1:
				# Check if provide a percentage e.g. '0.5 Homeoffice')
				perc = re.match('\d+\.\d+', self.description)
				if perc:
					perc = float(perc.group(0))
					hotime = self.getWorkingTime() * perc
				else:
					hotime = self.getWorkingTime()
				return hotime
			else:
				return timedelta(hours=0)
		else:
			return timedelta(hours=0)
		
	
	def __str__(self):
		return "{0} {1}".format(str(self.daytype),str(self.timeblocks))
		


class WorkMonth(object):
	
	def __init__(self, workdays):
		self.workdays = workdays
		
	def check(self):
		"""Check rules on worktime month, day and print errors"""
		fails = 0
		worktime_month = timedelta(hours=0)
		worktime_homeoffice = timedelta(hours=0)
		for num in self.workdays:
			day = self.workdays[num]
			if day.daytype == DayType.work:	
				fails += day.check(num)
				worktime = day.getWorkingTime()
				worktime_month += worktime
				hotime = day.getHomeofficeTime()
				worktime_homeoffice += hotime
				
		if (worktime_homeoffice > timedelta(days=10)):
			prRed('! {:02d}. max. mtl. Heimarbeit überschritten ({} <= 10days)'.format(num, worktime))
			fails += 1
		print('----------------')
		if fails == 0:
			prGreen('Keine Verstöße erkannt')
		else:
			prRed('{0} Verstöße erkannt'.format(fails))					
	
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
			month.check()
		
	
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
						'Dienstreise': DayType.business_trip,
						'Freistellung': DayType.unpaid_free}
		workdays = {}
		if xml.find('Erweitert').text == 'true':
			extendedFormat = True
		else:
			extendedFormat = False
		for panday in xml.findall('Tag'):
			# parse
			numday = int(panday.find('Datum').text)
			daytype = panday.find('TagesTyp').text
			description = panday.find('Bemerkung').text
			morning = panday.find('Vormittag').text
			afternoon = panday.find('Nachmittag').text
			if extendedFormat:
				third = panday.find('Dritte').text
				fourth = panday.find('Vierte').text
			else:
				third = None
				fourth = None
			# convert
			daytype = dayTypeMapping[daytype]
			morning = self. _parsePANTimeRange(morning)
			afternoon = self. _parsePANTimeRange(afternoon)
			third = self. _parsePANTimeRange(third)
			fourth = self. _parsePANTimeRange(fourth)			
			timeblocks = [morning, afternoon, third, fourth]
			timeblocks = list(filter(None, timeblocks))
			# save
			day = WorkDay(daytype, description, timeblocks)
			workdays[numday] = day
		month = WorkMonth(workdays)
		return month
			
	
	def _parsePANTimeRange(self,strDayRange):
		#deconstruct '09:00 - 12:30'
		try:
			begin, end = strDayRange.split(' - ')
			begin = datetime.strptime(begin, FMT)
			end = datetime.strptime(end, FMT)
			return begin, end
		except AttributeError:
			return None
			
		
		

if __name__ == '__main__':
	PAN()
