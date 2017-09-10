/*needs JQuery, URLify*/
/* fullfills 25% of the effect in no-time-at-all rules */

$( document ).ready(function() {
 
  $('#id_title').on( "change", function() {
  var txt = $('#id_title').val()
  var slugTxt = URLify(txt, 64, false)
  $('#id_slug').val(slugTxt)

});
});
