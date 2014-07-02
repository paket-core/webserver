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

// Mark a spot in the map.
function addmarkertolayer(latlng, iconname, iconanchor, text, click, layer){
    var icon =  L.icon({
        iconUrl: '/static/images/' + iconname + '.png',
        iconSize: [32, 32],
        iconAnchor: iconanchor,
    });
    var marker = L.marker([latlng[0], latlng[1]], {'icon': icon}).bindPopup(text).on('click', click);
    layer.addLayer(marker);
}

var map;

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

// General startup.
$(function(){
    $('#nojs').remove();

    // Initialize, center and zoom map.
    map = L.map('map');
    source_mapbox = 'https://{s}.tiles.mapbox.com/v3/{id}/{z}/{x}/{y}.png'
    source_openstreetmap = 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
    source_opencyclemap = 'http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png'

    // TODO https://gist.github.com/mourner/1804938 for a better solution.
    L.tileLayer(source_mapbox, {
        attribution:
            'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
        id: 'examples.map-zr0njcqy'
    }).addTo(map);
    map.setView([0, 0], 1);
});
