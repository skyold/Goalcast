var defaultDemoLeague=2012;
var rootURL = $('#rootURL').text();

$('a.showAll').on('click',function(e){
	$(this).hide();
	$('.dataPoints').css("max-height", "none");
});

$('.navbar-toggler').on('click',function(e){
	var toggleObj = $(this).data('target');
	$(toggleObj).toggleClass("collapse");
});

$('a[href*="#"]')
  // Remove links that don't actually link to anything
  .not('[href="#"]')
  .not('[href="#0"]')
  .click(function(event) {
    // On-page links
    if (
      location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') 
      && 
      location.hostname == this.hostname
    ) {
      // Figure out element to scroll to
      var target = $(this.hash);
      target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
      // Does a scroll target exist?
      if (target.length) {
        // Only prevent default if animation is actually gonna happen
        event.preventDefault();
        $('html, body').animate({
          scrollTop: target.offset().top - 100
        }, 600, function() {
          // Callback after animation
          // Must change focus!
          var $target = $(target);
          $target.focus();
          if ($target.is(":focus")) { // Checking if the target was focused
            return false;
          } else {
            $target.attr('tabindex','-1'); // Adding tabindex for elements not focusable
            $target.focus(); // Set focus again
          };
        });
      }
    }
  });

// AJAX Stuff

	$('#league-selector li').on('click',function(e){
		iso = $(this).data('country');
		$('.league-data').css('display','none');
		$('#leagues-'+iso).css('display','block');
	});

	// Convert Normal Data

	function convertDate(date){
		let convertDate = parseInt((new Date(date).getTime() / 1000).toFixed(0));
		return convertDate;
	}

function loading(status){
	 $('.demo-section .terminal ul.data').html("<ul><li>Loading API Data...</li></ul>");
}

$('.demoDatePicker').change(function() {

	loading();
	date_u = $("#date").val();
	date_u = convertDate(date_u);

	    $.ajax({
	      url: rootURL + "api-site/ajax_landingPage.php?type=demoData&id=" + defaultDemoLeague + "&date_u="+date_u,
	      type:"GET", 
	      data: {'rootURL': rootURL},
	      success:function(html) {
	        $('.demo-section .terminal ul.data').html(html);
	      }
	    });

});


	// Demo Data

	$('a.demoToggle').on('click',function(e){

		id = $(this).data('id');
		loading();
		defaultDemoLeague = id;
		date_u = $("#date").val();
		date_u = convertDate(date_u);
		$('.demoToggle').removeClass('active');
		$(this).addClass('active');

	    $.ajax({
    	  url: rootURL + "api-site/ajax_landingPage.php?type=demoData&id=" + id + "&date_u="+date_u,
	      type:"GET",
	      data: {'rootURL': rootURL},
	      success:function(html) {
	        $('.demo-section .terminal ul.data').html(html);
	      }
	    });

   });

// $('[data-side="front"]').data('params');

$(document).on('click','.ui-expand-link', function(e){

	id = $(this).data('uid');
	link = $(this);
	target = $(".ui-expand-target[data-uid=" + id + "]");

	expandContent(id, link, target);

});


// Show and Hide Content

function toggleContent(id, link, target){
	$('.ui-toggle-target').hide();
	$('.ui-toggle-link').removeClass('active');
	$(link).addClass('active');
	$(target).addClass('active').show();
}


$(document).on('click','.ui-toggle-link', function(e){
	id = $(this).data('id');
	link = $(this);
	target = $('.ui-toggle-target#' + id);
	toggleContent(id, link, target);
});
// Video Modal JS

"use strict";var _typeof=typeof Symbol==="function"&&typeof Symbol.iterator==="symbol"?function(obj){return typeof obj}:function(obj){return obj&&typeof Symbol==="function"&&obj.constructor===Symbol&&obj!==Symbol.prototype?"symbol":typeof obj};(function umd(factory){"use strict";if(typeof define==="function"&&define.amd){define(["jquery"],factory)}else if((typeof exports==="undefined"?"undefined":_typeof(exports))==="object"){module.exports=factory(require("jquery"))}else{factory(jQuery)}})(function modalVideo($){var defaults={channel:"youtube",youtube:{autoplay:1,cc_load_policy:1,color:null,controls:1,disablekb:0,enablejsapi:0,end:null,fs:1,h1:null,iv_load_policy:1,list:null,listType:null,loop:0,modestbranding:null,origin:null,playlist:null,playsinline:null,rel:0,showinfo:1,start:0,wmode:"transparent",theme:"dark"},ratio:"16:9",vimeo:{api:false,autopause:true,autoplay:true,byline:true,callback:null,color:null,height:null,loop:false,maxheight:null,maxwidth:null,player_id:null,portrait:true,title:true,width:null,xhtml:false},allowFullScreen:true,animationSpeed:300,classNames:{modalVideo:"modal-video",modalVideoClose:"modal-video-close",modalVideoBody:"modal-video-body",modalVideoInner:"modal-video-inner",modalVideoIframeWrap:"modal-video-movie-wrap",modalVideoCloseBtn:"modal-video-close-btn"},aria:{openMessage:"You just openned the modal video",dismissBtnMessage:"Close the modal by clicking here"}};function getQueryString(obj){var url="";for(var key in obj){if(obj.hasOwnProperty(key)){if(obj[key]!==null){url+=key+"="+obj[key]+"&"}}}return url.substr(0,url.length-1)}function getYoutubeUrl(youtube,videoId){var query=getQueryString(youtube);return"//www.youtube.com/embed/"+videoId+"?"+query}function getVimeoUrl(vimeo,videoId){var query=getQueryString(vimeo);return"//player.vimeo.com/video/"+videoId+"?"+query}function getVideoUrl(opt,videoId){if(opt.channel==="youtube"){return getYoutubeUrl(opt.youtube,videoId)}else if(opt.channel==="vimeo"){return getVimeoUrl(opt.vimeo,videoId)}}function getPadding(ratio){var arr=ratio.split(":");var width=Number(arr[0]);var height=Number(arr[1]);var padding=height*100/width;return padding+"%"}function getHtml(opt,videoId){var videoUrl=getVideoUrl(opt,videoId);var padding=getPadding(opt.ratio);return'\n\t\t\t\t\t<div class="'+opt.classNames.modalVideo+'" tabindex="-1" role="dialog" aria-label="'+opt.aria.openMessage+'">\n\t\t\t\t\t\t<div class="'+opt.classNames.modalVideoBody+'">\n\t\t\t\t\t\t\t<div class="'+opt.classNames.modalVideoInner+'">\n\t\t\t\t\t\t\t\t<div class="'+opt.classNames.modalVideoIframeWrap+'" style="padding-bottom:'+padding+'">\n\t\t\t\t\t\t\t\t\t<button class="'+opt.classNames.modalVideoCloseBtn+' js-modal-video-dismiss-btn" aria-label="'+opt.aria.dismissBtnMessage+"\"/>\n\t\t\t\t\t\t\t\t\t<iframe width='460' height='230' src=\""+videoUrl+"\" frameborder='0' allowfullscreen="+opt.allowFullScreen+' tabindex="-1"/>\n\t\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>\n\t\t\t'}$.fn.modalVideo=function(opt){opt=$.extend({},defaults,opt);$(this).each(function(){if(!$(this).data("video-id")){$(this).data("video-id",opt.videoId)}});$(this).click(function(){var $me=$(this);var videoId=$me.data("video-id");var html=getHtml(opt,videoId);var $modal=$(html);var $btn=$modal.find(".js-modal-video-dismiss-btn");var speed=opt.animationSpeed;$("body").append($modal);$modal.focus();$modal.on("click",function(){var $self=$(this);$self.addClass(opt.classNames.modalVideoClose);$self.off("click");$self.off("keydown");$btn.off("click");setTimeout(function(){$self.remove();$me.focus()},speed)});$btn.on("click",function(){$modal.trigger("click")});$modal.on("keydown",function(e){if(e.which===9){e.preventDefault();if($modal.is(":focus")){$btn.focus()}else{$modal.attr("aria-label","");$modal.focus()}}})})}});
