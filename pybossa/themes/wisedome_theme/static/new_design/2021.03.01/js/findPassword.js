  (function ($) {
  	'use strict';
  	var current_fs, next_fs, previous_fs; //fieldsets
  	var left, opacity, scale; //fieldset properties which we will animate
  	var animating; //flag to prevent quick multi-click glitches

  	$(".next").click(function () {
  		if (animating) return false;
  		animating = true;

  		current_fs = $(this).parent();
  		next_fs = $(this).parent().next();

  		//activate next step on progressbar using the index of next_fs
  		$("#progressbar li").eq($("fieldset").index(next_fs)).addClass("active");

  		//show the next fieldset
  		next_fs.show();
  		//hide the current fieldset with style
  		current_fs.animate({
  			opacity: 0
  		}, {
  			step: function (now, mx) {
  				//as the opacity of current_fs reduces to 0 - stored in "now"
  				//1. scale current_fs down to 80%
  				scale = 1 - (1 - now) * 0.2;
  				//2. bring next_fs from the right(50%)
  				left = (now * 50) + "%";
  				//3. increase opacity of next_fs to 1 as it moves in
  				opacity = 1 - now;
  				current_fs.css({
  					'transform': 'scale(' + scale + ')',
  					'position': 'absolute'
  				});
  				next_fs.css({
  					'left': left,
  					'opacity': opacity
  				});
  			},
  			duration: 800,
  			complete: function () {
  				current_fs.hide();
  				animating = false;
  			},
  			//this comes from the custom easing plugin
  			easing: 'easeInOutBack'
  		});
  	});

  	$(".previous").click(function () {
  		if (animating) return false;
  		animating = true;

  		current_fs = $(this).parent();
  		previous_fs = $(this).parent().prev();

  		//de-activate current step on progressbar
  		$("#progressbar li").eq($("fieldset").index(current_fs)).removeClass("active");

  		//show the previous fieldset
  		previous_fs.show();
  		//hide the current fieldset with style
  		current_fs.animate({
  			opacity: 0
  		}, {
  			step: function (now, mx) {
  				//as the opacity of current_fs reduces to 0 - stored in "now"
  				//1. scale previous_fs from 80% to 100%
  				scale = 0.8 + (1 - now) * 0.2;
  				//2. take current_fs to the right(50%) - from 0%
  				left = ((1 - now) * 50) + "%";
  				//3. increase opacity of previous_fs to 1 as it moves in
  				opacity = 1 - now;
  				current_fs.css({
  					'left': left
  				});
  				previous_fs.css({
  					'transform': 'scale(' + scale + ')',
  					'opacity': opacity
  				});
  			},
  			duration: 800,
  			complete: function () {
  				current_fs.hide();
  				animating = false;
  			},
  			//this comes from the custom easing plugin
  			easing: 'easeInOutBack'
  		});
  	});

  	$(".submit").click(function () {
  		return false;
  	})
  })(jQuery);

/*

//1-1.이름 확인과 에러메시지
  $(function() {

	  var myName ="창원대";  //임의로 설정한 사용자 이름

    $('#name').on('keyup',function() {
        if( $(this).val() == myName ){
			$('#success-name').css("display","block");
			$('#error-name').css("display","none");
            $('#step1').attr('disabled', false);
        }
        else {
			$('#error-name').css("display","block");
			$('#success-name').css("display","none");
            $('#step1').attr('disabled', true);
        }
    });
});


//1-2.이메일확인과 에러메세지
$(function() {

	var myEmail ="abc@naver.com";  //임의로 설정한 사용자 이메일

  $('#email').on('keyup',function() {
	  if( $(this).val() == myEmail ){
		  $('#success-email').css("display","block");
		  $('#error-email').css("display","none");
		  $('#step1').attr('disabled', false);
	  }
	  else {
		  $('#error-email').css("display","block");
		  $('#success-email').css("display","none");
		  $('#step1').attr('disabled', true);
	  }
  });
});

*/

//2. 인증코드확인
$(function() {

	var myCode ="ZXC123";  //임의로 설정한 인증코드

  $('#code').on('keyup',function() {
	  if( $(this).val() == myCode ){
		  $('#success-code').css("display","block");
		  $('#error-code').css("display","none");
		  $('#step2').attr('disabled', false);
	  }
	  else {
		  $('#error-code').css("display","block");
		  $('#success-code').css("display","none");
		  $('#step2').attr('disabled', true);
	  }
  });
});



//3.비밀번호 일치하면 버튼 활성화
$(function() {
    $('#pwd2').on('keyup',function() {
        if($(this).val() == $('#pwd1').val() ){
			$('#success-pwd').css("display","block");
			$('#error-pwd').css("display","none");
            $('#step3').attr('disabled', false);
        }
        else {
			$('#error-pwd').css("display","block");
			$('#success-pwd').css("display","none");
            $('#step3').attr('disabled', true);
        }
    });
});
