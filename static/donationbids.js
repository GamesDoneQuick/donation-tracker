
__BIDS__ = null;

function prepareDonationBids(bids) {
  __BIDS__ = bids;
}

function filterSelectionClosure(textBox, selectBox) {

  var choiceSearchFields = ['name', 'choicename', 'runname'];
  var challengeSearchFields = ['name', 'runname'];
  
  return function(event) {
    var tokens = $.trim(textBox.value).split(new RegExp("\\s+"));
    for (var tok in tokens) {
      tokens[tok] = new RegExp($.ui.autocomplete.escapeRegex(tokens[tok]), "i");
    }
    
    selectBox.options.length = 0;
    
    for (var i = 0; i < __BIDS__.length; ++i) {
      var bid = __BIDS__[i];
      var fields = null;
      
      if (bid['type'].toLowerCase() == 'challenge') {
        fields = challengeSearchFields;
      }
      else {
        fields = choiceSearchFields;
      }

      var allFound = true;

      for (var tokenIdx in tokens) {
        var token = tokens[tokenIdx];
        var found = false;

        for (var fieldIdx in fields) {
          var field = fields[fieldIdx];

          if (token.test(bid[field])) {
	      found = true; 
              break;
          }

        }


        if (!found) {
          allFound = false;
          break;
        }
      }

      if (allFound) {
        selectBox.options[selectBox.options.length] = new Option(bid['label'], i);
      }

    }
  }
}

function bidSelectionClosure(selectBox, descBox, typeInput, idInput) {
  return function(event) {
    var bid = BIDS[selectBox.options[selectBox.selectedIndex].value];

    var text = "";
    
    if (bid['type'].toLowerCase() == 'choice') {
      
      text = "Choice: " + bid['choicename'];
      
      if (bid['choicedescription'] != "") {
        text += "<br />" + bid['choicedescription'];
      }
      
      text += "<br />Option: " + bid['name'];
      
      if (bid['description'] != "") {
        text += "<br />" + bid['description'];
      }
    }
    else {
      text = "Challenge: " + bid['name'];
    
      if (bid['description'] != "") {
        text += "<br />" + bid['description'];
      }
    }
    
    $(descBox).html(text);
    
    $(typeInput).val(bid['type']);
    $(idInput).val(bid['id']);
  }
}

function onAddBidAssignmentWidget(obj) {
  var widgetDiv = $(obj).find(".cdonationbidwidget").get(0);
  addBidCallbacksToWidget(widgetDiv);
  numBlocks = $(".toplevelformsetform").length;
  if (numBlocks >= 10) {
     $(".add-row").css("display", "none");
  }
}

function addBidCallbacksToWidget(obj) {
  
  textBox = $(obj).children(".cdonationbidfilter").get(0);
  selectBox = $(obj).children(".cdonationbidselect").get(0);
  descBox = $(obj).children(".cdonationbiddesc").get(0);
  typeInput = $(obj).children(".cdonationbidtype").get(0);
  idInput = $(obj).children(".cdonationbidid").get(0);

  // Its important to unbind any previous events, since the way that django 
  // dyanmic formset creation works, it will still have the old events attached.
  $(textBox).unbind();
  $(textBox).bind("keyup input", filterSelectionClosure(textBox, selectBox));
  filterSelectionClosure(textBox, selectBox)(null);
  $(selectBox).unbind();
  $(selectBox).change(bidSelectionClosure(selectBox, descBox, typeInput, idInput));

}