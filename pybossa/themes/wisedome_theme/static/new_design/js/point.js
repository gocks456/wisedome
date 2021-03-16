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



//Register account
$(function() {
  $('#userName').on('keyup',function() {
	  if( $(this).val() == "" ){
		  $('.error-name').css("display","block");
	  }
	  else {
		  $('.error-name').css("display","none");
	  }
  });
});


//bank account
  $(document).ready(function() {
	  if($('#bank option:selected').length == 0){
		  $('.error-bank').css("display","block");
	  }
	  else {
		  $('.error-bank').css("display","none");
	  }
  });

//Register account
$(function() {
  $('#bankAccount').on('keyup',function() {
	  if( $(this).val() == "" ){
		  $('.error-account').css("display","block");
	  }
	  else {
		  $('.error-account').css("display","none");
	  }
  });
});



//은행이름 젤 마지막단계에 띄우기
  $(document).ready(function(){
    $('#bank').on('change',function(){
        //var optionValue = $(this).val();
        //var optionText = $('#bank option[value="'+optionValue+'"]').text();
        var optionText = $("#bank option:selected").text();
        $('#bankName').html(optionText);
    });
});





//name print
function printName()  {
  const name = document.getElementById('userName').value;
  document.getElementById("result").innerText = name;
}

//금액 print
function printTransferMoney()  {
  const price = document.getElementById('price').value;
  document.getElementById("transferMoney").innerText = price;
}
document.querySelector(".wizard .actions ul li:nth-child(2) a").addEventListener("click",printTransferMoney,false); 


