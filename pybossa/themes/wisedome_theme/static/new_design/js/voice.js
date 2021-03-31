  
  function openPage(evt, pageNumber) {
    var i, editNumPages, tablinks;
    editNumPages = document.getElementsByClassName("pageContents");
    for (i = 0; i < editNumPages.length; i++) {
      editNumPages[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablink");
    for (i = 0; i < editNumPages.length; i++) {
      tablinks[i].className = tablinks[i].className.replace(" purple", "");
    }
    document.getElementById(pageNumber).style.display = "block";
    evt.currentTarget.className += " purple";
  }
  
  
 $(document).ready(function(){
    $("#manage-answer-btn").click(function(){
      $("#manage-answer").show("slow");
    });
    $("#manage-answer-btn").click(function(){
      $("#manage-answer-top").hide("slow");
    });
  });
  
