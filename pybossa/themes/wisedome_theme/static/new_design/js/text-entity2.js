"use strict";


function validateNum() {
    var numInput1 = document.getElementById("start_num");
    var numInput2 = document.getElementById("end_num");
    var errorDiv = document.getElementById("error");
    try {
       if(/\d/.test(numInput1.value) === false){ 
          throw "숫자를 입력하여 주시기 바랍니다";
       }else if(/\d/.test(numInput2.value) === false){
          throw "숫자를 입력하여 주시기 바랍니다";
       }
       numInput1.style.borderColor = "";
       numInput2.style.background = "";
       errorDiv.style.display = "none";
       errorDiv.innerHTML = "";
    }
    catch(msg) { 
       errorDiv.style.display = "block";
       errorDiv.innerHTML = msg;
       numInput1.style.borderColor = "orangered"; 
       numInput2.style.borderColor = "orangered";       
    }
 }



 function createEventListeners() {

    var numInput1 = document.getElementById("start_num");
    var numInput2 = document.getElementById("end_num");
 
    if (numInput1.addEventListener) {  
       numInput1.addEventListener("change",validateNum, false); 
       numInput2.addEventListener("change",validateNum, false); 
    } else if (numInput1.attachEvent) {
       numInput1.attachEvent("onchange",validateNum);
       numInput2.attachEvent("onchange",validateNum);
    }
}

    if (window.addEventListener) {
        window.addEventListener("load", createEventListeners, false);
     } else if (window.attachEvent) {
        window.attachEvent("onload", createEventListeners);
     }     