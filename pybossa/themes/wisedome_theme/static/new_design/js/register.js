/**modal**/
var modal = document.getElementById("myModal");
var btn = document.getElementById("read-detail");
var span = document.getElementsByClassName("close")[0];

btn.onclick = function() {
  modal.style.display = "block";}

span.onclick = function() {
  modal.style.display = "none";}

window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none"; }
}



/***가입하기 누르면 */
function chk(event){
    
   event.preventDefault();
    var fm  = document.join;

    for(var i=1; i<=2; i++)
    {
        if (!fm['enable'+i].checked)
        {
        alert("필수 이용약관에 모두 동의 해주시기 바랍니다")
            return false;
        }
    }

    fm.submit();
}
 

//이메일 인증번호 

function CustomAlert(){

  this.render = function(dialog){
      var winW = window.innerWidth;
      var winH = window.innerHeight;
      var dialogoverlay = document.getElementById('dialogoverlay');
      var dialogbox = document.getElementById('dialogbox');
      var emptyoverlay = document.getElementById('emptyoverlay');
      var emptybox = document.getElementById('emptybox');
      var value = document.getElementById('email_addr').value;

      if (value === '') {
        if (screen.width >= 768) {  emptybox.style.left = (winW/2) - (550 * .5)+"px";}
        emptyoverlay.style.display = "block";
        emptyoverlay.style.height = winH +"px";
        emptybox.style.top = "100px";
        emptybox.style.display = "block";
        document.getElementById('emptyboxhead').innerHTML = "이메일 입력";
        document.getElementById('emptyboxbody').innerHTML = '<h4>올바른 이메일을 입력해주시기 바랍니다</h4>';
        document.getElementById('emptyboxfoot').innerHTML = '<button onclick="Alert.ok()" class="btn-primary" >확   인</button>';
      }
      else{
        if (screen.width >= 768) {  dialogbox.style.left = (winW/2) - (550 * .5)+"px";}
        dialogoverlay.style.display = "block";
        dialogoverlay.style.height = winH+"px";
        dialogbox.style.top = "100px";
        dialogbox.style.display = "block";
        document.getElementById('dialogboxhead').innerHTML = "이메일인증";
        document.getElementById('timer').innerHTML = `${05} : ${00} `;  startTimer();
        document.getElementById('dialogboxbody').innerHTML ='<img src="../static/images/mail.svg" style="width: 15%;" >'+ '<h4>입력해주신 이메일로 인증번호가 전송되었습니다</h4>' + '<input type="text" class="input-field" placeholder="인증번호를 입력하세요" style="background:#fff;">';
        document.getElementById('dialogOk').innerHTML = '<button onclick="Alert.ok()" class="btn-primary" style="width:48%; float: left;  margin-bottom:1rem;" >확 인</button>';
      }
  }
this.ok = function(){
  document.getElementById('dialogbox').style.display = "none";
  document.getElementById('dialogoverlay').style.display = "none";
  document.getElementById('emptybox').style.display = "none";
  document.getElementById('emptyoverlay').style.display = "none";
}
}
var Alert = new CustomAlert();




function startTimer() {

  var presentTime = document.getElementById('timer').innerHTML;
  var timeArray = presentTime.split(/[:]+/);
  var m = timeArray[0];
  var s = checkSecond((timeArray[1] - 1));
  if(s==59){m=m-1}
  if(m<0){document.getElementById('dialogtime').innerHTML= '입력시간이 초과되었습니다';}
  document.getElementById('dialogResend').innerHTML = '<button onclick="resetTimer()" id="re-send-email"  class="btn-gradient-danger" style="width:48%; float: left; margin-right:0.5rem;">재전송</button>'; 
  document.getElementById('timer').innerHTML = `${m} : ${s}`;
  setTimeout(startTimer, 1000);
}

function resetTimer() {
 var reTimer = document.getElementById('timer').innerHTML =  `${05} : ${00} `;
  setTimeout(function(){ 
    reTimer();
    startTimer(); 
  });
}


function checkSecond(sec) {
  if (sec < 10 && sec >= 0) {sec = "0" + sec}; // add zero in front of numbers < 10
  if (sec < 0) {sec = "59"};
  return sec;
}