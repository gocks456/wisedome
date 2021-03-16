
//if click reset
  $('#myCancel').click(function(){ 
    $('#summernote').summernote('reset');
    $("#myQuestion").trigger("reset");
  });


//editor template
  $('#summernote').summernote({

    lang: "ko-KR",
    placeholder: "입력하세요",
    tabsize: 2,
    height: 250,

    toolbar: [
      ['style', ['style']],
      ['font', ['bold', 'underline', 'clear']],
      ['fontname', ['fontname']],
      ['color', ['color']],
      ['para', ['paragraph']],
      ['table', ['table']],
      ['insert', ['link', 'picture', 'video']],
      ['view', ['fullscreen', 'codeview', 'help']],
    ],
    
  });

  $('#summernote').summernote('foreColor','#76767a');