var owl = $('.owl-carousel');
owl.owlCarousel({
    loop:true,
    rtl:true,
    nav:true,
    margin:10,
    responsive:{
        0:{
            items:1
        },
        575:{
            items:2
        },
        769:{
            items:3
        },           
        1025:{
            items:4
        },
        1620:{
            items:5
        }
    }
});
owl.on('mousewheel', '.owl-stage', function (e) {
    if (e.deltaY>0) {
        owl.trigger('next.owl');
    } else {
        owl.trigger('prev.owl');
    }
    e.preventDefault();
});


