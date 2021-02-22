//write comment
$(document).ready(function(){
    $("#addComment").click(function(){
      $(".comment-view").slideToggle("slow");
    });
  });
  

//switch heart icon
$(document).ready(function(){
  $('#heartIcon').click(function() {
    $(this).children().toggleClass('mdi-heart-outline mdi-heart');
  });
});

//댓글섹션
$(document).ready(function () { 
    $("#submitComment").click(function () { 
        var txt = $("#comment-input").val(); 
        $("#displayComment").html(txt); 
        $("#comment-input").val(""); 
        $(".comment-area").css({display:"block"});
    }); 
}); 


//disable button if input value is empty
$(function(){
    $("#comment-input").on('input',function(){
      if($("#comment-input").val()=='')
      $("#submitComment").attr("disabled",true);
      else
      $("#submitComment").attr("disabled", false);
    });
  })