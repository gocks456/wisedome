

//nav color change
$(window).scroll(function(){
	var scroll = $(window).scrollTop();
	if(scroll > 50){
    $('.fixed-top').css('background', '#e5f1f0');
    $('.fixed-top').css('opacity', '0.99');
	} else if( scroll ===  0 ){
		$('.fixed-top').css('background', '#c7e4e2');
	} 
	else{
		$('.fixed-top').css('background', 'transparent');
	}
});

