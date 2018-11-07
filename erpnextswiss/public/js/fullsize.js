var fontSizeArray = [];
(function ($) {
  $(document).ready(function(){
	addFullsizeBtn();
	addEventListenerToBtnFullSize();
  });
}(jQuery));

function addFullsizeBtn() {
	var node = document.createElement("LI");
	var a_tag = document.createElement("A");
	a_tag.setAttribute('id','fullsizebtn');
	var t = document.createTextNode("Fullsize View");
	a_tag.appendChild(t);
	node.appendChild(a_tag);
	document.getElementById("toolbar-user").insertBefore(node, document.getElementById("toolbar-user").getElementsByClassName("divider")[0]);
}

function goFullsize() {
	var sheet = document.createElement('style')
	sheet.setAttribute('id', 'fullsizestyle');
	sheet.innerHTML = ".container { width: 100% !important; }";
	document.body.appendChild(sheet);
	prepareBackToNormalView();
}

function addEventListenerToBtnFullSize() {
	document.getElementById("fullsizebtn").onclick = function() { goFullsize() };
}

function addEventListenerToBtnNormalView() {
	document.getElementById("fullsizebtn").onclick = function() { backToNormalView() };
}

function prepareBackToNormalView() {
	document.getElementById("fullsizebtn").innerHTML="Normal View";
	addEventListenerToBtnNormalView();
}

function backToNormalView() {
	var sheetToBeRemoved = document.getElementById('fullsizestyle');
	var sheetParent = sheetToBeRemoved.parentNode;
	sheetParent.removeChild(sheetToBeRemoved);
	document.getElementById("fullsizebtn").innerHTML="Fullsize View";
	addEventListenerToBtnFullSize();
}
