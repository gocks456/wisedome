/***
function validate() {
  var checkBox = document.getElementById("agreement");
  var text = document.getElementById("alert");

  if (checkBox.checked == true){
    text.style.display = "block";
  } else {
     text.style.display = "none";
  }
}
***/

/****이용약관 동의안하면 표시 */
function DoCheck(d,dchecked,dunchecked)
{
   if( d.checked == true )
   {
      document.getElementById(dchecked).style.display = "block";
      document.getElementById(dunchecked).style.display = "none";
      return;
   }
   else
   {
      document.getElementById(dchecked).style.display = "none";
      document.getElementById(dunchecked).style.display = "block";
   }

}

/***가입하기 누르면 */
function chk()
{
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
 

 


/**모달팝업창**/
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



