
//프리미엄 프로젝트 스와이프 동작

  var swiper = new Swiper('.swiper-container', {
    slidesPerView: 4,
    spaceBetween: 20,
    // init: false,
 /**   autoplay: {
      delay: 2000,
      disableOnInteraction: false,
    },

    **/
  pagination: {
      el: '.swiper-pagination',
      clickable: true,
    },
navigation: {
nextEl: '.swiper-button-next',
prevEl: '.swiper-button-prev',
},    

breakpoints: {
1320: {
slidesPerView: 4,
spaceBetween: 20,
},
1280: {
  slidesPerView: 4,
  spaceBetween: 10,
  },
1024: {
slidesPerView: 3,
spaceBetween: 20,
},
991: {
  slidesPerView: 3,
  spaceBetween: 10,
  },
768: {
slidesPerView: 2,
spaceBetween: 15,
},
480: {
slidesPerView: 1,
spaceBetween: 10,
}
}
});