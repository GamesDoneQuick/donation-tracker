
__BIDS__ = null;

function MegaFilter(objects, groupings, searchFields, labelCallback, detailsCallback) {

  this.objects = objects;
  
  
  this.objectsLookup = {};
  
  for (var i in this.objects) {
    this.objectsLookup[this.objects[i]['id']] = this.objects[i];
  }
  
  this.groupings = groupings;
  this.searchFields = searchFields;
  this.labelCallback = labelCallback;
  this.detailsCallback = detailsCallback;
  
  this.getObjectById = function(id) {
    return this.objectsLookup[id];
  }

  this.filterSelectionClosure = function(textBox, typeBox, selectBox) {
    
    var self = this;

    if (typeBox != null && this.groupings != null && this.groupings.length > 0) {
      typeBox.options.length = 0;
      typeBox.add(new Option("All", "all"));
      for (var i in this.groupings) {
        typeBox.add(new Option(this.groupings[i], this.groupings[i]));
      }
      typeBox.selectedIndex = 0;
    }

    return function(event) {

      var typeStr = "all";

      if (typeBox.selectedIndex > 0) {
        typeStr = typeBox.options[typeBox.selectedIndex].value;
        
        if ($.inArray(typeStr,self.groupings) == -1) {
          typeStr = "all";
        }
      }
      
      var tokens = $.trim(textBox.value).split(new RegExp("\\s+"));
      for (var tok in tokens) {
        tokens[tok] = new RegExp($.ui.autocomplete.escapeRegex(tokens[tok]), "i");
      }
      
      selectBox.options.length = 0;

      for (var i = 0; i < self.objects.length; ++i) {
        var bid = self.objects[i];
        var allFound = true;
        
        if (typeStr == "all" || typeStr in bid)
        {

          for (var tokenIdx in tokens) {
            var token = tokens[tokenIdx];
            var found = false;

            var prefix = "";

            if (typeStr != "all") {
              for (var suggestionIdx in bid[typeStr]) {
                var suggestion = bid[typeStr][suggestionIdx];
                if (token.test(suggestion)) {
                  found = true;
                }
              }
            }

            var curBid = bid;
            
            while (curBid != null && !found)
            {
              for (var fieldIdx in self.searchFields) {
                var field = self.searchFields[fieldIdx];

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
            var prefix = "";

            if (typeStr != "all") {
              prefix = "(" + bid[typeStr] + ") ";
            }
              
            selectBox.options[selectBox.options.length] = new Option(prefix + self.labelCallback(bid), i);
          }
        }
      }

    }
  };
  
  this.selectionClosure = function(selectBox, descBox, idInput, selectionCallback) {
    var self = this;
    
    return function(event) {
      var bid = self.objects[selectBox.options[selectBox.selectedIndex].value];

      var text = self.detailsCallback(bid);

      $(descBox).html(text);
      
      var clearButton = $('<button type="button">Clear</button>').get(0);
      
      $(clearButton).click(
        function() {
          selectBox.selectedIndex = -1;
          $(descBox).html("");
          $(idInput).val("");
          $(idInput).change();
        });
        
      $(descBox).append($('<br />')).append(clearButton);
      
      $(idInput).val(bid['id']);
      $(idInput).change();

      if (selectionCallback) {
        selectionCallback(bid);
      }
    }
  };
  
  this.setWidgetValue = function(obj, value) {
    var filterBox = $(obj).children(".mf_filter").get(0);
    var groupBox = $(obj).children(".mf_grouping").get(0);
    var groupBoxLabel = $(obj).children(".mf_groupingLabel").get(0);
    var selectBox = $(obj).children(".mf_selectbox").get(0);
    var descBox = $(obj).children(".mf_description").get(0);
    var idInput = $(obj).children(".mf_selection").get(0);
  
    var found = false;
    
    if (value !== 'undefined') {
      for (var optionId in selectBox.options) {
        var obj = this.objects[optionId];
        if (typeof obj !== 'undefined' && value == obj.id) {
          console.log('found');
          selectBox.selectedIndex = optionId;
          $(selectBox).change();
          found = true;
          break;
        }
      }
      
      if (!found) {
        $(idInput).val("");
      }
    }
  }
  
  this.applyToWidget = function(obj, selectionCallback) {
    
    var filterBox = $(obj).children(".mf_filter").get(0);
    var groupBox = $(obj).children(".mf_grouping").get(0);
    var groupBoxLabel = $(obj).children(".mf_groupingLabel").get(0);
    var selectBox = $(obj).children(".mf_selectbox").get(0);
    var descBox = $(obj).children(".mf_description").get(0);
    var idInput = $(obj).children(".mf_selection").get(0);
    
    if ((this.groupings == null || this.groupings.length == 0) || groupBox == null) {

      if (groupBox != null) {
        $(groupBox).hide();
      }
      if (groupBoxLabel != null) {
        $(groupBoxLabel).hide();
      }
    }

    // Its important to unbind any previous events, since the way that django 
    // dyanmic formset creation works, it will still have the old events attached.
    $(filterBox).unbind();
    var filterSelectionMethod = this.filterSelectionClosure(filterBox, groupBox, selectBox);
    
    $(groupBox).unbind();
    $(groupBox).change(filterSelectionMethod);
    $(filterBox).bind("keyup input", filterSelectionMethod);
    
    filterSelectionMethod(null);
    
    var optionSelectionMethod = this.selectionClosure(selectBox, descBox, idInput, selectionCallback);
    
    $(selectBox).unbind();
    $(selectBox).change(optionSelectionMethod);
    
    this.setWidgetValue(obj, $(idInput).val());
  };
  
} // class MegaFilter


