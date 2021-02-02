(function ($) {
  "use strict";
  var form = $("#example-form");
  form.children("div").steps({
    headerTag: "h3",
    bodyTag: "section",
    transitionEffect: "slideLeft",
    onFinished: function (event, currentIndex) {
      document.getElementById("finish").style.display = "block";
    },
  });
  var validationForm = $("#example-validation-form");
  validationForm.val({
    errorPlacement: function errorPlacement(error, element) {
      element.before(error);
    },
    rules: {
      confirm: {
        equalTo: "#password",
      },
    },
  });
  validationForm.children("div").steps({
    headerTag: "h3",
    bodyTag: "section",
    transitionEffect: "slideLeft",
    onStepChanging: function (event, currentIndex, newIndex) {
      validationForm.val({
        ignore: [":disabled", ":hidden"],
      });
      return validationForm.val();
    },
    onFinishing: function (event, currentIndex) {
      validationForm.val({
        ignore: [":disabled"],
      });
      return validationForm.val();
    },
    onFinished: function (event, currentIndex) {
      alert("Submitted!");
    },
  });

})(jQuery);


//price amount add comma
function inputNumberFormat(obj) {
  obj.value = comma(uncomma(obj.value));
}

function comma(str) {
  str = String(str);
  return str.replace(/(\d)(?=(?:\d{3})+(?!\d))/g, '$1,');
}

function uncomma(str) {
  str = String(str);
  return str.replace(/[^\d]+/g, '');
}

$("input:text[numberOnly]").on("keyup", function() {
  $(this).val($(this).val().replace(/[^0-9]/g,""));
});



// if input empty display warning
const accountName = document.getElementById('userName');
const bank = document.getElementById('bankAccount');

$(document).ready(function() { 
  $(accountName && bank).on('input', function() {
      if ($(accountName && bank ).val() == '') {

          $('#confirm-page').css({
              'display': 'none'
          });
          $('#fail-page').css({
            'display': 'block'
          });

      } else {
          $('#confirm-page').css({
              'display': 'block'
          });
          $('#fail-page').css({
            'display': 'none'
        });
      }
  });
})

//agree to policy check
$(document).ready(function(){
  $("#checkPolicy").change(function(){
      if($("#checkPolicy").is(":checked")){
          $("#chkConfirm").css("display","none");
      }else{
        $("#chkConfirm").css("display","block");
      }
  });
});

//name print
function printName()  {
  const name = document.getElementById('userName').value;
  document.getElementById("result").innerText = name;
}