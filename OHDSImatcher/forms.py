from django import forms

class XMLInputForm(forms.Form):
	xmlinput = forms.CharField(required = True)
