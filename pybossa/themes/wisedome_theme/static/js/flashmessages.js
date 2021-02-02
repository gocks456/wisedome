function pybossaNotify(msg, showNotification, type){
    $("#pybossa-notification").remove();
    var div = $("<div/>");
    div.attr("id", "pybossa-notification");
    //div.attr("class", "content-wrapper");
    var icon = $("<i/>");
    var close = $("<i/>");
    close.addClass("mdi mdi-window-close");
    close.on('click', function(){
        $("#pybossa-notification").addClass("hide-notification");
    });
    if (type === undefined) {
        type = 'info';
    }
    if ((type === 'danger') || (type === 'error') || (type === 'warning') || (type == 'message')) {
        icon.addClass("mdi mdi-alert-circle"); 
    }

    if (type === 'message') {
        type = 'warning';
    }

    if (type === 'info') {
        icon.addClass("mdi mdi-comment-alert-outline"); 
    }

    if (type === 'success') {
        icon.addClass("mdi mdi-checkbox-marked-circle-outline"); 
    }

    if (type === 'loading') {
        icon.addClass("mdi mdi-comment-alert-outline"); 
        type = 'info';
    }



    var text = $("<span/>");
    text.html(msg);
    if (type === 'error') {
        type = 'danger';
    }
    div.addClass("alert-" + type);
    div.prepend(icon);
    div.append(text);
    div.append(close);
    if (showNotification === true) {
        div.addClass("show-notification");
        //$("body").prepend(div);
		$(".main-panel").prepend(div);

    }
    else {
        $("#pybossa-notification").addClass("hide-notification");
    }
}
