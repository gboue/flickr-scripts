#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
	tagimportr allows to tag your flickr photos from their exif and geo data.
	
	Usage:
		./tagimportr 				list the sets
		./tagimportr -n 5			list the 5 first sets
		./tagimportr 1221929129		tag the photos in the set 1221929129
	
	Colophon:
		
		flickrapi is as a flickr client
		
			get_token_part_one, get_token_part_two for the authentication
			photosets_getList
			photosets_getPhotos
			photos_getExif
			photos_geo_getLocation
			photos_addTags
		
		elementtree helps parse the result from this client
		google reverse geoencoding is used for translating the coordinates into a humann readable data
		optparse for the command line
	
	Author: Guillaume BOUÉ
	Creation Date : 2010-01-16
	Version: 1
"""

import flickrapi
import elementtree

import sys
import re
import urllib, urllib2
import xml.dom.minidom
from optparse import OptionParser

# VAR AND CONSTANTS 
# =================

# tagimportr version
VERSION = "1.0"

# For debug purposes print aditional info when True
debug = False

# Reverse Geocoding : translating a point into a human-readable address
# http://code.google.com/intl/fr/apis/maps/documentation/geocoding/#ReverseGeocoding
REVERSE_GEO_URL='http://maps.google.com/maps/geo?q=%s,%s&output=json&sensor=false&key=%s'

# Locality pattern
LOCALITY_REGEXP = u"""".*LocalityName" : "(.*?)\""""

# Country pattern
COUNTRY_REGEXP = u"""".*CountryName" : "(.*?)\""""

# basic month list
MONTH_LIST = ['January','February','March','April','May','June','July','August','September','October','November','December']

# MAIN CLASS
# ==========

class TagImportR():
	"""
	TagImportR provides three methods
	- init_flickr for initializing the flickr client
	- 
	"""
	flickr = None
	user_id = ""
	gmap_api_key = ""

	def __init__(self, api_key, secret, user_id, gmap_api_key):
		"""
		Delegate the initialization of the flickr client
		
		Args:
			api_key -- flickr api key 
			secret  -- 
			user_id --
			gmap_api_key --
		"""
		
		print "TagImportR for user %s " % user_id
		
		# 1. init flickr client
		self.init_flickr(api_key,secret)
		
		# 2. init other variables
		self.user_id = user_id
		self.gmap_api_key = gmap_api_key



	def init_flickr(self, api_key, secret):
		"""
		Initialize the flickr client
		
		Args:
			api_key
			secret
		"""
	
		self.flickr = flickrapi.FlickrAPI(api_key, secret)

		(token, frob) = self.flickr.get_token_part_one(perms='write')
		if not token: raw_input("Press ENTER after you authorized this program")
		self.flickr.get_token_part_two((token, frob))



	@classmethod
	def get_url_data(self,url):
		"""
		Get url data fetches all the data from an url
		utf-8 conversion is applied
		"""
		if debug:
			print "Fetch data from url %s" % url
	
		# 1. Get info and data regarding that url
		u = urllib2.urlopen(url)
		data = u.read()
		info = u.info()
		u.close()
	
		# 2. utf8 conversion
		charset = "utf-8"    
		ignore, charset = info['Content-Type'].split('charset=')
		data = data.decode(charset).encode('utf-8')  
		
		if debug:
			print "Data for url %s ==> %s " % (url,data,)

		return data



	def list_photosets(self,limit=0):
		"""
		List the photosets
		"""
		photosets = self.flickr.photosets_getList()
	
		if (limit == 0 ):
			limit = len(photosets[0])
	
		for photoset in photosets[0][:limit]:
			print "%s ==> %s " % (photoset.get("id") , photoset[0].text)

	def tag_photos(self, set_id):
		"""
		Tag the photos of a user in a particular set
		
		Args:
		set_id 
		"""
		# 1. Get all photos for the given set
		photos = self.flickr.photosets_getPhotos(user_id=self.user_id, photoset_id=set_id)
	
		# 2. For each photo ...
		for photo in photos[0]:
			
			print "Import for %s ==> %s " %  (photo.get('id'), photo.get('title'),)
		
			# 2.1 Get the exif data for a photo photo_id
			# ------------------------------------------
			photo_id = photo.get('id')
			
			exifs = self.flickr.photos_getExif(photo_id=photo_id)
		
			tags = []
			tagMap = {}
		 
			# 2.2 Fetch only the exif data we are interested into
			# ---------------------------------------------------
			for exif in exifs[0]:
			
				# 2.2.1 get the first row only ... 
				#       the second row is for clean data 
				#              (format in which we are interedted only for a few values)
				data = exif[0]
			
				# 2.2.2 filter depending on tag and tagspace
				tagspace = exif.get("tagspace")
				tag = exif.get('tag')
				
				# 2.2.3 actual filtering is here :
				value = data.text
				if (tagspace, tag) in [('IFD0','Model'),('XMP-aux','Lens')] or \
					(tagspace == 'ExifIFD' and tag in ['ExposureTime','ExposureProgram','ISO','FNumber','FocalLength','DateTimeOriginal']) or\
					tag in ['ImageWidth','ImageHeight'] or\
					tag in ['33434','33437','37386','272','36867']:
				
					tagMap[tag] = data.text
					tags.append(data.text)
				
					if (debug):
						print exif.get("tagspace") + " | " + exif.get('tag') + " " + data.text 
			
				# 2.2.4 for two values we are interested in the clean data
			
				# f/5.6
				if (tag == '33437'):
					tagMap[tag] = exif[1].text
				
				# 5.8mm
				if (tag == '37386'):
					tagMap[tag] = exif[1].text
			
				# 2.2.5 data duplication for original date
			
				# original date 
				if (tag == '36867'):
					tagMap['DateTimeOriginal'] = tagMap[tag]	
				
			
			# 2.3 Format some tag data, add or remove them
			# ---------------------------------------------------
		
			key = 'ISO'
			if (key in tagMap):
				tagMap[key] = "ISO %s" % tagMap[key]
			
			key = 'FNumber'
			if (key in tagMap):
				tagMap[key] = "f/%s" % tagMap[key]
			
			key = 'ExposureTime'
			if (key in tagMap):
				tagMap[key] = "%s sec" % tagMap[key]
			
			key = '33434'
			if (key in tagMap):
				tagMap[key] = "%s sec" % tagMap[key]
			
			key = 'Lens'
			if (key in tagMap):
				tagMap[key] = "Lens %s" % tagMap[key]
		
			key = 'ExposureProgram'
			if (key in tagMap and tagMap[key] == 'Not Defined'):
				del tagMap[key]
			
			key = 'DateTimeOriginal'
			if (key in tagMap ):
				data = tagMap[key].split(':')
				tagMap['Year'] = data[0]
				month = int(data[1]) 
				tagMap['Month'] = MONTH_LIST[month -1]
		
			# 2.4 Add some tag data depending on the image dimension
			# ------------------------------------------------------
		
			if ('ImageWidth' in tagMap and 'ImageHeight' in tagMap):
				w = int(tagMap['ImageWidth'])
				h = int(tagMap['ImageHeight'])
			
				formats = []
				SQUARE_FACTOR = 80
			
				if (w == h):
					formats.append('Square Format')
				elif (w < h):
					formats.append('Portrait Format')
					if (100 * w / h > SQUARE_FACTOR):
						formats.append('Almost Square Format')
				elif (h < w):
					formats.append('Landscape Format')
					if (100 * h / w > SQUARE_FACTOR):
						formats.append('Almost Square Format')
					
				tagMap['Format'] = formats
			
			# 2.5 Add  tags depending on geolocation atrtibutes
			# ------------------------------------------------------

			try:
				
				info = self.flickr.photos_geo_getLocation(photo_id=photo_id)
				lat = info[0][0].get('latitude')
				lon = info[0][0].get('longitude')
			
				url = REVERSE_GEO_URL % (lat, lon, self.gmap_api_key)
			
				data = TagImportR.get_url_data(url)
			
				# Locality
				r = re.compile(LOCALITY_REGEXP, re.DOTALL | re.MULTILINE | re.UNICODE)
				str = re.search(r, data)
				if str:
					tagMap['Locality'] = str.group(1).strip()
		
				#CountryName	
				r = re.compile(COUNTRY_REGEXP, re.DOTALL | re.MULTILINE | re.UNICODE)
				str = re.search(r, data)
				if str:
					tagMap['Country'] = str.group(1).strip()
			
			except (Exception):
				print "No Geo data available"
	
		
			# 2.6 Prepare and add the tags to the photo
			# ------------------------------------------------------
		
			newTags = ''
			for key in ['ExposureTime','33434','FNumber','33437', 'FocalLength', '37386', 'ExposureProgram', \
						'ISO', 'Lens','Format','Model','272','Locality','Country', 'Month','Year']:
			
				if key in tagMap:
					if key == 'Format':
						nextValue = ",".join(tagMap[key])
					else:
						nextValue = tagMap[key]
		
					if newTags != "" and nextValue !="":
						newTags = newTags + ","
					
					newTags = newTags + nextValue
		
			if 	newTags != '':
				newTags = newTags + ",gbo:tagged=1"
				
				print "Tags to be added : %s" % newTags
				
				self.flickr.photos_addTags(tags=newTags, photo_id=photo_id)
				
				print "Tags added"


	def importr(self):
	
	
		photosets = self.flickr.photosets_getList(user_id=self.user_id)
		print photosets
		

def main():
	
	tag_importr = None
	
	usage = "usage: %prog [options] <set_id> if no <set_id> is provided we assume the list of set is requested"
	parser = OptionParser(usage=usage, version="%%prog %s" % VERSION)
	parser.add_option("-n", type="int", dest="limit", help='Limit the set result to this number', default=0)
	parser.add_option("-l", dest="shall_list_set", help='Explicit set search', action="store_true")
	
	parser.add_option("--flickr_api_key", dest="flickr_api_key", help='Flickr Api Key', action="store_const")
	parser.add_option("--flickr_secret", dest="flickr_secret", help='Flickr secret', action="store_const")
	parser.add_option("--flickr_user_id", dest="flickr_user_id", help='Flickr user id', action="store_const")
	parser.add_option("--gmap_api_key", dest="gmap_api_key", help='Google Map Key', action="store_const")
	
	(options, args) = parser.parse_args()

	try:
		import settings
	except :
		print "Unexpected error:", sys.exc_info()[0]
		print "No settings file defined"
		
	tag_importr = TagImportR(settings.FLICKR_API_KEY, \
							 settings.FLICKR_SECRET, \
							 settings.FLICKR_USER_ID, \
							 settings.GMAP_API_KEY )

	
	l = len(args)
	if l < 1 or options.shall_list_set :
		tag_importr.list_photosets(options.limit)
	elif l == 1:	
		tag_importr.tag_photos(args[0])
	else:
		parser.error("incorrect number of arguments")

if __name__ == '__main__':
	main()
