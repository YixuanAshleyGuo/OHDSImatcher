from django import forms
import settings 

class XMLInputForm(forms.Form):
	xmlinput = forms.CharField(widget = forms.Textarea(attrs={'class':'form-control span6', 'rows':"12", 'id': 'xmlinput'}), required = True)

class EliIEInputForm(forms.Form):
	eliie_input_free_text = forms.CharField(widget = forms.Textarea(attrs={'class':'form-control span6', 'rows':"12", 'id': 'eliieinput'}), required = True)
	eliie_package_directory = forms.FilePathField(path="/Users/cyixuan/Documents/CUMC_STUDY/SymbolicMethods/", required= True, recursive = True, allow_files = False, allow_folders = True)
	eliie_file_name = forms.CharField(required = True, max_length = 200)
	eliie_output_directory = forms.FilePathField(path="/Users/cyixuan/Documents/CUMC_STUDY/SymbolicMethods/", required= True, recursive = True, allow_files = False, allow_folders = True)

class EliIEForm(forms.Form):
	eliie_input_free_text = forms.CharField(required = True)
	eliie_package_directory = forms.CharField(required= True)
	eliie_file_name = forms.CharField(required = True, max_length = 200)
	eliie_output_directory = forms.CharField(required= True)
