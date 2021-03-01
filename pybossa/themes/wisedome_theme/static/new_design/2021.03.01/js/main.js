(function($) {

	var	$window = $(window),
		$body = $('body');

	// Breakpoints.
		breakpoints({
			xlarge:  [ '1281px',  '1680px' ],
			large:   [ '770px',   '1280px' ],
			medium:  [ '481px',   '769px'  ],
			small:   [ null,      '480px'  ]
		});

	// Play initial animations on page load.
		$window.on('load', function() {
			window.setTimeout(function() {
				$body.removeClass('is-preload');
			}, 100);
		});

	// Dropdowns.
		$('#nav > ul').dropotron({
			mode: 'fade',
			noOpenerFade: true,
			alignment: 'center',
			detach: false
		});

	// Nav.

		// Title Bar.
			$(
				'<div id="titleBar">' +
					'<a href="#navPanel" class="toggle"></a>' +
					'<span class="title">' + $('#logo h1').html() + '</span>' +
				'</div>'
			)
				.appendTo($body);

		// Panel.
			$(
				'<div id="navPanel">' +
					'<nav>' +
						$('#nav').navList() +
					'</nav>' +
				'</div>'
			)
				.appendTo($body)
				.panel({
					delay: 500,
					hideOnClick: true,
					hideOnSwipe: true,
					resetScroll: true,
					resetForms: true,
					side: 'left',
					target: $body,
					visibleClass: 'navPanel-visible'
				});

 
				$(".hover").mouseleave(
					function () {
						$(this).removeClass("hover");
					}
				);

	})(jQuery);


	


function arrow(x) {
	x.classList.toggle("fa-chevron-up"); 
}



$(document).ready(function(){
  $(".down-arrow").click(function(){
    $("#project-bottom").slideToggle("slow");
  });
});



$(document).ready(function(){
  $(".footer-arrow1").click(function(){
    $("#footer-list1").slideToggle("slow");
  });
});

$(document).ready(function(){
  $(".footer-arrow2").click(function(){
    $("#footer-list2").slideToggle("slow");
  });
});


$(document).ready(function(){
  $(".footer-arrow3").click(function(){
    $("#footer-list3").slideToggle("slow");
  });4});

$(document).ready(function(){
  $(".footer-arrow4").click(function(){
    $("#footer-list4").slideToggle("slow");
  });
});

$(document).ready(function(){
  $(".footer-arrow5").click(function(){
    $("#footer-list5").slideToggle("slow");
  });
});



$('#Capa_1').click(function() {
	$(this).css('fill', '#4B93A3');
	$('#Capa_2, #Capa_3, #Capa_4').css('fill','#315057');
	return false;
});
$('#Capa_2').click(function() {
	$(this).css('fill', '#4B93A3');
	$('#Capa_1, #Capa_3, #Capa_4').css('fill','#315057');
	return false;
});
$('#Capa_3').click(function() {
	$(this).css('fill', '#4B93A3');
	$('#Capa_2, #Capa_4, #Capa_1').css('fill','#315057');
	return false;
});
$('#Capa_4').click(function() {
	$(this).css('fill', '#4B93A3');
	$('#Capa_1, #Capa_2, #Capa_3').css('fill','#315057');
	return false;
});




//nav color change
$(window).scroll(function(){
	var scroll = $(window).scrollTop();
	if(scroll < 300){
		$('.fixed-top').css('background', 'transparent');
	} else{
		$('.fixed-top').css('background', 'rgba(23, 162, 184, 0.9)');
	}
});