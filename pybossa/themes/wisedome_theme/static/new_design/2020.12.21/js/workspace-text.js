//폰트 글자 키우기
function changeFontSize(className, fontSize) {
  for (let element of document.getElementsByClassName(className))
    element.style.fontSize =
      (typeof fontSize === "function" ? fontSize(element) : fontSize) + "px";
}

window.addEventListener("input", () => {
  const input = event.target;
  if (input.classList.contains("controlbar"))
    changeFontSize(input.dataset.fsTargetClass || "textsize", input.value);
});


//더블 화살표 위아래로 바뀜
function arrow(x) {
	x.classList.toggle("fa-chevron-up"); 
}


//나의 답변관리 숨겼다 나타내기
$(document).ready(function(){
  $("#manage-answer-btn").click(function(){
    $("#manage-answer").slideToggle("slow");
  });
});


///선택형 화면에서 답선택하면 next버튼 나타남
$(document).ready(function () {
	$("#edit").click(function () {
			$(".reselect").css("display", "block");
	});
});

