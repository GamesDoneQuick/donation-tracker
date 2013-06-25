
__BIDS__ = null;

function prepareDonationBids(bids) {

  for (var bidIdx in bids) {
    var bid = bids[bidIdx];
    if (bid['amount'] == null) {
      bid['amount'] = 0;
    }
    if (bid['type'].toLowerCase() == 'challenge') {
      
      bid['label'] = bid['name'] + " (" + bid['runname'] + ") $" + bid['amount'].toFixed(2) + " / $" + bid['goal'].toFixed(2);
    }
    else {
      bid['label'] = bid['choicename'] + ": " + bid['name'] + " (" + bid['runname'] + ") $" + bid['amount'].toFixed(2);
    }
  }
  
  __BIDS__ = bids;
}

function filterSelectionClosure(textBox, selectBox) {

  var choiceSearchFields = ['name', 'choicename', 'runname'];
  var challengeSearchFields = ['name', 'runname'];
  
  return function(event) {
    var toks = $.trim(textBox.value).split(new RegExp("\\s+"));
    for (var tok in toks) {
      toks[tok] = $.ui.autocomplete.escapeRegex(toks[tok]);
    }
    
    var matcher = new RegExp(toks.join('|'), "i");
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

      for (var fieldIdx in fields) {
        var field = fields[fieldIdx];
        if (matcher.test(bid[field])) {
          selectBox.options[selectBox.options.length] = new Option(bid['label'], i);
          break;
        }
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
  var children = $(obj[0]).children().get(0);
  var c2 = $(children).children().get(1);
  addBidCallbacksToWidget(c2);
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