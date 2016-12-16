from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from .forms import XMLInputForm
import requests,urllib,json
from xmljson import badgerfish as bf
from xml.etree import ElementTree as ET

def index(request):
	ohdsiconcept = {}
	counts_orig = {'count':[]}
	if request.method == 'POST':
		xmlform = XMLInputForm(data = request.POST)
		print("about to validate form")
		# print(request.POST)
		if xmlform.is_valid():
			print("form is valid")
			data = xmlform.cleaned_data
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
			for itr in js_obj['root']['sent']['entity']:
				# print 'Concept:', itr['$'], ' ID:', itr['@class']
				params = {
					"QUERY": itr['$'],
					"DOMAIN_ID": [itr['@class']]
				}
				# request url method
				response = requests.post(url_con, data=json.dumps(params), headers=headers)
				# print "url_con response text: ", response.text
				if response.text == '[]':
					urlvalue = urllib.quote(itr['$'])
					urls = url_con + "/" + urlvalue
					print "try dropping off the domain: ", urls
					response = urllib.urlopen(urls)
					concepts = json.loads(response.read().decode('utf-8')) # response.info().get_param('charset')))
				else:
					concepts = json.loads(response.text)


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
				if payload == []:
					count = []
				else:
					url_cnt = "http://54.242.168.196/WebAPI/CS1/cdmresults/conceptRecordCount"
					# fetch all the counts informaiton
					response = requests.post(url_cnt, data=json.dumps(payload), headers=headers)
					count = json.loads(response.text)
				print count
				counts_orig['count'].append(count)
				for itr4 in concepts:
					concept = { "concept": itr4 }
					concept_set["expression"]["items"].append(concept);

				#   append the concept the the ohdsi variable, and increase the number by one
				ohdsi["ConceptSets"].append(concept_set)
				cnt += 1
			# concepts = codecs.open(output_dir, 'w')
			ohdsiconcept = json.dumps(ohdsi)
			counts = json.dumps(counts_orig)
			print "concept id match Finished!"
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




