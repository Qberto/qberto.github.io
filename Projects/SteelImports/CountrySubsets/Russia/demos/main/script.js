require([
  'Canvas-Flowmap-Layer/CanvasFlowmapLayer',
  'esri/graphic',
  'esri/map',
  'esri/layers/FeatureLayer',
  'local-resources/config',
  'dojo/domReady!'
], function(
  CanvasFlowmapLayer,
  Graphic,
  Map,
  FeatureLayer,
  config
) {
  var map = new Map('map', {
    basemap: 'dark-gray-vector',
    center: [169.855494, 41.616024],
    zoom: 2
  });

  map.on('load', function() {
    var cityToCityLayer = new CanvasFlowmapLayer({
      // JSAPI GraphicsLayer constructor properties
      id: 'cityToCityLayer',
      visible: true,
      // CanvasFlowmapLayer custom constructor properties
      //  - required
      originAndDestinationFieldIds: config.originAndDestinationFieldIds,
      //  - optional
      pathDisplayMode: 'all', // 'selection' or 'all'
      wrapAroundCanvas: true,
      animationStarted: true
    });

    map.addLayer(cityToCityLayer);
    
    // var originLayer = new FeatureLayer("https://services.arcgis.com/hRUr1F8lE8Jq2uJo/arcgis/rest/services/BIS_steel_import_origins_FS/FeatureServer/0");
    // var destLayer = new FeatureLayer("https://services.arcgis.com/hRUr1F8lE8Jq2uJo/ArcGIS/rest/services/BIS_steel_imports_destinations/FeatureServer/0");

    // map.addLayer(originsLayer);
    // map.addLayer(destLayer);

    // here we use Papa Parse to load and read the CSV data
    // we could have also used another library like D3js to do the same
    Papa.parse('../csv-data/Flowmap_Cities_one_to_many.csv', {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: function(results) {
        var csvGraphics = results.data.map(function(datum) {
          return new Graphic({
            geometry: {
              x: datum.s_lon,
              y: datum.s_lat,
              spatialReference: {
                wkid: 4326
              }
            },
            attributes: datum
          });
        });

        // add all graphics to the canvas flowmap layer
        cityToCityLayer.addGraphics(csvGraphics);
      }
    });

    cityToCityLayer.on('click', function(evt) {
      // evt.sharedOriginGraphics: array of all ORIGIN graphics with the same ORIGIN ID field
      // evt.sharedDestinationGraphics: array of all ORIGIN graphics with the same DESTINATION ID field
      //  - you can mark shared origin or destination graphics as selected for path display using these modes:
      //    - 'SELECTION_NEW', 'SELECTION_ADD', or 'SELECTION_SUBTRACT'
      //  - these selected graphics inform the canvas flowmap layer which paths to display

      // NOTE: if the layer's pathDisplayMode was originally set to "all",
      // this manual selection will override the displayed paths
      if (evt.sharedOriginGraphics.length) {
        cityToCityLayer.selectGraphicsForPathDisplay(evt.sharedOriginGraphics, 'SELECTION_NEW');
      }
      if (evt.sharedDestinationGraphics.length) {
        cityToCityLayer.selectGraphicsForPathDisplay(evt.sharedDestinationGraphics, 'SELECTION_NEW');
      }
    });
  });
});
