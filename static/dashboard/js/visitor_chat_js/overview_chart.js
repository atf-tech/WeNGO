var options = {
    series: [
        {
            name: "Conversations",
            type: "bar",
            data: [120, 255, 355, 285, 245, 280, 300, 120, 215, 290, 225, 280, 285, 85]
        },
        {
            name: "Messages",
            type: "bar",
            data: [290, 450, 590, 465, 475, 410, 495, 270, 475, 565, 395, 370, 300, 220]
        },
        {
            name: "Visitors",
            type: "area",
            data: [110, 230, 280, 205, 180, 200, 250, 105, 185, 220, 180, 180, 200, 60]
        }
    ],

    chart: {
        height: 430,
        type: "line",
        stacked: false,
        toolbar: {
            show: false
        }
    },

    colors: [
        "#5969aa", // Conversations
        "#2ec4b6", // Messages
        "#3498db"  // Visitors
    ],

    stroke: {
        width: [0, 0, 4],
        curve: "smooth"
    },

    plotOptions: {
        bar: {
            horizontal: false,
            columnWidth: "35%",
            borderRadius: 5
        }
    },

    fill: {
        opacity: [1, 1, 0.45],
        gradient: {
            shade: "light",
            type: "vertical",
            opacityFrom: 0.7,
            opacityTo: 0.15,
            stops: [0, 100]
        }
    },

    dataLabels: {
        enabled: false
    },

    markers: {
        size: 0
    },

    xaxis: {
        categories: [
            "31 May",
            "01 Jun",
            "02 Jun",
            "03 Jun",
            "04 Jun",
            "05 Jun",
            "06 Jun",
            "07 Jun",
            "08 Jun",
            "09 Jun",
            "10 Jun",
            "11 Jun",
            "12 Jun",
            "13 Jun"
        ],
        axisBorder: {
            show: false
        }
    },

    yaxis: {
        min: 0,
        max: 700,
        tickAmount: 7,
        labels: {
            formatter: function (val) {
                return parseInt(val);
            }
        }
    },

    grid: {
        borderColor: "#e9ecef",
        strokeDashArray: 3
    },

    legend: {
        position: "bottom",
        horizontalAlign: "left",
        markers: {
            radius: 12
        }
    },

    tooltip: {
        shared: true,
        intersect: false
    }
};

var chart = new ApexCharts(
    document.querySelector("#line_area_charts"),
    options
);

chart.render();  
  
  
  
 