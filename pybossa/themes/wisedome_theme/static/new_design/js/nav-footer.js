

//nav color change
$(window).scroll(function(){
	var scroll = $(window).scrollTop();
	if(scroll > 350){
    $('.fixed-top').css('background', '#e5f1f0');
    $('.fixed-top').css('opacity', '0.95');
	} else{
		$('.fixed-top').css('background', 'transparent');
	}
});
