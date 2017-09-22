/* requires jquery */
/*
plugin.js - autocomplete functions by Robert Crowther
js requires HTMl text input with class autocomplete-titled-id and ajaxref attribute i.e. minimal tag,
<input class="autocomplete-titled-id" autocomplete="off" ajaxref="..." type="text">
no detection of autocomplete attribute, but should be be off.
the url is queried witth a search string for the existing stub in the input.
*/
(function() {
    'use strict';
    var AutocompleteAttach = {
        
        init: function() {
            // New widget from the widget factory
            // autowires the 'source' property. Other properties can be 
            // supplied as usual.
            $.widget( "ui.django_titled_id_autocomplete", $.ui.autocomplete, {
                loadFromJSON: function(request, responseCB) {
                    var b = [];
                    var url = this.options.href + "?search=" + request.term;
                    const max = this.options.max_results;
                    $.getJSON(url, function( data ) {
                          var limit = data.length;
                          if (limit > max) {
                            limit = max
                          }
                          var e;
                          for (e of data.slice(0, limit)) {
                              //console.log(e);
                              b.push(e[1] + ' (' + e[0] + ')');
                          }
                    })
                    .fail(function() {
                      console.log( "ajax read error: url:" + url);
                    })
                    .always(function() {
                        responseCB(b);
                    });
                },
            })
            
            // available for override
            $.ui.django_titled_id_autocomplete.prototype.options.max_results = 25;
            // support code provides this values. Required. 
            $.ui.django_titled_id_autocomplete.prototype.options.href = null;
            // hardwire the 'source' property to the ajax data getter 
            $.ui.django_titled_id_autocomplete.prototype.options.source = $.ui.django_titled_id_autocomplete.prototype.loadFromJSON;


            // Initialise the widget where tags match requirements
            var inputs = document.getElementsByTagName('input');
            for (var i = 0; i < inputs.length; i++) {
                var ip = inputs[i];
                var ipk = null;
                if (ip.getAttribute('type') === 'text' && ip.className.match(/autocomplete-titled-id/)) {
                  // ok, we found one. Install the javascript.
                  // get the tree id
                  const href = $(ip).attr('ajaxref');

                  // find the id field
                  $(ip).django_titled_id_autocomplete({
                      delay: 200,
                      href: href,
                  });
                  //! No joy switching ARIA off, done in CSS
                  //$(ip).django_titled_id_autocomplete( "widget" ).role = null
                }
            }
        },

    }
    $(document).ready(AutocompleteAttach.init);
})();
