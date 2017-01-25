from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from .forms import XMLInputForm,EliIEInputForm, EliIEForm
import requests,urllib2,json,urllib
from xmljson import badgerfish as bf
from xml.etree import ElementTree as ET
import re
import textwrap
import os
from django.core.files import File


def index(request):
	return render(request,'OHDSImatcher/index.html')

def eliie(request):
	print("you entered the EliIE page")
	if request.method == 'POST':
		xml_text = eliie_exec(equest.POST)
		request.session['xml_text'] = xml_text
		return HttpResponseRedirect('/json-transform')
	else:
		eliieform = EliIEInputForm()
		nct_eli = {}
		context = {
			'nct_eli' : nct_eli,
			'eliieform': eliieform
		}
		return render(request,'OHDSImatcher/eliie.html', context)

def eliie_nct(request,slug):
	print "you entered the EliIE page at",slug
	if request.method == 'POST':
		xml_text = eliie_exec(request.POST)
		request.session['xml_text'] = xml_text
		return HttpResponseRedirect('/json-transform')
	else:
		eliieform = EliIEInputForm()
		nct_eli = {}
		if slug[0:3] != "NCT" and slug[0:3] != "nct":
			nct_eli['text'] = str("You entered ClinicalTrials.gov ID: "+slug+", but this is not valid!")
		else:
			url = "https://clinicaltrials.gov/show/"+slug+"?displayxml=true"
			response = urllib2.urlopen(url)
			try:
				nct_orig = response.read().decode('utf-8')
				nct_orig = nct_orig.encode('ascii','ignore')
				# print nct_orig
				try:
					nct_root = ET.fromstring(nct_orig)
				except:
					print 'ET not working'
					nct_eli['text'] = str("You entered ClinicalTrials.gov ID: "+slug+", but this is not valid or there is error in parsing the result from ClincalTrials.gov!")
					context = {
						'nct_eli': nct_eli,
						'eliieform': eliieform
					}
					return render(request,'OHDSImatcher/eliie.html',context)
				eli = nct_root.findall('eligibility')[0]
				# nct_txt = "entered ClinicalTrials.gov ID: "+slug+", and success fetch response."
				for child in eli:
					if child.tag == "criteria":
						txt = child.findall('textblock')[0].text
						txt_list = txt.split('\n')
						textarea = ''
						# the returned raw text contains false line break
						# find the false line break and conncet the original sentence together
						prev_continue = True
						for ilist in txt_list:
							ilist_parse = re.sub(' +',' ',ilist).lower().strip()
							if ilist_parse == '':
								continue
							# if the first character is alphabetic, then continue with previous line
							if prev_continue and ilist_parse.find("clusion criteria") == -1 and ilist_parse[0].isalpha():
								textarea += ' '+ilist.strip()
							else:
								textarea += '\n'+ilist.strip()
							# the current line end with stop punctuation, the next line should have \n even if it start with alphabetic
							if ilist_parse[len(ilist_parse)-1] == "." or ilist_parse.find("clusion criteria") != -1:
								prev_continue = False
								if ilist_parse[len(ilist_parse)-1] == "." and ilist_parse[-4:]=="i.e.":
									prev_continue = True
							else:
								prev_continue = True

						nct_eli['text'] = textarea[1:]
					elif child.tag == "gender":
						nct_eli['gender'] = child.text
					elif child.tag == "minimum_age":
						nct_eli['min_age'] = child.text
					elif child.tag == "maximum_age":
						nct_eli['max_age'] = child.text			

			except ValueError:
				nct_eli['text'] =  str("You entered ClinicalTrials.gov ID: "+slug+", and but did not fetch response!")
				print "the clinical trial NCT does not match any record"

		context = {
			'nct_eli': nct_eli,
			'eliieform': eliieform
		}
		return render(request,'OHDSImatcher/eliie.html',context)

def eliie_exec(post):
	data = {
		'eliie_input_free_text': post['eliie_input_free_text'], 
		'eliie_package_directory':"/home/cy2465/EliIE",
		'eliie_file_name': "EliIE_input_free_text",		
		'eliie_output_directory':"/home/cy2465/EliIE/Tempfile"
	}

	# write the free text to file
	nct_file = data['eliie_output_directory']+'/'+data['eliie_file_name']+'.txt'
	with open(nct_file,'w') as f:
		myfile = File(f)
		myfile.write(data['eliie_input_free_text'])
	myfile.closed
	f.closed

	# change the directory to the EliIE package path, then execute the 2 steps
	os.chdir(data['eliie_package_directory'])

	command = 'python NamedEntityRecognition.py "'+ data['eliie_output_directory']+'" '+data['eliie_file_name'] + '.txt ' + data['eliie_output_directory']
	print 'Attention: command 1 NER: ', command,' is about to execute, check the output file'
	os.system(command)
	command = 'python Relation.py '+ data['eliie_output_directory']+' '+data['eliie_file_name']+'.txt'
	print 'Attention: command 2 Relation: ', command, ' is about to execute, check the output file'		
	os.system(command)
				
	# read the parsed xml file
	xml_fname = data['eliie_file_name']+'_Parsed.xml'
	xml_txt = open(os.path.join(data['eliie_output_directory'],xml_fname)).read()
	print 'result xml is ready'
	return xml_txt


def json_trans(request):
	if request.method == 'POST':
		xmlform = XMLInputForm(data = request.POST)
		print("about to validate XML input form")
		# print(request.POST)
		if xmlform.is_valid():
			print("XML input form is valid")
			data = xmlform.cleaned_data
			# for temp use, should be removed later
			# inputdata = '<root>'++'</root>'
			root = ET.fromstring(data['xmlinput'])
			js = json.dumps(bf.data(root), indent=4, sort_keys=True)
			js_obj = json.loads(js)
			# prepare to send http request
			headers = {'content-type': 'application/json'}
			url_con = "http://54.242.168.196/WebAPI/JNJL/vocabulary/search"
			# define the result variable
			ohdsi = {'ConceptSets':[]}
			# define the inner field of result
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
			demographic_criteria = {}
			#by default, the criteria are inclusion criteria
			exclusion = False
			# Type: 0: exactly, 1: at most, 2: at least
			# Count: the count of occurrence
			occurrence = [
			{
			"Type":2,
			"Count":1
			},
			{
			"Type":0,
			"Count":0
			}
			]
			# by default, the occurrence is "at least 1"
			occur_idx = 0

			cnt = 0
			if js_obj.get('root') and js_obj['root'].get('sent'):
				payload = []
				concepts = []
				# check if there is only one sentence in the current xml root directory
				if type(js_obj['root']['sent']) == list:
					single0 = 0
				else:
					single0 = 1
				for itrs in js_obj['root']['sent']:
					# check if the current criteria is inclusion criteria or exlusion criteria
					# set the exclusion flag "exclusion" to corresponding value
					# by default, demographic information (age, gender) are regarded as inclusion criteria 
					# and does not influenced by "exclusion"
					text_tmp = itrs['text']['$'].lower()
					# by default, the criterias are treated as inclusion criteria
					if text_tmp.find('inclusion criteria') != -1:
						exclusion = False
					elif text_tmp.find('exclusion criteria') != -1:							
						exclusion = True
					
					# for exclusion criteria: change criteria occurrence to "exactly 0"
					if exclusion == True:
						occur_idx = 1
					# for inclusion criteria: change criteria occurrence to "at least 1"
					else:
						occur_idx = 0

					# check if the current sentence has entity
					if single0 == 1 or (itrs.get('entity')):
						if single0 == 1:
							itrs = js_obj['root']['sent']

						
						# print 'exclusion: ',exlusion,' occur_idx: ', occur_idx


						# check if there is only one entity in the current sentence
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

							# entity "female/male" should be handled differently 
							# and save to the condition occurance of primary criteria list
							# 
							lower_entity = itr['$'].lower().strip()
							if lower_entity == "male" or lower_entity=="female":
								gender = []
								if lower_entity=="female":
									g = {
										"CONCEPT_CODE": "F",
										"CONCEPT_ID": 8532,
										"CONCEPT_NAME": "FEMALE",
										"DOMAIN_ID": "Gender",
										"VOCABULARY_ID": "Gender"
									}
									gender.append(g)
								else:
									g = {
										"CONCEPT_CODE": "M",
										"CONCEPT_ID": 8507,
										"CONCEPT_NAME": "MALE",
										"DOMAIN_ID": "Gender",
										"VOCABULARY_ID": "Gender"
									}
									gender.append(g)
								demographic_criteria["Gender"]=gender
								if single1 == 1:
									break
								else:
									continue

#########################################
# PART I: get the vocabulary
# iterate the json object and add attribute Concept ID in the json object
# Request URL:http://54.242.168.196/WebAPI/JNJL/vocabulary/search/drug%20allergies
# Request Method:POST
# url_con = "http://discovery.dbmi.columbia.edu:8080/WebAPI/Synpuf-1-Percent/vocabulary/search"
							# if the entity is "age", do not treat it as concept
							if lower_entity != "age" and lower_entity != "ages":
								print 'the entity is either age or ages'
								params = {
									"QUERY": itr['$'],
									"DOMAIN_ID": [itr['@class']]
								}

								# request url method
								response = requests.post(url_con, data=json.dumps(params), headers=headers)
								# print "url_con response text: ", response.text
								# concepts = []
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


								# substring match algorithm - triggered when the whole string does not have match
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
									"expression": {
										"items": []
									}
								}
#########################################
# PART II: get the DR, CDR count value of the concepts 
# request with the concepts sets and get the counts of each one
# Request URL:http://54.242.168.196/WebAPI/CS1/cdmresults/conceptRecordCount
# Request Method:POST
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

#########################################
# PART III: get the criteria related to the entity
# primary criteria: has_value 
# additional criteria: has_TempMea
								# negation information
								# together with exclusion criteria flag
								# to determine whether the occurrence of the concept set is 0 or 1
								if itr.get('@negation') and itr['@negation'] == "Y":
									# if negated, the condition occurrence should be reversed
									occur_idx = 1 - occur_idx


							has_additional_criteria = False
							# if the entity has measurement value, add the measurement to the criteria list
							if itr.get('@relation') and (itr['@relation'].find("has_value") != -1 or itr['@relation'].find("has_tempMea") != -1):
								relation_split = itr['@relation'].split('|')
								for irelation in relation_split:
									print irelation
									# "has_value" relation
									# find the measurement value, 
									# insert into additional criteria list
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
												# situation 1: if the value is int, 
												# handle differently, set op to be "gt" by default
												if isinstance(attr, int):
													if lower_entity == "age" or lower_entity == "ages":
														demographic_criteria["Age"]={
															"Value": attr,
															"Op": "gt",
														}
													else:
														criteria_cur = {
														"Criteria":{
															"Measurement":{
																"CodesetId": cnt,
																"ValueAsNumber":{
																	"Value": attr,
																	"Op": "gt"
																}
															}
														},
														"StartWindow":{
															"Start":{
															"Coeff":-1
															},
															"End":{
															"Days":0,
															"Coeff":-1
															}
														},
														"Occurrence":occurrence[occur_idx]
														}
														additional_criteria["CriteriaList"].append(criteria_cur)
														has_additional_criteria = True
													break

												multiple = float(time_unit(attr))/365
												if multiple == 0:
													multiple = 1
												# situation 2: if the value has "between" keyword, 
												# means that it has lower and upper values
												if attr.find("between") != -1 or attr.find("to") != -1:
													op = "bt"
													value = [0,0]
													j = 0
													for i in attr.split():
														if j < 2 and i.isdigit():
															value[j] = int(i)
															j += 1
													
													if lower_entity == "age" or lower_entity == "ages":
														demographic_criteria["Age"]={
															"Value": value[0]*multiple,
															"Extent": value[1]*multiple,
															"Op": op
														}
													else:
														criteria_cur = {
														"Criteria":{
															"Measurement":{
																"CodesetId": cnt,
																"ValueAsNumber":{
																	"Value": value[0],
																	"Extent": value[1],
																	"Op": op
																}
															}
														},
														"StartWindow":{
															"Start":{
															"Coeff":-1
															},
															"End":{
															"Days":0,
															"Coeff":-1
															}
														},
														"Occurrence":occurrence[occur_idx]
														}
														additional_criteria["CriteriaList"].append(criteria_cur)
														has_additional_criteria = True
													break

												# situation 3: the value is simply > or < or =
												# extract the value information
												if attr.find("less than") != -1 or attr.find("smaller than") != -1 or attr.find("<=") != -1:
													op = "lt"
												elif attr.find("greater than") != -1 or attr.find("larger than") != -1 or attr.find("over") != -1 or attr.find(">=") != -1:
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
												if lower_entity == "age"  or lower_entity == "ages":
													demographic_criteria["Age"]={
														"Value": value*multiple,
														"Op": op,
													}
												else:
													criteria_cur = {
													"Criteria":{
														"Measurement":{
															"CodesetId": cnt,
															"ValueAsNumber":{
																"Value": value,
																"Op": op
															}
														}
													},
													"StartWindow":{
														"Start":{
														"Coeff":-1
														},
														"End":{
														"Days":0,
														"Coeff":-1
														}
													},
													"Occurrence": occurrence[occur_idx]													}
													additional_criteria["CriteriaList"].append(criteria_cur)
													has_additional_criteria = True
												break
											# only one attribute, and has been processed already, so jump out of the loop
											if single2 == 1:
												break

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
												multiple = time_unit(attr)
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
												if day != 0 and multiple == 0:
													multiple = 1;
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
															"Coeff": -1
														}
													},
													"Occurrence": occurrence[occur_idx]
												}
												additional_criteria["CriteriaList"].append(criteria_cur)
												has_additional_criteria = True
											break
											if single3 == 1:
												break
							# add default additional criteria when none is found so far
							if lower_entity != "age"  and lower_entity != "ages" and has_additional_criteria == False:
								# set the entity occurance to be 1								
								if itr['@class'] == "Condition":
									entity = "ConditionOccurrence"
								elif itr['@class'] == "Observation":
									entity = "Observation"
								elif itr['@class'] == "Procedure_Device":
									entity = "ProcedureOccurrence"
								elif itr['@class'] == "Drug":
									entity = "DrugExposure"
								criteria_cur = {
										"Criteria":{
											entity: {
												"CodesetId": cnt
											}
										},
										"StartWindow":{
											"Start":{
												"Coeff":-1
											},
											"End":{
												"Days":0,
												"Coeff":-1
											}
										},
										"Occurrence": occurrence[occur_idx]
								}
								additional_criteria["CriteriaList"].append(criteria_cur)


							if lower_entity != "age" and lower_entity != "ages":
								cnt += 1

							print 'exclusion: ',exclusion,' occur_idx: ', occur_idx

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
			additional_criteria["DemographicCriteriaList"].append(demographic_criteria) 
			ohdsi["AdditionalCriteria"] = additional_criteria
			ohdsiconcept = json.dumps(ohdsi)
			counts = json.dumps(counts_orig)
			print "concept id match Finished!"
			# print ohdsiconcept
			request.session['ohdsi'] = ohdsiconcept
			request.session['counts'] = counts
			return HttpResponseRedirect('/json-transform/result')
		else:
			print "the form is not valid"

	if request.session.get('xml_text'):
		xmlinputform = XMLInputForm(initial={'xmlinput':request.session['xml_text']})
	else:
		xmlinputform = XMLInputForm()
	context = {
		'xmlinputform':xmlinputform
	}
	return render(request,'OHDSImatcher/json_transform.html',context)

def time_unit(attr):
	if attr.find("year") != -1 or attr.find("years") != -1 or attr.find("yr") != -1 or attr.find("yrs") != -1:
		multiple = 365
	elif attr.find("month") != -1 or attr.find("months") != -1 or attr.find("mo") != -1 or attr.find("mos") != -1:
		multiple = 30
	elif attr.find("week") != -1 or attr.find("weeks") != -1 or attr.find("wk") != -1 or attr.find("wks") != -1:
		multiple = 7
	elif attr.find("day") != -1 or attr.find("days") != -1:
		multiple = 1
	else:
		multiple = 0
	return multiple

def json_trans_res(request):
	if request.session.get('ohdsi') and request.session.get('counts'):
		context = {
			'ohdsi': request.session['ohdsi'],
			'counts': request.session['counts'],
		}
	else:
		context = {
			'ohdsi': {},
			'counts': []
		}
	return render(request, 'OHDSImatcher/concept_filter.html',context)


# concept match request function: 
# request the OHDSI API to match the entities with concepts
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



