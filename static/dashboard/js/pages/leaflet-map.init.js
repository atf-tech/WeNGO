const MAPBOX_TOKEN = document.querySelector('meta[name="mapbox-token"]')?.content?.trim() || "";
const USE_MAPBOX = Boolean(MAPBOX_TOKEN);
const MAPBOX_URL = `https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token=${MAPBOX_TOKEN}`;
const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const MAPBOX_ATTRIBUTION =
  'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, <a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>';
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors';

function createTileLayer(styleId) {
  if (USE_MAPBOX) {
    return L.tileLayer(MAPBOX_URL, {
      maxZoom: 18,
      attribution: MAPBOX_ATTRIBUTION,
      id: styleId,
      tileSize: 512,
      zoomOffset: -1,
    });
  }

  return L.tileLayer(OSM_TILE_URL, {
    maxZoom: 18,
    attribution: OSM_ATTRIBUTION,
  });
}

const mymap = L.map("leaflet-map").setView([51.505, -0.09], 13);
createTileLayer("mapbox/streets-v11").addTo(mymap);

const markermap = L.map("leaflet-map-marker").setView([51.505, -0.09], 13);
createTileLayer("mapbox/streets-v11").addTo(markermap);
L.marker([51.5, -0.09]).addTo(markermap);
L.circle([51.508, -0.11], {
  color: "#0ab39c",
  fillColor: "#0ab39c",
  fillOpacity: 0.5,
  radius: 500,
}).addTo(markermap);
L.polygon(
  [
    [51.509, -0.08],
    [51.503, -0.06],
    [51.51, -0.047],
  ],
  { color: "#405189", fillColor: "#405189" }
).addTo(markermap);

const popupmap = L.map("leaflet-map-popup").setView([51.505, -0.09], 13);
createTileLayer("mapbox/streets-v11").addTo(popupmap);
L.marker([51.5, -0.09])
  .addTo(popupmap)
  .bindPopup("<b>Hello world!</b><br />I am a popup.")
  .openPopup();
L.circle([51.508, -0.11], {
  color: "#f06548",
  fillColor: "#f06548",
  fillOpacity: 0.5,
})
  .addTo(popupmap)
  .bindPopup("I am a circle.");
L.polygon(
  [
    [51.509, -0.08],
    [51.503, -0.06],
    [51.51, -0.047],
  ],
  { color: "#405189", fillColor: "#405189" }
)
  .addTo(popupmap)
  .bindPopup("I am a polygon.");

const customiconsmap = L.map("leaflet-map-custom-icons").setView([51.5, -0.09], 13);
L.tileLayer(OSM_TILE_URL, {
  maxZoom: 18,
  attribution: OSM_ATTRIBUTION,
}).addTo(customiconsmap);

const LeafIcon = L.Icon.extend({
  options: {
    iconSize: [45, 45],
    iconAnchor: [22, 94],
    popupAnchor: [-3, -76],
  },
});

const greenIcon = new LeafIcon({ iconUrl: "assets/images/logo-sm.png" });
L.marker([51.5, -0.09], { icon: greenIcon }).addTo(customiconsmap);

const interactivemap = L.map("leaflet-map-interactive-map").setView([37.8, -96], 4);
createTileLayer("mapbox/light-v9").addTo(interactivemap);

function getColor(e) {
  return e > 1000
    ? "#405189"
    : e > 500
    ? "#516194"
    : e > 200
    ? "#63719E"
    : e > 100
    ? "#7480A9"
    : e > 50
    ? "#8590B4"
    : e > 20
    ? "#97A0BF"
    : "#A8B0C9";
}

function style(e) {
  return {
    weight: 2,
    opacity: 1,
    color: "white",
    dashArray: "3",
    fillOpacity: 0.7,
    fillColor: getColor(e.properties.density),
  };
}

L.geoJson(statesData, { style }).addTo(interactivemap);

const cities = L.layerGroup();
L.marker([39.61, -105.02]).bindPopup("This is Littleton, CO.").addTo(cities);
L.marker([39.74, -104.99]).bindPopup("This is Denver, CO.").addTo(cities);
L.marker([39.73, -104.8]).bindPopup("This is Aurora, CO.").addTo(cities);
L.marker([39.77, -105.23]).bindPopup("This is Golden, CO.").addTo(cities);

const grayscale = createTileLayer("mapbox/light-v9");
const streets = createTileLayer("mapbox/streets-v11");

const layergroupcontrolmap = L.map("leaflet-map-group-control", {
  center: [39.73, -104.99],
  zoom: 10,
  layers: [streets, cities],
});

const baseLayers = { Grayscale: grayscale, Streets: streets };
const overlays = { Cities: cities };
L.control.layers(baseLayers, overlays).addTo(layergroupcontrolmap);
