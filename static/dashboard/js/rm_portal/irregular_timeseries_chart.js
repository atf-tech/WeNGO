(function () {
  const dayChartEl = document.getElementById("area_chart_irregular_0101");
  if (!dayChartEl) return;

  // Avoid duplicate chart initialization if this script is loaded twice.
  if (dayChartEl.dataset.apexInitialized === "true") return;
  dayChartEl.dataset.apexInitialized = "true";

  function readJson(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  // Coerce every value to a number; fall back to 0 for null/undefined/NaN
  // so the chart still renders when a series has empty or zero values.
  function toNumberArray(arr) {
    if (!Array.isArray(arr)) return [];
    return arr.map(function (v) {
      const n = Number(v);
      return n != null && !isNaN(n) ? n : 0;
    });
  }

  const dayLabels = readJson("day-labels");
  const chennaiData = readJson("chennai-day");
  const maduraiData = readJson("madurai-day");
  const bangaloreData = readJson("bangalore-day");

  if (
    !Array.isArray(dayLabels) ||
    !Array.isArray(chennaiData) ||
    !Array.isArray(maduraiData) ||
    !Array.isArray(bangaloreData)
  ) {
    // Required JSON scripts are missing; do not initialize the chart.
    return;
  }

  const chennai = toNumberArray(chennaiData);
  const madurai = toNumberArray(maduraiData);
  const bangalore = toNumberArray(bangaloreData);

  const options = {
    series: [
      { name: "Chennai", data: chennai },
      { name: "Madurai", data: madurai },
      { name: "Bangalore", data: bangalore },
    ],

    colors: ["#4cc1d6", "#f0a728", "#e884ac"],

    chart: {
      type: "area",
      height: 350,
      stacked: false,
      toolbar: { show: false },
      zoom: {
        enabled: false,
      },
    },

    dataLabels: {
      enabled: false,
    },

    markers: {
      size: 4,
    },

    stroke: {
      curve: "smooth",
      width: 2,
    },

    fill: {
      type: "gradient",
      gradient: {
        shadeIntensity: 1,
        inverseColors: false,
        opacityFrom: 0.45,
        opacityTo: 0.05,
        stops: [20, 100, 100, 100],
      },
    },

    yaxis: {
    min: 0,
    max: 50000,
    tickAmount: 5,
    labels: {
        formatter: function (value) {
            return Math.round(value).toLocaleString("en-IN");
        }
    }
    },

    xaxis: {
      categories: dayLabels,
      labels: {
        style: {
          colors: "#8e8da4",
        },
      },
    },

    title: {
      text: "7 Days Data",
      align: "left",
    },

    tooltip: {
      shared: true,
      y: {
        formatter: function (val) {
          return "₹" + Number(val).toLocaleString("en-IN");
        },
      },
    },

    legend: {
      position: "top",
      horizontalAlign: "right",
    },
  };

  const chart = new ApexCharts(dayChartEl, options);
  chart.render();
})();
