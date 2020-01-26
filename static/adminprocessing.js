/* eslint-disable */
/*
Its true, everything I know about javascript I learned on stackoverflow
http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
*/
if (!String.prototype.format) {
    String.prototype.format = function() {
        var str = this.toString();
        if (!arguments.length)
            return str;
        var args = typeof arguments[0],
            args = (("string" == args || "number" == args) ? arguments : arguments[0]);
        for (arg in args)
            str = str.replace(RegExp("\\{" + arg + "\\}", "gi"), args[arg]);
        return str;
    }
}

/*
  Assign a default to undefined values
*/
function defaultFor(arg, val)
{
  return typeof arg !== 'undefined' ? arg : val;
}

/*
  Attempts to encode the object as Http parameters
  TODO: add more serialization for specific types
*/
function encodeObjectAsHttp(x) {
  var result = "";

  for (var key in x) {
    if (x.hasOwnProperty(key)) {
      var p = x[key];

      result += key + "=";

      if (p == null)
      {
        result += "null";
      }
      if (p instanceof Date)
      {
        JSON.stringify(p);
      }
      else
      {
        result += String(p);
      }

      result += "&";
    }
  }

  return result;
}

/*

*/
function objectToString(obj)
{
  result = "{ ";
  for (var k in obj) {
    result += k + " : " + obj[k] + ",";
  }
  return result + " }";
}

function disableElements(element)
{
  $(element).find("*").prop("disabled", true).find('a').addClass("disableClick");
}

function enableElements(element)
{
  $(element).find("*").prop("disabled", false).find('a').removeClass("disableClick");
}

function safeHtml(text)
{
  // http://wonko.com/post/html-escaping
  return String(text).replace(/[&<>{}\[\]\'\" \/`!@$%\(\)=+\\]/g,
    function(s){
      return "&#" + s.charCodeAt().toString(10) + ";";
    });
}

function asMoney(val) {
  if (typeof val == "string") {
    val = parseFloat(val);
  }
  else if (typeof val == "number")
  {
  }
  else
  {
    console.log("A new number conversion type: " + typeof val);
  }
  return "$" + val.toFixed(2);
}

function makeAnchor(text, url) {
  return $('<a href="' + url + '">' + safeHtml(text) + '</a>').get(0);
}

function getObjectModel(obj) {
  return obj["model"].split(".")[1];
}

function makeEditButton(row, obj, text, resultText, fields) {
  var button = $('<button>' + text + '</button>').get(0);

  button.onclick = function() {
    disableElements(row);

    var editParams = fields;

    if ($.isFunction(fields))
    {
      editParams = fields();
    }

    trackerAPI.editObject(getObjectModel(obj), obj['pk'], editParams,
      function(status, response) {
        enableElements(row);
        if (status == 200) {
          $(row).children(".statuscell").html(resultText);

          values = JSON.parse(response)[0];

          for (var field in values['fields'])
          {
            obj[field] = values['fields'][field];
          }
        }
        else {
          $(row).children(".statuscell").html(response);
        }
      }
    );
  }

  return button;
}

function makeDeleteButton(row, obj, text, resultText, confirm) {
  var button = $('<button>' + text + '</button>').get(0);

  confirm = defaultFor(confirm, true);

  button.onclick = function() {
    if (!confirm || window.confirm("Are you sure you want to delete " +  obj["__repr__"] + "?")) {

      disableElements(row);

      trackerAPI.deleteObject(getObjectModel(obj), obj['pk'],
        function(status, response) {
          enableElements(row);

          if (status == 200) {
            $(row).children(".statuscell").html(resultText);
            $(row).fadeOut(500, function(){
              //$(row).remove();
            });
          }
          else {
            $(row).children(".statuscell").html(response);
          }
        }
      );
    }
  }

  return button;
}

function TrackerAPI(apiUrls) {

  this.apiUrls = apiUrls;

  /*
    Calls the tracker object search API
  */
  this.searchObjects = function(type, fields, oncomplete) {
    oncomplete = defaultFor(oncomplete, function(status, response){});

    params = {
      "complete" : function(xhr, status) { oncomplete(xhr.status, xhr.responseText); },
      "data" : Object.assign({type: type}, fields),
    };

    $.ajax(this.apiUrls.searchURL, params);
  };

  /*
    Calls the tracker object edit API
  */
  this.editObject = function(type, id, fields, oncomplete) {
    oncomplete = defaultFor(oncomplete, function(status, response){});

    params = {
      "method": "POST",
      "complete" : function(xhr, status) { oncomplete(xhr.status, xhr.responseText); },
      "data" : Object.assign({type: type, id: id}, fields),
    };

    $.ajax(this.apiUrls.editURL, params);
  };

  /*
    Calls the tracker object add API
  */
  this.addObject = function(type, fields, oncomplete) {
    oncomplete = defaultFor(oncomplete, function(status, response){});

    params = {
      "method": "POST",
      "complete" : function(xhr, status) { oncomplete(xhr.status, xhr.responseText); },
      "data" : Object.assign({type: type}, fields),
    };

    $.ajax(this.apiUrls.addURL, params);
  };

  /*
    Calls the tracker object delete API
  */
  this.deleteObject = function(type, id, oncomplete) {
    oncomplete = defaultFor(oncomplete, function(status, response){});

    params = {
      "method": "POST",
      "complete" : function(xhr, status) { oncomplete(xhr.status, xhr.responseText); },
      "data" : {type: type, id: id},
    };

    $.ajax(this.apiUrls.deleteURL, params);
  };

  /*
    Creates a URL link for editing the target object in the admin
  */
  this.createAdminEditURL = function(model, pk) {
    return this.apiUrls.adminBaseURL + model + '/' + pk + '/';
  };

}

function ProcessingPartitioner(partitionId, partitionCount, cookieName)
{
  this.partitionId = $(partitionId).get(0);
  this.partitionCount = $(partitionCount).get(0);
  this.cookieName = defaultFor(cookieName, null);

  if (this.cookieName != null)
  {
    var partition = $.cookie(this.cookieName);
    if (typeof partition !== 'undefined')
    {
      var toks = partition.split(",");
      $(this.partitionId).val(parseInt(toks[0]));
      $(this.partitionCount).val(parseInt(toks[1]));
    }
  }
  else
  {
    $(this.partitionId).val(1);
    $(this.partitionCount).val(1);
  }

  this.getPartition = function()
  {
    var pid = $(this.partitionId).val();
    var pset = $(this.partitionCount).val();
    return [parseInt(pid), parseInt(pset)];
  }

  this.updatedPartitionCount = function(event)
  {
    var partition = this.getPartition();

    $(this.partitionId).attr("max", partition[1]);

    if (partition[0] < 1) {
      $(this.partitionId).val(1);
    }
    else if (!(partition[0] <= partition[1])) {
      $(this.partitionId).val(partition[1]);
    }

    this.resetPartitionCookie();
  }

  this.resetPartitionCookie = function(event)
  {
    if (this.cookieName != null)
    {
      var partition = this.getPartition();
      $.cookie(this.cookieName, partition[0].toString() + "," + partition[1].toString());
      //console.log("Set partition for '" + this.cookieName + "' = " + $.cookie(this.cookieName));
    }
  }

  $(this.partitionId).attr("min", 1);
  $(this.partitionCount).attr("min", 1);

  this.updatedPartitionCount();

  // I have no idea why jquery does this, but this is a hack to get the right 'this' param in place
  var self = this;
  $(this.partitionId).change(function(){ self.resetPartitionCookie(); });
  $(this.partitionCount).change(function(){ self.updatedPartitionCount(); });
}
