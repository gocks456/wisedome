(function($) {
  'use strict';
  $(function() {
    $('[data-toggle="offcanvas"]').on("click", function() {
      $('.sidebar-offcanvas').toggleClass('active')
    });
  });
})(jQuery);


//사이드바 아이콘(들어갔다 나왔다함)
function intend(x) {
	x.classList.toggle("mdi-format-horizontal-align-right"); 
}
