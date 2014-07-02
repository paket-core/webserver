function grabdeliverydiv(deliveryid, delivery){
    log(delivery);
    return '<div><a href="delivery?id=' + deliveryid + '">take delivery</a></div>'
}

function clickroute(delivery){
    L.polyline(delivery.path, {
        color: 'red',
        dashArray: '5, 6, 2, 6',
        weight: '2',
    }).addTo(map);
}

// Show all deliveries originating (default) or arriving within a circle.
function getdeliveries(position, range, pointofinterest){
    jsonp(
        'deliveriesinrange',
        {
            'lat': position.lat,
            'lng': position.lng,
            'radius': range,
            'pointofinterest': pointofinterest
        },
        function(deliveries){
            var fromMarkers = new L.MarkerClusterGroup({
                showCoverageOnHover: false, maxClusterRadius: 50
            });
            var toMarkers = new L.MarkerClusterGroup({
                showCoverageOnHover: false, maxClusterRadius: 50
            });

            L.circle(position, range * 110000,{
                color: 'red',
                weight: '0.5',
                fillColor: '#f00',
                fillOpacity: 0.1
            }).addTo(map);

            $.each(deliveries, function(id, delivery){

                // TODO: Here I filter out commited deliveries, but better to find a nice way to show them.
                if(0 < delivery.status) return true;
                addmarkertolayer(
                    delivery['fromlatlng'],
                    'green_flag_icon',
                    [1, 30],
                    'from here to ' + (
                        delivery['toaddress'] ?
                        delivery['toaddress'] :
                        delivery['tolatlng']
                    ) + grabdeliverydiv(id, delivery),
                    function(e){clickroute(delivery)},
                    fromMarkers
                );
                addmarkertolayer(
                    delivery['tolatlng'],
                    'pink_flag_icon',
                    [1, 30],
                    'from ' + (
                        delivery['fromaddress'] ?
                        delivery['fromaddress'] :
                        delivery['fromlatlng']
                    ) + ' to here' + grabdeliverydiv(id),
                    function(e){clickroute(delivery)},
                    toMarkers
                );
            });
            map.addLayer(fromMarkers);
            map.addLayer(toMarkers);
        }
    );
}

$(function(){
    getcurrentposition(function(latlng, accuracy){
        map.setView([latlng.lat, latlng.lng], 13);
        var range = '0.02';
        addmarkertolayer(
            [latlng.lat, latlng.lng],
            'cyan_pin_icon',
            [9, 30], 'you are ' + accuracy / 2 + ' meters from here',
            function(e){;},
            map
        );

        getdeliveries(latlng, range);
    });
});
