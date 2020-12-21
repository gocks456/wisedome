
//나의 답변관리 숨겼다 나타내기
$(document).ready(function(){
  $("#disable-submit").click(function(){
    $("#disable-reason").slideToggle("slow");
  });
});


///답변을 누르면 제출하기 버튼 활성화됨
function taggedButton() {
  document.getElementById("submit").disabled = false;
}

function enableButton() {
  document.getElementById("bounding-start").disabled = false;
}


///문장요약란이 글자가 입력되면 제출하기 버튼 활성화
$(function(){
  $("#input_text").on('input',function(){
    if($("#input_text").val()=='')
    $("#disable-reason-btn").attr("disabled",true);
    else
    $("#disable-reason-btn").attr("disabled", false);
  });
})



//이미지선택형 문제에서 break point
var swiper = new Swiper('.swiper-container', {
  slidesPerView: 2,
  spaceBetween: 15,
	// init: false,
	/*****
    autoplay: {
    delay: 2000,
    disableOnInteraction: false,
  },
***/

pagination: {
    el: '.swiper-pagination',
    clickable: true,
  },
navigation: {
nextEl: '.swiper-button-next',
prevEl: '.swiper-button-prev',
},    

breakpoints: {
1320: {
slidesPerView: 2,
spaceBetween: 15,
},

1199: {
slidesPerView: 2,
spaceBetween: 10,
},
991: {
slidesPerView: 2,
spaceBetween: 15,
},
768: {
slidesPerView: 1,
spaceBetween: 20,
},
575: {
slidesPerView: 1,
spaceBetween: 15,
}
}
});