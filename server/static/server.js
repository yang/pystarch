
function update() {
    var code = $('#input').val();
    $.post('/html', {source: code}).done(function(response) {
        $('#output').val(response);
    }).fail(function() {
        alert('Syntax error in source code');
    });
}
