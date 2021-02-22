var owl = $('.owl-carousel');
owl.owlCarousel({
    loop:true,
    rtl:true,
    nav:true,
    margin:10,
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
        },
        1281:{
            items:5
        }
    }
});
owl.on('mousewheel', '.owl-stage', function (e) {
    if (e.deltaY>0) {
        owl.trigger('next.owl');
    } else {
        owl.trigger('prev.owl');
    }
    e.preventDefault();
});



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
  