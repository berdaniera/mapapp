Number.prototype.round = function(places) {
  return +(Math.round(this + "e+" + places)  + "e-" + places);
}
var coo;
var latd;
var lond;
var coors;
var map = L.map('mapbox').setView([36, -78], 5);
L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpandmbXliNDBjZWd2M2x6bDk3c2ZtOTkifQ._QA7i5Mpkd_m30IGElHziw', {
  maxZoom: 12,
  minZoom: 3,
  attribution: '',
  id: 'mapbox.streets'
}).addTo(map);

coo = map.getCenter();
if(coo.lat < 0){ latd='°S // '; }else{ latd='°N // '; }
if(coo.lng < 0){ lond='°W '; }else{ lond='°E '; }
coors = Math.abs(coo.lat.round(1)) + latd + Math.abs(coo.lng.round(1)) + lond;

map.on('dragend', function(){
  coo = map.getCenter();
  if(coo.lat < 0){ latd='°S // '; }else{ latd='°N // '; }
  if(coo.lng < 0){ lond='°W'; }else{ lond='°E'; }
  coors = Math.abs(coo.lat.round(1)) + latd + Math.abs(coo.lng.round(1)) + lond;
  //console.log(coors);
  $("#coordinates").text(coors);
});

// set clip
$('input[name=cut]').change(function() {
  $(".crop").hide();
  if($('input[name=cut]:checked').val()=="ctry"){
    $("#ctry").show();
  } else if($('input[name=cut]:checked').val()=="stat") {
    $("#stat").show();
  }
});

var ar;
var arp;
var wid;
// change size
$('input[name=size]').change(function(){
  if($('input[name=size]:checked').val()=="1824"){
    $("#price").text("$40");
    ar = 0.8; // map aspect ratio
    //arp = 0.75; // document aspect ratio
    $('#orderAmt').val("4000");
    $("#price-final").text("$40");
  } else { // 24x36
    $("#price").text("$50");
    ar = 0.688; // map aspect ratio
    //arp = 0.667; // document aspect ratio
    $('#orderAmt').val("5000");
    $("#price-final").text("$50");
  }
  if($('input[name=orient]:checked').val()=='landscape'){
    $("#mapbox").width( $("#mapbox").height()/ar );
    //$('#proofimg').width( $("#mapbox").height()/arp ); // switch width
  }else{
    $("#mapbox").height( $("#mapbox").width()/ar );
    //$("#proofimg").height( $("#proofimg").width()/arp );
  }
  map.invalidateSize();
});
// change orientation
$('input[name=orient]').change(function(){
  wid = $("#mapbox").width();
  $("#mapbox").width( $("#mapbox").height() );
  $("#mapbox").height( wid );
  //widp = $("#proofimg").width();
  //$("#proofimg").width( $("#proofimg").height() );
  //$("#proofimg").height( widp );
  map.invalidateSize();
});
// check custom text
$('input[name=customtext]').change(function(){
  if($('input[name=customtext]').val().length>0){
    $("#customtext").text($('input[name=customtext]').val().toUpperCase());
  }else{
    $("#customtext").text("CITY, STATE, COUNTRY");
  }
});

// reset
$(function(){
$("button#backup").click(function(){
  $('#checkout').hide();
  $("button#proof").prop("disabled", false);
})
});
$(function(){
$("button#backupa").click(function(){
  $('#prooferr').hide();
  $("button#proof").prop("disabled", false);
})
});


// generate proof
$(function(){
$("button#proof").click(function(){
  console.log(map.getBounds());
  $("#loading").show();
  $("button#proof").prop("disabled", true);
  $('html, body').animate({
    scrollTop: $("#loading").offset().top
  },500);
  var data = {};
  data['xmin'] = map.getBounds()._southWest.lng;
  data['xmax'] = map.getBounds()._northEast.lng;
  data['ymin'] = map.getBounds()._southWest.lat;
  data['ymax'] = map.getBounds()._northEast.lat;
  var textm = $('input[name=customtext]').val().toUpperCase(); // title
  if (typeof textm == 'undefined') textm = "";
  data['textm'] = textm;
  data['textc'] = coors;// coordinates
  data['size'] = $('input[name=size]:checked').val();
  data['shape'] = $('input[name=orient]:checked').val();
  if($('input[name=cut]:checked').val()=="ctry"){
    data['clip'] = $('#countries').val();
  } else if($('input[name=cut]:checked').val()=="stat") {
    data['clip'] = $("#states").val();
  }else{
    data['clip'] = '';
  };
  $.ajax({
    type: 'POST',
    url:'/_proof',
    data: JSON.stringify(data),
    contentType: 'application/json;charset=UTF-8',
    success: function(response){
      $('#orderId').val(response.result);
      $('#orderData').val(JSON.stringify(response.params));
      var imgsrc = "/static/proofs/".concat(response.result,".png");
      $("#loading").hide();
      $('#checkout').show();
      //$('#proofimg').css({'background-image':'url('+imgsrc+')', 'background-size':'cover', 'background-position':'center'})
      $('#proofimg img').attr('src',imgsrc);//append('<img src="'+imgsrc+'">')
    },
    error: function(error){
      console.log(error);
      $('#prooferr').show();
      $("#loading").hide();
    }
  });
});
});

// check coupon
$(function(){
  $("button#coupon-check").click(function(){
    var data = {};
    data['coupon'] = $('input[name=coupon-code]').val();
    $.ajax({
      type: 'POST',
      url:'/_coupon-check',
      data: JSON.stringify(data),
      contentType: 'application/json;charset=UTF-8',
      success: function(response){
        if(response.res==1){
          var discount = 1 - response.disc;
          $('#coupon-group').attr("class","form-group has-success");
          var discountprice = discount * parseInt($('#orderAmt').val());
          $('#orderAmt').val(discountprice.toString());
          discountprice = discountprice/100
          $("#price-final").text("$"+discountprice.toString());
        }else{
          $('#coupon-group').attr("class","form-group has-warning");
        }
      },
      error: function(error){
        console.log(error);
      }
    });
  });
});

// email form
$(function(){
  $("button#email-list").click(function(){
    var data = {};
    data['email'] = $('input[name=email-list]').val();
    $.ajax({
      type: 'POST',
      url:'/_email-list',
      data: JSON.stringify(data),
      contentType: 'application/json;charset=UTF-8',
      success: function(response){
        console.log(response.result);
        $('input[name=email-list]').val("");
        $('#email-group').attr("class","form-group has-success");
      },
      error: function(error){
        console.log(error);
      }
    });
  });
});

// Collect payment
$(function() {
  $("button#pay").click(function(event){
    // Disable the submit button to prevent repeated clicks:
    $('button#pay').prop('disabled', true);
    // Request a token from Stripe:
    Stripe.card.createToken($('#payment-form'), stripeResponseHandler);
    // Prevent the form from being submitted:
    return false;
  });
});
function stripeResponseHandler(status, response) {
  if (response.error) { // Problem!
    // Show the errors on the form:
    $('#payment-form').find('.payment-errors').text(response.error.message);
    $('button#pay').prop('disabled', false); // Re-enable submission
  } else { // Token was created!
    // Get the token ID:
    var token = response.id;
    // Insert the token ID into the form so it gets submitted to the server:
    $('#payment-form').append($('<input type="hidden" name="stripeToken">').val(token));
    // Submit the form:
    $('#payment-form').get(0).submit();
    // console.log(token);
  }
};
