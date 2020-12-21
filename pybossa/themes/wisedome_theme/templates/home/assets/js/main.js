

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

       //진행중인 프로젝트
				$(".hover").mouseleave(
					function () {
						$(this).removeClass("hover");
					}
				);

	})(jQuery);

//더블 화살표 위아래로 바뀜
function arrow(x) {
	x.classList.toggle("fa-chevron-up"); 
}



//진행중이 프로젝트 숨겼다 나타내기
$(document).ready(function(){
  $(".down-arrow").click(function(){
    $("#project-bottom").slideToggle("slow");
  });
});




//footer 리스트 모바일에서 내렸다올렸다 하기
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

