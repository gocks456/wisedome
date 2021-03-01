var owl = $('.owl-carousel');
owl.owlCarousel({
    items:4,
    loop:true,
    margin:10,
    autoplay:true,
    autoplayTimeout:1500,
    autoplayHoverPause:true,
    responsive:{
        0:{
            items:1
        },
        575:{
            items:2
        },
        769:{
            items:3
        },           
        1025:{
            items:4
        }
    }
});



var today = new Date();
var date = today.getFullYear()+'-'+(today.getMonth()+1)+'-'+today.getDate();
document.getElementById("currentDate").innerHTML = '현재시간 기준  : ' + date;



$(document).ready(function(){
  $("#premium-icon").click(function(){
    $("#card-icon1,.iconTitle1").toggleClass("icon-active ");
  });
  $("#voice-icon").click(function(){
    $("#card-icon2,.iconTitle2").toggleClass("icon-active ");
  });
  $("#img-icon").click(function(){
    $("#card-icon3,.iconTitle3").toggleClass("icon-active ");
  });
  $("#text-icon").click(function(){
    $("#card-icon4,.iconTitle4").toggleClass("icon-active ");
  });
  $("#video-icon").click(function(){
    $("#card-icon5,.iconTitle5").toggleClass("icon-active ");
  });
});
