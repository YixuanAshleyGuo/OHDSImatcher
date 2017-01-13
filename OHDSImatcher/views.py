from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from .forms import XMLInputForm
import requests,urllib,json
from xmljson import badgerfish as bf
from xml.etree import ElementTree as ET
import re

def index(request):
	ohdsiconcept = {}
	counts_orig = {'count':[]}
	primary_criteria = {
		"CriteriaList":[],
		"ObservationWindow":{
			"PriorDays":0,
			"PostDays":0
		},
		"PrimaryCriteriaLimit":{
			"Type": "All"
		}
	}
	additional_criteria = {
		"Type": "ALL",
		"CriteriaList":[],
		"DemographicCriteriaList": [],
		"Groups": []
	}
	if request.method == 'POST':
		xmlform = XMLInputForm(data = request.POST)
		print("about to validate form")
		# print(request.POST)
		if xmlform.is_valid():
			print("form is valid")
			data = xmlform.cleaned_data
			# for temp use, should be removed later
			# inputdata = '<root>'++'</root>'
			root = ET.fromstring(data['xmlinput'])
			js = json.dumps(bf.data(root), indent=4, sort_keys=True)
			js_obj = json.loads(js)
			# prepare to send http request
			headers = {'content-type': 'application/json'}
			#########################################
			# PART I: get the vocabulary
			# iterate the json object and add attribute Concept ID in the json object
			# Request URL:http://54.242.168.196/WebAPI/JNJL/vocabulary/search/drug%20allergies
			# Request Method:POST
			# url_con = "http://discovery.dbmi.columbia.edu:8080/WebAPI/Synpuf-1-Percent/vocabulary/search"
			url_con = "http://54.242.168.196/WebAPI/JNJL/vocabulary/search"
			#define the result variable
			ohdsi = {'ConceptSets':[]}

			cnt = 0
			if js_obj.get('root') and js_obj['root'].get('sent'):
				if type(js_obj['root']['sent']) == list:
					single0 = 0
				else:
					single0 = 1
				for itrs in js_obj['root']['sent']:
					if single0 == 1 or (itrs.get('entity')):
						if single0 == 1:
							itrs = js_obj['root']['sent']

						if type(itrs['entity']) == list:
							single1 = 0
							print "single entity is not true"
						else:
							single1 = 1
							print "single entity is true"

						for itr in itrs['entity']:
							# itr = itrs['entity'][i]
							# i += 1
							# print 'Concept:', itr['$'], ' ID:', itr['@class']
							if single1 == 1:
								itr = itrs['entity']

							params = {
								"QUERY": itr['$'],
								"DOMAIN_ID": [itr['@class']]
							}

							# request url method
							response = requests.post(url_con, data=json.dumps(params), headers=headers)
							# print "url_con response text: ", response.text
							concepts = []
							if response.text == '[]':
								# safe = '' is for encoding the / in string
								urlvalue = urllib.quote(itr['$'],safe='')
								urls = url_con + "/" + urlvalue
								print "try dropping off the domain: ", urls
								response = urllib.urlopen(urls)
								try:
									concepts = json.loads(response.read().decode('utf-8')) # response.info().get_param('charset')))
								except ValueError:
									print(itr['$'],' is not matched')
							else:
								concepts = json.loads(response.text)
								print "concept is matched  at first attempt"


							# substring match algorithm
							# try to drop word from the string, once match is found, use the substring for concept match
							if concepts == []:
								istr = itr['$']
								# if the sentence include () remove the words in ()
								print('before remove (): ', istr)
								istr = re.sub('\(.*?\)','',istr)
								print('after remove (): ',istr)
								# remove and, or, / in the string
								istr = re.sub('/',' ', istr)
								istr = re.sub(' and ',' ',istr)
								istr = re.sub(' or ',' ', istr)

								# remove the leading Modified, and tailing smaller
								# this problem is a remaining problem that the parser
								# did not recognize the modifier and measurement word
								istr = re.sub('Modified', '', istr)
								istr = re.sub('smaller','',istr)

								# change multiple space into single space
								istr = re.sub(' +',' ', istr).strip()
								print('after remove and or /: ', istr)

								# substring match
								# first, remove one word;
								# then, remove two words;
								# etc...
								concepts = ohdsirequest(istr, itr['@class'])
								if concepts == []:
									words = istr.split()
									lens = len(words)
									# for single word removal, try to remove each word
									for word in words:
										# if word end with 's', remove s to see if match is find
										if word.endswith('s'):
											word_new = word[:-1]
											istr0 = istr.replace(word,word_new)
											concepts = ohdsirequest(istr0,itr['@class'])
											if concepts != []:
												break

										istr0 = istr.replace(word,'')
										istr0 = re.sub(' +',' ',istr0).strip()
										concepts = ohdsirequest(istr0,itr['@class'])
										if concepts != []:
											break

									iconcept = []
									if concepts == []:
										# for multiple word removal, remove head and tail word, keep the body
										# for keeping context meaning as much as possible
										for i in range(2, lens):
											for j in range(0,i+1):
												istr0 = istr
												if j < i:
													for k in range(0,i-j):
														istr0 = istr0.replace(words[k],'')
												if j > 0:
													for k in range(lens-j,lens):
														istr0 = istr0.replace(words[k],'')
												# strip() remove the leading and tailing spaces
												istr0 = re.sub(' +',' ',istr0).strip()

												print('i= ',i,' j= ',j,' substring= ',istr0)

												iconcept = ohdsirequest(istr0, itr['@class'])
												# at the same lose word level, chose the one with smallest concept set, 
												# which should be more accurate concept set
												if iconcept != []:
													print('substring ', istr0,' is matched!')
													if concepts == [] or len(iconcept) < len(concepts):
														concepts = iconcept
														print('len(iconcpet)= ',len(iconcept),' len(concepts)= ',len(concepts))
											if concepts != []:
												break

							payload = []
							for itr2 in concepts:
								payload.append(itr2["CONCEPT_ID"])
								
							concept_set = {
								"id": cnt,							
								"name": itr['$'],
								# "domain": itr['@class'],
								"expression": {
									"items": []
								}
							}
							# negated concept
							if itr.get('@negation') and itr['@negation'] == "Y":
								concept_set["isExcluded"] = true

							# if the entity is drug, add drug exposure to criteria list
							if itr['@class'] == "Drug":
								drug_exp = {
								"DrugExposure":{
									"CodesetId": cnt
								}}
								primary_criteria["CriterialList"].append(drug_exp)

							# if the entity has measurement value, add the measurement to the criteria list
							if itr['@relation'].find("has_value") != -1 or itr['@relation'].find("has_tempMea") != -1:
								relation_split = itr['@relation'].split('|')
								for irelation in relation_split:
									print irelation
									# find the measurement value, insert into primary criteria list
									if irelation.find("has_value") != -1:
										idx = irelation.split(':')[0]
										print("find has_value at ", idx)
										if type(itrs['attribute']) == list:
											single2 = 0
										else:
											single2 = 1
										for itr_attr in itrs['attribute']:
											if single2 == 1:
												itr_attr = itrs['attribute']
											if itr_attr['@index'] == idx:
												attr = itr_attr['$']
												# extract the value information
												if attr.find("less than") != -1 or attr.find("smaller than") != -1 or attr.find("<=") != -1:
													op = "lt"
												elif attr.find("greater than") != -1 or attr.find("larger than") != -1 or attr.find(">=") != -1:
													op = "gt"
												else:
													op = "eq" #equal to the value
												# extract the value information
												value = 0 # default set to 0
												# iterate the string to find number
												for i in attr.split():
													if i.isdigit():
														value = int(i)
														break
												criteria_cur = {
													"Measurement":{
														"CodesetId": cnt,
														"ValueAsNumber":{
															"Value": value,
															"Op": op
														}
													}
												}
												primary_criteria["CriteriaList"].append(criteria_cur)
											break
											# only one attribute, and has been processed already, so jump out of the loop
											if single2 == 1:
												break
										continue

									# find the temperal measurement, add to the additional criteria list
									if irelation.find("has_tempMea") != -1:
										idx = irelation.split(':')[0]
										print ("find has_tempMea at ", idx)
										if type(itrs['attribute']) == list:
											single3 = 0
										else:
											single3 = 1
										for itr_attr in itrs['attribute']:
											if single3 == 1:
												itr_attr = itrs['attribute']
											if itr_attr['@index'] == idx:
												attr = itr_attr['$']
												day = 0
												# find the unit of time
												multiple = 0
												if attr.find("year") != -1 or attr.find("years") != -1 or attr.find("yr") != -1 or attr.find("yrs") != -1:
													multiple = 365
												elif attr.find("month") != -1 or attr.find("months") != -1 or attr.find("mo") != -1 or attr.find("mos") != -1:
													multiple = 30
												elif attr.find("week") != -1 or attr.find("weeks") != -1 or attr.find("wk") != -1 or attr.find("wks") != -1:
													multiple = 7
												elif attr.find("day") != -1 or attr.find("days") != -1:
													multiple = 1
												# there is time unit found, the default day count set to 1
												# note: some description like past year, does not have number, so the default should be 1
												if multiple != 0:
													day = 1
												attr_split = attr.split()
												print ("try to find day info")
												for i in range(1,len(attr_split)):
													print attr_split[i]
													if attr_split[i] in ["year","years","yr","yrs","month","months","mo","mos","week","weeks","wk","wks","day","days"]:
														print (attr_split[i-1])
														if attr_split[i-1].isdigit():
															day = int(attr_split[i-1])
														elif attr_split[i-1] == 'two':
															day = 2
														elif attr_split[i-1] == 'three':
															day = 3
														elif attr_split[i-1] == 'four':
															day = 4
														elif attr_split[i-1] == 'five':
															day = 5
														elif attr_split[i-1] == 'six':
															day = 6
														elif attr_split[i-1] == 'seven':
															day = 7
														elif attr_split[i-1] == 'eight':
															day = 8
														elif attr_split[i-1] == 'nine':
															day = 9
														elif attr_split[i-1] == 'ten':
															day = 10
														# some note like "x4 wks"
														elif attr_split[i-1][0] == 'x' and attr_split[i-1].splice(0,1).isdigit():
															day = int(attr_split[i-1].splice(0,1))
														break

												criteria_cur = {
													"Criteria":{
														"ConditionOccurrence":{
															"CodesetId": cnt
														}
													},
													"StartWindow":{
														"Start":{
															"Days": day*multiple,
															"Coeff": -1
														},
														"End":{
															"Days": "0",
															"Coeff": 1
														}
													},
													"Occurrence":{
														"Type": 2,
														"Count": 1														
													}
												}
												additional_criteria["CriteriaList"].append(criteria_cur)
											break
											if single3 == 1:
												break

							# get the CDR of each concept
							if payload == []:
								count = []
							else:
								url_cnt = "http://54.242.168.196/WebAPI/CS1/cdmresults/conceptRecordCount"
								# fetch all the counts informaiton
								response = requests.post(url_cnt, data=json.dumps(payload), headers=headers)
								count = json.loads(response.text)

							new_count = []
							for icount in count:
								if icount['value'][1] != 0:
									new_count.append(icount)
							# sort the count based on ['value'][1] field
							new_count = sorted(new_count,key=lambda k:k['value'][1], reverse = True)

							counts_orig['count'].append(new_count)
							for itr4 in concepts:
								concept = { "concept": itr4 }
								concept_set["expression"]["items"].append(concept);

							#   append the concept the the ohdsi variable, and increase the number by one
							ohdsi["ConceptSets"].append(concept_set)
							cnt += 1


							if single1 == 1:
								break
					if single0 == 1:
						break
			else:
				HttpResponse('The input xml file format is not valid')

			# concepts = codecs.open(output_dir, 'w')
			# added based on the ohdsi export json format
			ohdsi["QualifiedLimit"] = {				
			"Type":"First"
			}
			ohdsi["ExpressionLimit"] = {
			"Type":"First"
			}
			ohdsi["InclusionRules"] = []
			ohdsi["CensoringCriteria"] = []
			ohdsi["PrimaryCriteria"] = primary_criteria
			ohdsi["AdditionalCriteria"] = additional_criteria
			ohdsiconcept = json.dumps(ohdsi)
			counts = json.dumps(counts_orig)
			print "concept id match Finished!"
			# print ohdsiconcept
			context = {
				'ohdsi':ohdsiconcept,
				'counts': counts,
			}
			return render(request, 'OHDSImatcher/conceptFilter.html',context)
		else:
			print "the form is not valid"

	context = {
		'ohdsi':ohdsiconcept,
	}
	return render(request,'OHDSImatcher/index.html',context)

def ohdsirequest(query, domain):
	url_con = "http://54.242.168.196/WebAPI/JNJL/vocabulary/search"
	# prepare to send http request
	headers = {'content-type': 'application/json'}
	params = {
		"QUERY": query,
		"DOMAIN_ID": [domain]
	}
	# request url method
	response = requests.post(url_con, data=json.dumps(params), headers=headers)
	# print "url_con response text: ", response.text
	concepts = []
	if response.text == '[]':
		# safe = '' is for encoding the / in string
		urlvalue = urllib.quote(query,safe='')
		urls = url_con + "/" + urlvalue
		print "try dropping off the domain: ", urls
		response = urllib.urlopen(urls)
		try:
			concepts = json.loads(response.read().decode('utf-8')) # response.info().get_param('charset')))
		except ValueError:
			print(query,' is not matched')
	else:
		try:
			concepts = json.loads(response.text)
		except ValueError:
			print(query,'is not matched')
		print "concept is matched  at first attempt"
	return concepts



