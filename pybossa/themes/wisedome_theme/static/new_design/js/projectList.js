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
$(".dropdown-menu a").click(function(){
  $(this).parents(".dropdown").find('.btn').html($(this).text() + '  <span class="data-value"></span>');
  $(this).parents(".dropdown").find('.btn').val($(this).data('value'));
});