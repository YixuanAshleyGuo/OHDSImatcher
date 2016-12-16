from django import forms

class XMLInputForm(forms.Form):
	xmlinput = forms.CharField(required = True ,max_length=65525)
