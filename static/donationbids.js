
__BIDS__ = null;

function prepareDonationBids(bids) {
  __BIDS__ = bids;
}

function filterSelectionClosure(textBox, selectBox) {

  var searchFields = ['name', 'description', 'runname'];
  
  return function(event) {
    var tokens = $.trim(textBox.value).split(new RegExp("\\s+"));
    for (var tok in tokens) {
      tokens[tok] = new RegExp($.ui.autocomplete.escapeRegex(tokens[tok]), "i");
    }
    
    selectBox.options.length = 0;
    
    for (var i = 0; i < __BIDS__.length; ++i) {
      var bid = __BIDS__[i];
      var allFound = true;

      for (var tokenIdx in tokens) {
        var token = tokens[tokenIdx];
        var found = false;

        curBid = bid;
        
        while (curBid != null && !found)
        {
          for (var fieldIdx in searchFields) {
            var field = searchFields[fieldIdx];

            if (field in curBid && token.test(curBid[field])) {
              found = true; 
              break;
            }       
          }
          
          if ('parent' in curBid) {
            curBid = curBid['parent'];
          } else {
            curBid = null;
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

function bidDetailText(bid) {
  
  var parents = Array();
  
  if ('parent' in bid)
  {
    var parent = bid['parent'];
    while (parent != null) {
      parents.push(parent);
      if ('parent' in parent) {
        parent = parent['parent'];
      } else {
        parent = null;
      }
    }
    parents.reverse();
  }
  
  parents.push(bid);
  
  var text = "";
  
  for (var i = 0; i < parents.length; ++i)
  {
    text += "<ul><li>"
    text += parents[i]['name'];

    if (parents[i]['description']) {
      text += "<br />Description: " + parents[i]['description'];
    }
  }

  for (var i = 0; i < parents.length; ++i)
  {
    text += "</li></ul>";
  }

  return text;
}

function bidSelectionClosure(selectBox, descBox, idInput) {
  return function(event) {
    var bid = BIDS[selectBox.options[selectBox.selectedIndex].value];

    var text = bidDetailText(bid);

    $(descBox).html(text);
    
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
  idInput = $(obj).children(".cdonationbidid").get(0);

  // Its important to unbind any previous events, since the way that django 
  // dyanmic formset creation works, it will still have the old events attached.
  $(textBox).unbind();
  $(textBox).bind("keyup input", filterSelectionClosure(textBox, selectBox));
  filterSelectionClosure(textBox, selectBox)(null);
  $(selectBox).unbind();
  $(selectBox).change(bidSelectionClosure(selectBox, descBox, idInput));

}
