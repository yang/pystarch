
var DIRTY = false;

function update() {
    var code = $('#input').val();
    $.post('/html', {source: code}).done(function(response) {
        $('#output').val(response);
    }).fail(function() {
        $('#output').val('Syntax error in source code');
    });
}

function onInterval() {
    if(DIRTY)
        update();
    DIRTY = false; 
}

$(document).ready(function() {
    $('#input').bind('input propertychange', function() { DIRTY = true; });
    setInterval(onInterval, 1000);
    update();
});
