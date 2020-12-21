//아코디언메뉴
let accordion = document.querySelector('.accordion');
let items = accordion.querySelectorAll('.accordion__item');
let title = accordion.querySelectorAll('.accordion__title');

function toggleAccordion() {
  let thisItem = this.parentNode;
  
  items.forEach(item => {
    if (thisItem == item ) {

      thisItem.classList.toggle('active');
      return;
    } 
    item.classList.remove('active');
  });
}

title.forEach(question => question.addEventListener('click', toggleAccordion));



///선택형 화면에서 답선택하면 next버튼 나타남
$(document).ready(function () {
	$("#check1").click(function () {
			$(".next").css("display", "block");
	});
	$("#check2").click(function () {
			$(".next").css("display", "block");
  });
  $("#check3").click(function () {
    $(".next").css("display", "block");
  });
  $("#check4").click(function () {
    $(".next").css("display", "block");
  });
});



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

