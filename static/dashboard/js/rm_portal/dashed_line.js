(function () {
  const monthChartEl = document.querySelector("#line_chart_dashed_111");
  if (!monthChartEl) return;

  // Avoid duplicate chart initialization if this script is loaded twice.
  if (monthChartEl.dataset.apexInitialized === "true") return;
  monthChartEl.dataset.apexInitialized = "true";

  const monthLabelsScript = document.getElementById("month-labels");
  const chennaiMonthScript = document.getElementById("chennai-month");
  const maduraiMonthScript = document.getElementById("madurai-month");
  const bangaloreMonthScript = document.getElementById("bangalore-month");

  if (!monthLabelsScript || !chennaiMonthScript || !maduraiMonthScript || !bangaloreMonthScript) {
    // Required JSON scripts are missing; do not initialize the chart.
    return;
  }

  const monthLabels = JSON.parse(monthLabelsScript.textContent);
  const chennaiMonth = JSON.parse(chennaiMonthScript.textContent);
  const maduraiMonth = JSON.parse(maduraiMonthScript.textContent);
  const bangaloreMonth = JSON.parse(bangaloreMonthScript.textContent);

  // Validate array lengths to prevent ApexCharts failures.
  const len = monthLabels.length;
  if (
    !Array.isArray(monthLabels) ||
    !Array.isArray(chennaiMonth) ||
    !Array.isArray(maduraiMonth) ||
    !Array.isArray(bangaloreMonth) ||
    chennaiMonth.length !== len ||
    maduraiMonth.length !== len ||
    bangaloreMonth.length !== len
  ) {
    return;
  }

  const monthOptions = {
    chart: {
      type: "line",
      height: 350,
      toolbar: { show: false },
    },
    colors: ["#2e65d3", "#4ab02b", "#f672a7"],
    series: [
      { name: "Chennai", data: chennaiMonth },
      { name: "Madurai", data: maduraiMonth },
      { name: "Bangalore", data: bangaloreMonth },
    ],
    xaxis: {
      categories: monthLabels,
    },
    stroke: {
      curve: "smooth",
      width: 4,
    },
    dataLabels: {
      enabled: false,
    },
    markers: {
      size: 5,
    },
    yaxis: {
      min: 0,
      max: 1500000,
      tickAmount: 5,
      labels: {
        formatter: function (val) {
          return "₹" + Number(val).toLocaleString("en-IN");
        },
      },
    },
    tooltip: {
      shared: true,
      intersect: false,
      y: {
        formatter: function (val) {
          return "₹" + Number(val).toLocaleString("en-IN");
        },
      },
    },
    grid: {
      borderColor: "#f1f1f1",
    },
  };

  new ApexCharts(monthChartEl, monthOptions).render();
})();
