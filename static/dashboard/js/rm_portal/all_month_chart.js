var options = {
  series: [{
    name: "This Month Revenue",
    data: [480, 620, 350]
  }],

  chart: {
    type: "bar",
    height: 420,
    toolbar: {
      show: false
    },
    background: "transparent",
    dropShadow: {
      enabled: true,
      top: 8,
      left: 0,
      blur: 10,
      opacity: 0.15
    }
  },

  colors: [
    "#4F46E5",
    "#06B6D4",
    "#F97316"
  ],

  plotOptions: {
    bar: {
      horizontal: false,
      distributed: true,
      columnWidth: "45%",
      borderRadius: 15,
      borderRadiusApplication: "end",
      borderRadiusWhenStacked: "last",
      dataLabels: {
        position: "top"
      }
    }
  },

  dataLabels: {
    enabled: true,
    offsetY: -20,
    style: {
      fontSize: "14px",
      fontWeight: "700",
      colors: ["#374151"]
    },
    formatter: function (val) {
      return "₹" + val;
    }
  },

  xaxis: {
    categories: [
      "Chennai",
      "Bangalore",
      "Madurai"
    ],
    labels: {
      style: {
        fontSize: "14px",
        fontWeight: 600
      }
    },
    axisBorder: {
      show: false
    },
    axisTicks: {
      show: false
    }
  },

  yaxis: {
    labels: {
      formatter: function (val) {
        return "₹" + val.toLocaleString("en-IN");
      }
    }
  },

  grid: {
    borderColor: "#E5E7EB",
    strokeDashArray: 5,
    padding: {
      left: 20,
      right: 20
    }
  },

  legend: {
    show: false
  },

  title: {
    text: "Branch Revenue - This Month",
    align: "left",
    style: {
      fontSize: "20px",
      fontWeight: "700"
    }
  },

  subtitle: {
    text: "Monthly Revenue Performance",
    style: {
      fontSize: "13px",
      color: "#6B7280"
    }
  },

  tooltip: {
    theme: "light",
    y: {
      formatter: function (val) {
        return "₹ " + val + "K";
      }
    }
  }
};

var chart = new ApexCharts(
  document.querySelector("#rmPortalBranchChart"),
  options
);

chart.render();