$(document).foundation();

$(function(){
    $(".star_style").hover(function() {
        if ($(this).hasClass('fixedStar')) {
            return;
        }
        var rating = calculateStarRatingFromDom(jQuery(this));
        var sectionDom = $(this).closest('div[id^="reviewCat"]');
        showStarsSelected(sectionDom, rating, false);
    });

    $(".star_style").click(function() {
        var thisDom = $(this);
        var rating = calculateStarRatingFromDom(thisDom);
        var sectionDom = thisDom.closest('div[id^="reviewCat"]');
        fixStarsSelected(sectionDom);
        showStarsSelected(sectionDom, rating, true);
        var idtag = sectionDom.attr("id");
        // console.log("idtag: " + idtag);
        var catIndex = idtag.search("reviewCat_") + 10;
        var isbnIndex = idtag.search("&isbn_") + 6;
        // console.log("catIndex: " + catIndex.toString() + " isbnIndex: " + isbnIndex.toString());
        var cat = idtag.substring(catIndex, isbnIndex - 6);
        // console.log(idtag.length);
        var isbn = idtag.substring(isbnIndex);
        // console.log("cat: "+cat+" isbn: "+isbn);
        var dataString = "isbn=" + isbn + "&cat=" + cat + "&rating=" + rating;
        // console.log(dataString);
        $.ajax({
            type: "POST",
            url: "/api/_updateuserreviews?",
            data: dataString,
            success: function(data) {
                console.log("successful");
            }
        });
    });
});

calculateStarRatingFromDom = function(starDom) {
    var ratingIndex=starDom.attr("class").indexOf("rating_")+7;
    return parseInt(starDom.attr("class").charAt(ratingIndex),10);
};

getStarsDomList = function(sectionDom) {
    return $(sectionDom).find(".star_style");
};

showStarsSelected = function(sectionDom, rating, reset) {
    getStarsDomList(sectionDom).each(function(){
        var thisDom=jQuery(this);
        var ratingIndex=thisDom.attr("class").search("rating_")+7;
        if(parseInt(thisDom.attr("class").charAt(ratingIndex),10)<=rating) {
            if (reset) {
                thisDom.removeClass('highlight_star');
                thisDom.addClass('highlight_star');
            } else {
                thisDom.toggleClass('highlight_star');
            }
        } else {
            thisDom.removeClass('highlight_star');
        }
    });
};

fixStarsSelected = function(sectionDom) {
    getStarsDomList(sectionDom).each(function(){
        var thisDom=jQuery(this);
        thisDom.addClass('fixedStar');
    });
};
