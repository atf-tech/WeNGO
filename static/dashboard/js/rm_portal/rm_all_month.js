console.log(document.getElementById("rm-categories"));
const rmCategories = JSON.parse(
    document.getElementById("rm-categories").textContent
);

const rmValues = JSON.parse(
    document.getElementById("rm-values").textContent
);
const maxValue = Math.max(...rmValues);
console.log("Categories:", rmCategories);
console.log("Values:", rmValues);
console.log("Is Categories Array:", Array.isArray(rmCategories));
console.log("Is Values Array:", Array.isArray(rmValues));

var options = {
    chart: {
      type: 'bar',
      height: 600,
      toolbar: { show: false }
    },
    series: [{
      name: "collection",
      data: rmValues
    }],
    xaxis: {
        categories: rmCategories,
        title: {
            text: "Collection (₹)"
        },
        min: 0,
      
        // Dynamic max (10% extra space)
        max: Math.ceil(maxValue * 1.1),
      
        tickAmount: 5,
      
        labels: {
            formatter: function (val) {
                return "₹ " + Number(val).toLocaleString("en-IN");
            }
        }
    },
    yaxis: {
      title: { text: "collection (in all RM's)" }
    },
    colors: ["#00E396"],
    plotOptions: {
      bar: {
        borderRadius: 4,
        borderRadiusApplication: 'end',
        horizontal: true,
      }
    },
    dataLabels: {
      enabled: true,
      style: { fontSize: "12px", colors: ["#fff"] }
    },
    tooltip: {
      theme: "dark",
      y: {
        formatter: function (val) {
          return "₹ " + val;
        }
      }
    },
    grid: {
      padding: { top: 0, bottom: 0 },
      row: { colors: ["transparent"], opacity: 0 }
    }



  };


  

var chart = new ApexCharts(document.querySelector("#rmPortalChart"), options);
  chart.render();

  // Exposed for the date filter form (RM_Portal.html inline script)
  window.updateRmPortalCharts = function updateRmPortalCharts(selectedDate) {
    const url = window.location.pathname + '?ajax=1&selected_date=' + encodeURIComponent(selectedDate || '');

    fetch(url, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (payload) {
        const rmCategories = Array.isArray(payload.rm_categories) ? payload.rm_categories : [];
        const rmValues = Array.isArray(payload.rm_values) ? payload.rm_values : [];

        // If no data, show an empty chart with a single label.
        const nextCategories = rmCategories.length ? rmCategories : ['No Data'];
        const nextValues = rmValues.length ? rmValues : [0];

        const maxValue = Math.max.apply(null, nextValues);

        chart.updateOptions({
          xaxis: {
            categories: nextCategories,
            min: 0,
            max: Math.ceil((maxValue || 0) * 1.1),
            tickAmount: 5,
            labels: {
              formatter: function (val) {
                return "₹ " + Number(val).toLocaleString("en-IN");
              }
            }
          }
        });

        chart.updateSeries([{ name: 'collection', data: nextValues }], true);
      })
      .catch(function (err) {
        console.error('updateRmPortalCharts failed:', err);
      });
  };

