

//nav color change
$(window).scroll(function(){
	var scroll = $(window).scrollTop();
	if(scroll > 50){
    $('.fixed-top').css('background', '#c7e4e2');
    $('.fixed-top').css('opacity', '0.99');
	} 

});

