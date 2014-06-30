// Formatted time.
function now(d){
    if('undefined' === typeof(d)) d = new Date();
    var padded = $.map(
        [
            d.getMonth() + 1,
            d.getDate(),
            d.getHours(),
            d.getMinutes(),
            d.getSeconds()
        ],
        function(c){
            return (c < 10 ? '0' : '') + c;
        }
    );
    padded.unshift(d.getFullYear());
    return padded.slice(0, 3).join('-') + ' ' +  padded.slice(3).join(':');
}

// Log arguments to console, show first argumentst if it's a string.
function log(msg){
    console.log(arguments);
    if('string' === typeof msg) $('#log').prepend($('<div>').html(now() + ' ' + msg));
}

// JSONp request with data and callback.
function jsonp(method, data, callback){
    $.ajax({
        url: method,
        dataType: 'jsonp',
        data: data,
        success:function(data){
            if(null !== data && 'string' === typeof data.error) log(data.error);
            callback(data);
        },
        error:function(){
            log('Unable to retrieve ' + method);
        }
    });
};

// Call a callback with current position.
// TODO The should be a cookie that remembers your last position or something.
function getcurrentposition(callback, manual){
    // Manual prompting for non mobile devices
    if('undefined' !== typeof(manual) || /i686/i.test(navigator.userAgent)){
        var position = '32.0695:34.7987'.split(':');
        callback({'lat': position[0], 'lng': position[1]}, 0);
    }else{
        map.on('locationerror', function onLocationError(e){
            log(e.message, e);
            return getcurrentposition(callback, true);
        });
        map.on('locationfound', function(e){
            callback(e.latlng, e.accuracy);
        });
        map.locate({setView: true, maxZoom: 14, timeout: 3000});
    }
}

$(function(){
    $('#nojs').remove();

    getcurrentposition(function(latlng, accuracy){
        var range = '0.2';
        jsonp(
            'deliveriesinrange',
            {
                'lat': latlng.lat,
                'lng': latlng.lng,
                'radius': '0.2',
                'pointofinterest': 'to'
            },
            function(deliveries){
                $.each(deliveries, function(id, delivery){
                    log('!!!', delivery);
                });
            }
        );
    });
});
