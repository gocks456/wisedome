$('#video').on('hidden.bs.modal', function (e) {

  $('#video iframe').attr("src", $("#video iframe").attr("src"));
});


var owl = $('.owl-carousel');
owl.owlCarousel({
    items:4,
    loop:false,
    margin:10,
    autoplay:false,
    autoplayTimeout:1500,
    autoplayHoverPause:false,
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



  $('#radio1 img').on('click',function(){
    if( $(this).prev().attr('checked',true)) {
        $('#radio1').addClass('purple-border');
        $('#radio2, #radio3, #radio4').removeClass('purple-border');
    }
  });
  $('#radio2 img').on('click',function(){
     if( $(this).prev().attr('checked',true)) {
       $('#radio2').addClass('purple-border');
       $('#radio1, #radio3,#radio4').removeClass('purple-border');
    }
  });
  $('#radio3 img').on('click',function(){
      if( $(this).prev().attr('checked',true)) {
        $('#radio3').addClass('purple-border');
        $('#radio1,#radio2,#radio4').removeClass('purple-border');
       } 
    });
  $('#radio4 img').on('click',function(){
      if( $(this).prev().attr('checked',true)) {
       $('#radio4').addClass('purple-border');
       $('#radio1,#radio2,#radio3').removeClass('purple-border');
     } 
   });    




  $(function(){
    $(".card-img").on('click',function(){
      if( $(this).prev().attr('checked',true)){
      $(".upper-submit #submit, .bottom-submit #submit").attr("disabled",false);
    } else {
      $(".upper-submit #submit, .bottom-submit #submit").attr("disabled", true);
    }
    });
  })