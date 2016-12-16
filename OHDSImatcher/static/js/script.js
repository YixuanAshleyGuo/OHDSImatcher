// define variable
var ohdsi_json;
// on load funciton, initiate the input text when loading the page
function onLoadEvent(){
	// console.log("{{ohdsi}}");
	// if("{{ohdsi}}" == {}){
		var xmlinput = document.getElementById("xmlinput");
		var xmllabel = document.createElement("label");
		xmllabel.for = "xmltext";
		xmllabel.appendChild(document.createTextNode("Please enter the XML text here:"));
		var xmltext = document.createElement("textarea");
		xmltext.className = "form-control span6";
		xmltext.rows = "20";
		xmltext.form = "xmlinput";
		xmltext.name="xmlinput";
		// var xmltext = document.createElement("input");
		// xmltext.type="text";
		// xmltext.className = "form-control span6";
		xmltext.placeholder="please enter the parsed xml text here";
		xmltext.required = true;
		xmltext.id = "xmltext";
		var xmlsubmit = document.createElement("button");
		xmlsubmit.className = "btn btn-primary pull-right";
		// xmlsubmit.type="submit";
		xmlsubmit.innerHTML = "Start Transform";

		xmlinput.appendChild(xmllabel);
		xmlinput.appendChild(xmltext);
		// var xmlform = document.getElementById("inputform");
		xmlinput.appendChild(xmlsubmit);
	// }
	// else{
	// 	var xmlinput = document.getElementById("xmlinput");
	// 	xmlinput.innerHTML = "";
	// 	var ohdsitext = document.getElementById("ohdsi");
	// 	ohdsi.innerHTML = "{{ohdsi}}";
	// }
}

function onLoadConceptEvent(ohdsi){
	// document.getElementById("ohdsi").innerHTML = ohdsi;

	var txt = document.createElement("textarea");
    txt.innerHTML = ohdsi;
    // console.log(txt.value);
	// var ohdsi_json = JSON.parse(txt.value);
	// var txt2 = txt.value.replace(/u\'/g,'"');
	// txt2 = txt2.replace(/\'/g,'"');
	// console.log(txt.value);
	ohdsi_json = JSON.parse(txt.value);
	onChangeConcept();
	
}

function onChangeConcept(){
	var ohdsi_div = document.getElementById("transform");
	ohdsi_div.innerHTML = "";
	
	var conceptsets  = ohdsi_json['ConceptSets'];
	var form = document.createElement("div");
	form.id = "concept_form";		
	// form.onsubmit="return onSubmitConcept()";
	
	var conceptclass = document.createElement("div");
	// conceptclass.className = "";
	for(var i = 0; i < conceptsets.length; i++){
		var items = conceptsets[i]['expression']['items'];

		// var conceptname = document.createElement("a");
		// conceptname.className = "dropdown-toggle btn btn-primary btn-block";
		// conceptname.role = "button";
		// conceptname.attr("data-toggle":"collapse");
		// conceptname.attr("aria-expanded":"false");
		// conceptname.attr("aria-controls":"collapseExample");
		// conceptname.href = "#collapseExample"+i;
		// conceptname.innerHTML = conceptsets[i]['name'];

		var conceptname = '<a class="btn btn-primary btn-block" role="button" data-toggle="collapse" \
		href="#collapseExample'+i+'" aria-expanded="false" aria-controls="collapseExample">'+
  		conceptsets[i]['name']+'</a>';
  		// var parser = new DOMParser();
  		// var doc = parser.parseFromString(conceptname, "text/xml");

		conceptclass.insertAdjacentHTML('beforeend',conceptname);

		var conceptdiv = document.createElement("div");
		conceptdiv.className = "collapse";
		conceptdiv.id = "collapseExample"+i;
		var conceptwell = document.createElement("div");
		conceptwell.className = "well";
		for(var j = 0; j < items.length; j++){
			var checkbox = document.createElement("div");
			checkbox.className = "checkbox";
			var label = document.createElement("label");

			var concept = JSON.stringify(items[j]['concept']);
			var concept_txt = document.createTextNode(concept);
			// var concept = "test for items";
			var input = document.createElement("input");
			input.type = "checkbox";
			input.name = "conceptsets";
			input.value = conceptsets[i]['name'];
			input.checked = "checked";

			// label.innerHTML = concept;
			label.appendChild(input);
			label.appendChild(concept_txt);
			checkbox.appendChild(label);
			conceptwell.appendChild(checkbox);
		}
		conceptdiv.appendChild(conceptwell);
		// conceptclass.appendChild(conceptname);
		conceptclass.appendChild(conceptdiv);	
	}
	form.appendChild(conceptclass);

	var submit = '<button class="btn btn-default pull-right" onclick="onSubmitConcept()">Apply</button>';
	// var submit = document.createElement("button");
	// // submit.type = "submit";
	// submit.value = "Apply";
	// submit.innerHTML = "Apply";
	// submit.className = "btn btn-success pull-right";
	// submit.onclick=onSubmitConcept();

	// form.appendChild(submit);
	var prev = document.createElement("button");
	var prev = '<button class="btn btn-default pull-left" action="" onclick="history.go(-1)">Previous</button>';

	// prev.className = "btn btn-default pull-left";
	// prev.value = "Previous";
	// prev.innerHTML = "Previous";
	// prev.action = "action";
	// prev.onclick = "history.go(-2)";
	// form.appendChild(prev);
	var ohdsi_form = document.getElementById("ohdsi");
	ohdsi_form.innerHTML = "";
	ohdsi_form.appendChild(form);
	ohdsi_form.insertAdjacentHTML('beforeend',prev);
	ohdsi_form.insertAdjacentHTML('beforeend',submit);
}

function onSubmitConcept(){
	console.log("come in onSubmitConcept");
	var ohdsi = {"ConceptSets":[]};

	var ancestor = document.getElementById("concept_form");
    descendents0 = ancestor.getElementsByTagName('div')[0];
    descendents  = descendents0.childNodes;
    var i, a, div1;
	for(i = 0; i < descendents.length; ++i){
		// the a tagname, get the concept name
		a = descendents[i];
		var conceptsets = {"expression":{"item":[]},"id":i/2,"name":a.value};
		
		div0 = descendents[++i];
		div1 = div0.childNodes[0].childNodes;
		
		// div2 = div1.getElementsByTagName('div');
		var remove = [];
		var j;
		for(j = 0; j < div1.length; ++j){
			var div2 = div1[j].childNodes[0];
			if(!div2.childNodes[0].checked){
				console.log("deleting "+j+ "'s childnode");
				remove.push(j);
			}
		}
		for(j = remove.length-1; j >=0; j--){
			console.log("deleting i/2= "+i/2+" j= "+j);
			ohdsi_json["ConceptSets"][(i-1)/2]["expression"]["items"].splice(remove[j],1);
		}
	}
	var ohdsi_submit = document.createElement("div");
	ohdsi_submit.className = "well";
	ohdsi_submit.innerHTML = JSON.stringify(ohdsi_json,null,2);
	
	var prev = '<button class="btn btn-default btn-block" action="" onclick="onChangeConcept()">Previous</button>';
	// var prev = document.createElement("button");
	// prev.className = "btn btn-default btn-block";
	// prev.value = "Previous Step";
	// prev.action = "action";
	// prev.onclick = "history.go(-1)";
	var ohdsi_form = document.getElementById("ohdsi");
	// ohdsi_form.style.visibility ='hidden';
	ohdsi_form.innerHTML = "";
	var ohdsi_div = document.getElementById("transform");
	ohdsi_div.appendChild(ohdsi_submit);
	ohdsi_div.insertAdjacentHTML('beforeend',prev);
	
}

